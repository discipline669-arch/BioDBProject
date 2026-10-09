#!/usr/bin/env Rscript
# ============================================================
# BioDB Project — Member 3: ML Classification & Biomarker Discovery
# Datasets: GSE303889 (SKOV-3) + GSE283381 (OVCAR5)
#
# Models (per proposal §7): Logistic Regression (L1 glmnet),
#                            Random Forest (ranger),
#                            SVM radial (e1071)
#
# VALIDATION HIERARCHY (no data leakage):
#
#   PRIMARY — Cross-dataset external validation:
#     Train on ALL 6 samples of one cell line, predict the other.
#     Feature selection (top-K by |t|) is performed ONLY on the
#     training dataset. The test dataset is never consulted for
#     feature selection, scaling, or model fitting.
#     Direction A: SKOV-3 → OVCAR5
#     Direction B: OVCAR5 → SKOV-3
#
#   SECONDARY — Within-dataset LOOCV (reference only):
#     Leave-One-Out CV across all 12 samples. Feature selection
#     is nested inside each training fold. Results are reported
#     for within-study comparison only — not for biomarker claims.
#
#   IMPORTANT: The ML feature space is the full intersected gene
#   set (all genes present in both datasets). No DEG-based
#   pre-filtering is applied, because the DEG overlap was
#   computed using both datasets and would leak information.
#
# Outputs (results/ml/):
#   ml_metrics_summary.csv       metrics per model x K x validation
#   predictions_external.csv     per-direction external predictions
#   predictions_LOOCV.csv        per-fold held-out predictions (secondary)
#   external_by_direction.csv    per-direction external metrics
#   ROC_external.png
#   ROC_LOOCV.png
#   confusion_external.png
#   feature_importance.csv       per model x K: selection frequency
#   biomarker_panel.csv          top ranked candidate biomarkers
#   run_log.txt                  console log
# ============================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(glmnet)
  library(ranger)
  library(e1071)
})

set.seed(42)

# Resolve project root
resolve_proj <- function() {
  p <- Sys.getenv("BIODB_PROJ", unset = "")
  if (p != "" && dir.exists(p)) return(p)
  cands <- c("/home/nianderbrox/BioDB_Project",
             "E:/BioDBProject/transcriptomic_drug_resistance_project",
             getwd())
  cands[dir.exists(cands)][1]
}
PROJ <- resolve_proj()
cat("Project root:", PROJ, "\n")

RESULTS <- file.path(PROJ, "results")
MLOUT   <- file.path(RESULTS, "ml")

dir.create(MLOUT, recursive = TRUE, showWarnings = FALSE)
sink(file.path(MLOUT, "run_log.txt"), split = TRUE)
on.exit(sink(), add = TRUE)

cat("========================================\n")
cat("  ML ANALYSIS: RESISTANT vs SENSITIVE\n")
cat("  (Leakage-safe cross-dataset validation)\n")
cat("========================================\n")

# ============================================================
# 1. Load feature matrix and labels
# ============================================================
X <- read.csv(file.path(MLOUT, "expression_matrix.csv"), check.names = FALSE,
              row.names = "sample")
labels <- read.csv(file.path(MLOUT, "labels.csv"), stringsAsFactors = FALSE)

stopifnot(all(rownames(X) == labels$sample))
cat("Feature matrix:", nrow(X), "samples x", ncol(X), "genes\n")
cat("Conditions:\n"); print(table(labels$condition))
cat("Datasets:\n");  print(table(labels$dataset))

y <- factor(labels$condition, levels = c("Sensitive", "Resistant"))

FEATURE_COLS <- colnames(X)
K_VALUES <- c(20, 50, 100, 200, 500)
SEEDS <- list(LR = 42, RF = 43, SVM = 44)

# Dataset indices
ds <- labels$dataset
idx_ds1 <- which(ds == "GSE303889_SKOV3")   # SKOV-3 (6 samples)
idx_ds2 <- which(ds == "GSE283381_OVCAR5")  # OVCAR5 (6 samples)

# ============================================================
# 2. Helpers
# ============================================================

# Two-sample t statistic (positive => higher in Resistant)
tstat_per_gene <- function(x_train, y_train, pos = "Resistant") {
  g1 <- which(y_train == pos)
  g0 <- which(y_train != pos)
  stats <- apply(x_train, 2, function(v) {
    m1 <- mean(v[g1]); m0 <- mean(v[g0])
    if (length(g1) < 2 || length(g0) < 2) return(0)
    s1 <- sd(v[g1]); s0 <- sd(v[g0])
    n1 <- length(g1); n0 <- length(g0)
    sp <- sqrt(((n1 - 1) * s1^2 + (n0 - 1) * s0^2) / (n1 + n0 - 2))
    if (is.na(sp) || sp == 0) 0 else (m1 - m0) / sp
  })
  stats[is.finite(stats)]
}

# Nested feature selection: top-K genes by |t| on the TRAINING data only
select_top_k <- function(x_train, y_train, k) {
  ts <- tstat_per_gene(x_train, y_train)
  if (length(ts) == 0) return(character(0))
  names(sort(abs(ts), decreasing = TRUE))[seq_len(min(k, length(ts)))]
}

# AUC via Wilcoxon/Mann-Whitney
auc_from_scores <- function(score, pos_bool) {
  n_pos <- sum(pos_bool); n_neg <- sum(!pos_bool)
  if (n_pos == 0 || n_neg == 0) return(NA)
  r <- rank(score)
  (sum(r[pos_bool]) - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
}

# Binary classification metrics
compute_metrics <- function(prob, truth) {
  truth_f <- factor(truth, levels = c("Sensitive", "Resistant"))
  pred <- factor(ifelse(prob >= 0.5, "Resistant", "Sensitive"),
                 levels = c("Sensitive", "Resistant"))
  tp <- sum(pred == "Resistant" & truth_f == "Resistant")
  tn <- sum(pred == "Sensitive" & truth_f == "Sensitive")
  fp <- sum(pred == "Resistant" & truth_f == "Sensitive")
  fn <- sum(pred == "Sensitive" & truth_f == "Resistant")
  acc  <- (tp + tn) / length(truth_f)
  prec <- if (tp + fp == 0) NA_real_ else tp / (tp + fp)
  rec  <- if (tp + fn == 0) NA_real_ else tp / (tp + fn)
  f1   <- if (is.na(prec) || is.na(rec) || prec + rec == 0) NA_real_
          else 2 * prec * rec / (prec + rec)
  auc  <- auc_from_scores(prob, truth_f == "Resistant")
  c(Accuracy = acc, Precision = prec, Recall = rec, F1 = f1, ROC_AUC = auc)
}

# ROC curve
roc_points <- function(prob, pos_bool) {
  ord <- order(prob, decreasing = TRUE)
  p <- prob[ord]; t <- pos_bool[ord]
  n_pos <- sum(t); n_neg <- sum(!t)
  tpr <- numeric(length(t) + 1); fpr <- numeric(length(t) + 1)
  tpr[1] <- 0; fpr[1] <- 0
  for (i in seq_along(t)) {
    tpr[i + 1] <- sum(t[1:i]) / n_pos
    fpr[i + 1] <- sum(!t[1:i]) / n_neg
  }
  data.frame(FPR = fpr, TPR = tpr)
}

# Standardize a new matrix with training-fold statistics
scale_new <- function(m, mu, s) {
  m <- sweep(m, 2, mu, "-")
  sweep(m, 2, s, "/")
}

# ============================================================
# 3. Model builders: return predict(x_mat) -> prob(Resistant)
# ============================================================

build_lr <- function(x_tr, y_tr, seed) {
  fit <- glmnet(x_tr, as.numeric(y_tr), family = "binomial",
                alpha = 1, lambda = 0.1)
  function(x_te) drop(predict(fit, newx = x_te, type = "response"))
}

build_rf <- function(x_tr, y_tr, seed) {
  set.seed(seed)
  fit <- ranger(x = x_tr,
                y = factor(y_tr, levels = c("Sensitive", "Resistant")),
                probability = TRUE,
                num.trees = 500, mtry = max(2, floor(sqrt(ncol(x_tr)))),
                importance = "impurity", seed = seed, num.threads = 1)
  function(x_te) {
    pr <- predict(fit, data = x_te)
    pr$predictions[, "Resistant"]
  }
}

build_svm <- function(x_tr, y_tr, seed) {
  set.seed(seed)
  fit <- svm(x_tr, factor(y_tr, levels = c("Sensitive", "Resistant")),
             probability = TRUE, kernel = "radial", scale = FALSE)
  function(x_te) {
    pr <- predict(fit, x_te, probability = TRUE)
    attr(pr, "probabilities")[, "Resistant"]
  }
}

MODEL_BUILDERS <- list(
  LogisticRegression = build_lr,
  RandomForest       = build_rf,
  SVM                = build_svm
)

# ============================================================
# 4. PRIMARY: Cross-dataset external validation
#    Train on one cell line, predict the other.
#    Feature selection is nested inside the training dataset.
# ============================================================
cat("\n==============================================\n")
cat("  PRIMARY: CROSS-DATASET VALIDATION\n")
cat("  (One dataset discovers biomarkers, other validates)\n")
cat("==============================================\n")

ext_plans <- list(
  list(name = "SKOV3->OVCAR5", train = idx_ds1, test = idx_ds2),
  list(name = "OVCAR5->SKOV3", train = idx_ds2, test = idx_ds1)
)

ext_preds <- list()
ext_imp <- list()

for (model_name in names(MODEL_BUILDERS)) {
  builder <- MODEL_BUILDERS[[model_name]]
  for (K in K_VALUES) {
    cat("---", model_name, "top-K =", K, "---\n")
    fold_pred <- data.frame()
    imp_mat <- matrix(0, nrow = length(FEATURE_COLS), ncol = length(ext_plans),
                      dimnames = list(FEATURE_COLS, sapply(ext_plans, `[[`, "name")))

    for (d in seq_along(ext_plans)) {
      tr_idx <- ext_plans[[d]]$train
      te_idx <- ext_plans[[d]]$test

      feats <- select_top_k(X[tr_idx, , drop = FALSE], y[tr_idx], K)
      if (length(feats) < 2) {
        cat("  WARNING: fewer than 2 features selected for", ext_plans[[d]]$name, "- skipping\n")
        next
      }
      cat("  ", ext_plans[[d]]$name, ": selected", length(feats), "features\n")

      x_tr <- X[tr_idx, feats, drop = FALSE]
      mu <- colMeans(x_tr); s <- apply(x_tr, 2, sd); s[s == 0] <- 1
      x_tr_s <- scale_new(as.matrix(x_tr), mu, s)
      x_te_s <- scale_new(as.matrix(X[te_idx, feats, drop = FALSE]), mu, s)

      fit <- builder(x_tr_s, y[tr_idx], SEEDS[[model_name]])
      prob <- fit(x_te_s)

      fold_pred <- rbind(fold_pred, data.frame(
        sample = rownames(X)[te_idx],
        condition = as.character(y[te_idx]),
        dataset = ds[te_idx],
        direction = ext_plans[[d]]$name,
        model = model_name, K = K, prob = prob
      ))

      imp_mat[feats, d] <- 1
    }

    ext_preds[[paste(model_name, K, sep = "_K")]] <- fold_pred
    sel_freq <- rowSums(imp_mat) / 2
    ext_imp[[paste(model_name, K, sep = "_K")]] <-
      data.frame(gene = FEATURE_COLS, model = model_name, K = K,
                 selection_freq = sel_freq, stringsAsFactors = FALSE)
  }
}

# ============================================================
# 5. SECONDARY: Within-dataset LOOCV (reference only)
# ============================================================
cat("\n==============================================\n")
cat("  SECONDARY: WITHIN-DATASET LOOCV (reference)\n")
cat("==============================================\n")

loocv_preds <- list()
loocv_imp <- list()

for (model_name in names(MODEL_BUILDERS)) {
  builder <- MODEL_BUILDERS[[model_name]]
  for (K in K_VALUES) {
    cat("---", model_name, "top-K =", K, "---\n")
    fold_pred <- data.frame()
    imp_mat <- matrix(0, nrow = length(FEATURE_COLS), ncol = 12,
                      dimnames = list(FEATURE_COLS, paste0("fold", 1:12)))

    for (i in seq_len(nrow(X))) {
      tr_idx <- setdiff(seq_len(nrow(X)), i)
      te_idx <- i

      feats <- select_top_k(X[tr_idx, , drop = FALSE], y[tr_idx], K)
      if (length(feats) < 2) next

      x_tr <- X[tr_idx, feats, drop = FALSE]
      mu <- colMeans(x_tr); s <- apply(x_tr, 2, sd); s[s == 0] <- 1
      x_tr_s <- scale_new(as.matrix(x_tr), mu, s)
      x_te_s <- scale_new(as.matrix(X[te_idx, feats, drop = FALSE]), mu, s)

      fit <- builder(x_tr_s, y[tr_idx], SEEDS[[model_name]])
      prob <- fit(x_te_s)

      fold_pred <- rbind(fold_pred, data.frame(
        sample = rownames(X)[te_idx],
        condition = as.character(y[te_idx]),
        model = model_name, K = K, prob = prob
      ))

      imp_mat[feats, i] <- 1
    }

    loocv_preds[[paste(model_name, K, sep = "_K")]] <- fold_pred
    sel_freq <- rowSums(imp_mat) / 12
    loocv_imp[[paste(model_name, K, sep = "_K")]] <-
      data.frame(gene = FEATURE_COLS, model = model_name, K = K,
                 selection_freq = sel_freq, stringsAsFactors = FALSE)
  }
}

# ============================================================
# 6. Metrics summary
# ============================================================
summarize_metrics <- function(pred_df, label) {
  out <- compute_metrics(pred_df$prob, pred_df$condition)
  data.frame(validation = label, model = pred_df$model[1],
             K = pred_df$K[1], n = nrow(pred_df), t(out), check.names = FALSE)
}

# External metrics (PRIMARY)
metrics_ext <- lapply(ext_preds, function(pd) summarize_metrics(pd, "External"))
ml_metrics_ext <- bind_rows(metrics_ext)

# LOOCV metrics (SECONDARY)
metrics_loocv <- lapply(loocv_preds, function(pd) summarize_metrics(pd, "LOOCV"))
ml_metrics_loocv <- bind_rows(metrics_loocv)

ml_metrics <- bind_rows(ml_metrics_ext, ml_metrics_loocv)

# Per-direction external metrics
ext_by_dir <- bind_rows(ext_preds) %>%
  group_by(model, K, direction) %>%
  summarise(Accuracy = compute_metrics(prob, condition)[["Accuracy"]],
            ROC_AUC  = compute_metrics(prob, condition)[["ROC_AUC"]],
            Precision = compute_metrics(prob, condition)[["Precision"]],
            Recall    = compute_metrics(prob, condition)[["Recall"]],
            F1        = compute_metrics(prob, condition)[["F1"]],
            n = n(), .groups = "drop")

write.csv(ml_metrics, file.path(MLOUT, "ml_metrics_summary.csv"), row.names = FALSE)
write.csv(ext_by_dir, file.path(MLOUT, "external_by_direction.csv"), row.names = FALSE)
write.csv(bind_rows(ext_preds),  file.path(MLOUT, "predictions_external.csv"), row.names = FALSE)
write.csv(bind_rows(loocv_preds), file.path(MLOUT, "predictions_LOOCV.csv"), row.names = FALSE)

cat("\n========== METRICS SUMMARY ==========\n")
cat("\n--- External Validation (PRIMARY) ---\n")
print(ml_metrics_ext)
cat("\n--- LOOCV (SECONDARY, reference only) ---\n")
print(ml_metrics_loocv)
cat("\n--- Per-Direction External ---\n")
print(ext_by_dir)

# ============================================================
# 7. ROC curves
# ============================================================
plot_rocs <- function(pred_df, outfile, title_suffix) {
  roc_all <- pred_df %>%
    split(list(.$model, .$K)) %>%
    lapply(function(sdf) {
      rc <- roc_points(sdf$prob, sdf$condition == "Resistant")
      rc$model <- sdf$model[1]; rc$K <- as.factor(sdf$K[1])
      rc$AUC <- auc_from_scores(sdf$prob, sdf$condition == "Resistant")
      rc
    }) %>%
    bind_rows()

  if (nrow(roc_all) == 0) {
    cat("No valid ROC data for", title_suffix, "- skipping plot\n")
    return(invisible(NULL))
  }

  p <- ggplot(roc_all, aes(x = FPR, y = TPR, color = K)) +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "grey60") +
    geom_step(linewidth = 0.8) +
    facet_wrap(~ model) +
    scale_color_manual(values = c("#377eb8", "#4daf4a", "#e41a1c", "#984ea3", "#ff7f00"),
                       name = "Top-K") +
    labs(x = "False Positive Rate", y = "True Positive Rate",
         title = paste("ROC Curves —", title_suffix)) +
    theme_bw(base_size = 14) +
    theme(legend.position = "top")
  ggsave(outfile, p, width = 10, height = 7, dpi = 300)
}

plot_rocs(bind_rows(ext_preds),  file.path(MLOUT, "ROC_external.png"),
          "Cross-Dataset Validation (Primary)")
plot_rocs(bind_rows(loocv_preds), file.path(MLOUT, "ROC_LOOCV.png"),
          "Within-Dataset LOOCV (Secondary)")

# ============================================================
# 8. Confusion matrix heatmap (External, K = 100)
# ============================================================
best_K <- 100
conf_plot_df <- bind_rows(ext_preds) %>%
  filter(K == best_K) %>%
  mutate(pred = factor(ifelse(prob >= 0.5, "Resistant", "Sensitive"),
                       levels = c("Resistant", "Sensitive")),
         true = factor(condition, levels = c("Resistant", "Sensitive"))) %>%
  count(model, direction, true, pred, name = "count")

if (nrow(conf_plot_df) > 0) {
  p_conf <- ggplot(conf_plot_df, aes(x = pred, y = true, fill = count)) +
    geom_tile(color = "white") +
    geom_text(aes(label = count), color = "white", size = 6) +
    facet_wrap(~ model + direction, ncol = 2) +
    scale_fill_gradient(low = "#fdc086", high = "#e41a1c") +
    labs(x = "Predicted", y = "True", fill = "Count",
         title = paste("Confusion Matrices — Cross-Dataset Validation (top-K =", best_K, ")")) +
    theme_bw(base_size = 14) +
    theme(axis.text.x = element_text(angle = 0, hjust = 0.5))
  ggsave(file.path(MLOUT, "confusion_external.png"), p_conf, width = 10, height = 8, dpi = 300)
}

# ============================================================
# 9. Feature importance & biomarker panel
# ============================================================
# Aggregate selection frequency across cross-dataset folds
imp_all <- bind_rows(ext_imp) %>%
  group_by(gene) %>%
  summarise(
    n_select_slots = sum(selection_freq > 0),
    mean_freq     = mean(selection_freq),
    log2fc_mag_ds1 = NA_real_,
    log2fc_mag_ds2 = NA_real_,
    .groups = "drop"
  )

# Annotate with mean |log2FC| from the two DESeq2 runs
lfc1 <- read.csv(file.path(RESULTS, "comparison", "dataset1_annotated.csv"))
lfc2 <- read.csv(file.path(RESULTS, "comparison", "dataset2_annotated.csv"))
lfc1_g <- lfc1 %>% distinct(gene_name, .keep_all = TRUE) %>%
  transmute(gene = gene_name, lfc1 = abs(log2FoldChange))
lfc2_g <- lfc2 %>% distinct(gene_name, .keep_all = TRUE) %>%
  transmute(gene = gene_name, lfc2 = abs(log2FoldChange))
lfc_df <- merge(merge(imp_all, lfc1_g, by = "gene", all.x = TRUE),
                lfc2_g, by = "gene", all.x = TRUE)
lfc_df$log2fc_mag_ds1 <- lfc_df$lfc1
lfc_df$log2fc_mag_ds2 <- lfc_df$lfc2
lfc_df$lfc1 <- NULL; lfc_df$lfc2 <- NULL
lfc_df$mean_abs_lfc <- rowMeans(lfc_df[, c("log2fc_mag_ds1", "log2fc_mag_ds2")], na.rm = TRUE)

# Per-model feature-importance tables
imp_by_model <- bind_rows(ext_imp) %>%
  group_by(gene, model) %>%
  summarise(mean_selection_freq = mean(selection_freq), .groups = "drop") %>%
  inner_join(lfc_df[, c("gene", "mean_abs_lfc")], by = "gene")

write.csv(imp_by_model, file.path(MLOUT, "feature_importance.csv"), row.names = FALSE)

# Biomarker panel: rank by cross-dataset selection, tie-break by |log2FC|
panel <- lfc_df %>%
  arrange(desc(n_select_slots), desc(mean_freq), desc(mean_abs_lfc)) %>%
  head(30) %>%
  mutate(rank = seq_len(n())) %>%
  select(rank, gene, n_select_slots, mean_freq, mean_abs_lfc,
         log2fc_mag_ds1, log2fc_mag_ds2)

write.csv(panel, file.path(MLOUT, "biomarker_panel.csv"), row.names = FALSE)

cat("\nBiomarker panel (top 20, ranked by cross-dataset selection frequency):\n")
print(head(panel, 20))

# Feature importance plot (top genes across models)
top_genes <- lfc_df %>% arrange(desc(n_select_slots), desc(mean_abs_lfc)) %>%
  head(20) %>% pull(gene)
imp_plot_df <- imp_by_model %>% filter(gene %in% top_genes)

if (nrow(imp_plot_df) > 0) {
  p_imp <- ggplot(imp_plot_df, aes(x = reorder(gene, mean_selection_freq),
                                   y = mean_selection_freq, fill = model)) +
    geom_col(position = position_dodge(width = 0.8), width = 0.7) +
    coord_flip() +
    scale_fill_manual(values = c("#377eb8", "#4daf4a", "#e41a1c")) +
    labs(title = "Top Candidate Biomarkers — Mean Selection Frequency (Cross-Dataset)",
         x = "", y = "Mean selection frequency", fill = "Model") +
    theme_bw(base_size = 12)
  ggsave(file.path(MLOUT, "feature_importance.png"), p_imp, width = 11, height = 7, dpi = 300)
}

cat("\nAll outputs written to:", MLOUT, "\n")

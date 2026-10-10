#!/usr/bin/env Rscript
# ============================================================
# BioDB Project — Member 3: ML Classification & Biomarker Discovery
# Datasets: GSE303889 (SKOV-3) + GSE283381 (OVCAR5)
#
# Models (per proposal §7): Logistic Regression (L2 ridge glmnet),
#                            Random Forest (ranger),
#                            SVM radial (e1071)
#
# VALIDATION HIERARCHY:
#
#   PRIMARY — Cross-dataset external validation:
#     Train on ALL 6 samples of one cell line, predict the other.
#     Feature selection (top-K by |t|) is performed ONLY on the
#     training dataset. The test dataset is never consulted for
#     feature selection or model fitting.
#     Direction A: SKOV-3 → OVCAR5
#     Direction B: OVCAR5 → SKOV-3
#
#     Two test-normalization schemes are reported per direction:
#       target_z    (PRIMARY, transductive): test rows are z-scored
#                   with the test cell line's own mean/SD. This batch-
#                   corrects the two independently CPM-normalized datasets
#                   and matches the reference Python replication.
#       train_stats (secondary, strict): test rows are z-scored with the
#                   TRAINING cell line's mean/SD. Uses no information from
#                   the held-out dataset at all — the leak-free number.
#     In both schemes the model is fit once on identically normalized
#     training rows; only the test-row normalization differs.
#
#   SECONDARY — Within-cell-line LOOCV (reference only):
#     Leave-one-out within each cell line (5 training samples, 1 held
#     out). Feature selection AND normalization are computed from the
#     training samples only, so the held-out sample never influences its
#     own preprocessing. Results are for within-study comparison only.
#
#   IMPORTANT: The ML feature space is the full intersected gene
#   set (all genes present in both datasets). No DEG-based
#   pre-filtering is applied, because the DEG overlap was
#   computed using both datasets and would leak information.
#
# Outputs (results/ml/):
#   ml_metrics_summary.csv       metrics per model x K x validation x normalization
#   predictions_external.csv     per-direction external predictions (both normalizations)
#   predictions_LOOCV.csv        per-fold held-out predictions (secondary)
#   external_by_direction.csv    per-direction external metrics (both normalizations)
#   ROC_external.png             external ROC (target_z, primary)
#   ROC_external_trainstats.png  external ROC (train_stats, strict)
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
             "E:/BioDBProject/BioDBProject/transcriptomic_drug_resistance_project",
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
expr_rds <- file.path(MLOUT, "expression_matrix.rds")
if (file.exists(expr_rds)) {
  X <- readRDS(expr_rds)                       # fast: ~0.03 s vs >4 min for CSV
  cat("Loaded feature matrix from expression_matrix.rds\n")
} else {
  X <- as.matrix(read.csv(file.path(MLOUT, "expression_matrix.csv"),
                          check.names = FALSE, row.names = "sample"))
  cat("Loaded feature matrix from expression_matrix.csv (slow fallback)\n")
}
labels <- read.csv(file.path(MLOUT, "labels.csv"), stringsAsFactors = FALSE)

stopifnot(all(rownames(X) == labels$sample))
cat("Feature matrix:", nrow(X), "samples x", ncol(X), "genes\n")
cat("Conditions:\n"); print(table(labels$condition))
cat("Datasets:\n");  print(table(labels$dataset))

y <- factor(labels$condition, levels = c("Sensitive", "Resistant"))

FEATURE_COLS <- colnames(X)
K_VALUES <- c(20, 50, 100, 200, 500)
SEEDS <- list(LogisticRegression = 42, RandomForest = 43, SVM = 44)

# Dataset indices
ds <- labels$dataset
idx_ds1 <- which(ds == "GSE303889_SKOV3")   # SKOV-3 (6 samples)
idx_ds2 <- which(ds == "GSE283381_OVCAR5")  # OVCAR5 (6 samples)

# ============================================================
# 1b. Per-fold cross-dataset normalization
#     The two datasets were CPM-normalized independently, so they sit on
#     different per-gene scales (measured variance 0.172 vs 0.047). Genes are
#     standardized so the two cell lines share a common scale. This is done
#     INSIDE each fold from training rows only, so no held-out information is
#     used to fit the model.
# ============================================================
colvar <- function(m) {                 # fast column sample-variance
  n <- nrow(m)
  if (n < 2) return(rep(NA_real_, ncol(m)))
  mu <- colMeans(m)
  (colSums(m * m) - n * mu^2) / (n - 1)
}

# Standardize training rows with training statistics, and return the test rows
# under two normalizations:
#   te_self  -> test rows z-scored with the TEST rows' own mean/SD (transductive)
#   te_train -> test rows z-scored with the TRAINING rows' mean/SD (strict)
# For external folds `te_idx` is the whole held-out cell line; for LOOCV it is
# a single sample (so `te_self` is degenerate and `te_train` must be used).
standardize_train_test <- function(x, tr_idx, te_idx) {
  x_tr <- x[tr_idx, , drop = FALSE]
  mu_tr <- colMeans(x_tr)
  sd_tr <- sqrt(colvar(x_tr))
  sd_tr[!is.finite(sd_tr) | sd_tr == 0] <- 1
  x_tr_z <- sweep(sweep(x_tr, 2, mu_tr, "-"), 2, sd_tr, "/")

  x_te <- x[te_idx, , drop = FALSE]
  mu_te <- colMeans(x_te)
  sd_te <- sqrt(colvar(x_te))
  sd_te[!is.finite(sd_te) | sd_te == 0] <- 1
  x_te_self  <- sweep(sweep(x_te, 2, mu_te, "-"), 2, sd_te, "/")
  x_te_train <- sweep(sweep(x_te, 2, mu_tr, "-"), 2, sd_tr, "/")

  list(tr = x_tr_z, te_self = x_te_self, te_train = x_te_train)
}

# Test-normalization schemes reported for external validation. The first is the
# primary (batch-corrected) result; the second is the strictly non-transductive
# sensitivity check.
NORM_MODES <- c(target_z = "te_self", train_stats = "te_train")

# ============================================================
# 2. Helpers
# ============================================================

# Two-sample t statistic (positive => higher in Resistant). Vectorized over
# genes (~100x faster than the previous apply()-per-gene implementation).
tstat_per_gene <- function(x_train, y_train, pos = "Resistant") {
  g1 <- which(y_train == pos)
  g0 <- which(y_train != pos)
  if (length(g1) < 2 || length(g0) < 2) {
    return(stats::setNames(rep(0, ncol(x_train)), colnames(x_train)))
  }
  m1 <- x_train[g1, , drop = FALSE]
  m0 <- x_train[g0, , drop = FALSE]
  mu1 <- colMeans(m1); mu0 <- colMeans(m0)
  v1 <- colvar(m1);    v0 <- colvar(m0)
  n1 <- length(g1); n0 <- length(g0)
  sp <- sqrt(((n1 - 1) * v1 + (n0 - 1) * v0) / (n1 + n0 - 2))
  t <- (mu1 - mu0) / sp
  t[!is.finite(t)] <- 0
  stats::setNames(t, colnames(x_train))
}

# Nested feature selection: top-K genes by |t| on the TRAINING data only
select_top_k <- function(x_train, y_train, k) {
  ts <- tstat_per_gene(x_train, y_train)
  ts <- ts[is.finite(ts) & ts != 0]
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
  set.seed(seed)
  # Ridge (L2) logistic. Lasso (alpha = 1) is degenerate at this sample size:
  # with n = 6 and a few near-perfectly-separating genes the lasso CV path
  # collapses to a near-constant / inverted test probability. Ridge is stable
  # here and matches the reference Python replication (sklearn LR, L2).
  # Inner CV uses leave-one-out folds so both classes stay present in training.
  nfolds <- nrow(x_tr)
  cv <- tryCatch(
    glmnet::cv.glmnet(x_tr, as.numeric(y_tr), family = "binomial",
                      alpha = 0, nfolds = nfolds, standardize = TRUE),
    error = function(e) NULL
  )
  if (!is.null(cv)) {
    lambda <- cv$lambda.min
    fit    <- cv$glmnet.fit
  } else {                       # tiny-n fallback
    lambda <- 0.1
    fit    <- glmnet::glmnet(x_tr, as.numeric(y_tr), family = "binomial",
                             alpha = 0, lambda = lambda)
  }
  function(x_te) drop(predict(fit, newx = x_te, s = lambda, type = "response"))
}

build_rf <- function(x_tr, y_tr, seed) {
  set.seed(seed)
  fit <- ranger(x = x_tr,
                y = factor(y_tr, levels = c("Sensitive", "Resistant")),
                probability = TRUE,
                num.trees = 500, mtry = max(2, floor(sqrt(ncol(x_tr)))),
                min.node.size = 1,     # default is 10, > n=6 -> no splits possible
                importance = "impurity", seed = seed, num.threads = 1)
  function(x_te) {
    pr <- predict(fit, data = x_te)
    pr$predictions[, "Resistant"]
  }
}

build_svm <- function(x_tr, y_tr, seed) {
  set.seed(seed)
  yf <- factor(y_tr, levels = c("Sensitive", "Resistant"))
  # libsvm's internal probability cross-validation can fail when a fold ends up
  # single-class (possible at n = 5-6). Fall back to non-probabilistic SVM and
  # map decision values through a logistic, orienting the sign by training AUC.
  fit <- tryCatch(
    svm(x_tr, yf, probability = TRUE, kernel = "radial", scale = FALSE),
    error = function(e) NULL, warning = function(w) NULL
  )
  if (!is.null(fit)) {
    return(function(x_te) {
      pr <- predict(fit, x_te, probability = TRUE)
      attr(pr, "probabilities")[, "Resistant"]
    })
  }
  fit <- svm(x_tr, yf, probability = FALSE, kernel = "radial", scale = FALSE)
  dv_tr <- attr(predict(fit, x_tr, decision.values = TRUE), "decision.values")[, 1]
  orient <- if (auc_from_scores(dv_tr, y_tr == "Resistant") >= 0.5) 1 else -1
  function(x_te) {
    dv <- attr(predict(fit, x_te, decision.values = TRUE), "decision.values")[, 1]
    plogis(orient * dv)
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

      std <- standardize_train_test(X, tr_idx, te_idx)
      feats <- select_top_k(std$tr, y[tr_idx], K)
      if (length(feats) < 2) {
        cat("  WARNING: fewer than 2 features selected for", ext_plans[[d]]$name, "- skipping\n")
        next
      }
      cat("  ", ext_plans[[d]]$name, ": selected", length(feats), "features\n")

      x_tr <- std$tr[, feats, drop = FALSE]
      mu <- colMeans(x_tr); s <- apply(x_tr, 2, sd); s[s == 0] <- 1
      x_tr_s <- scale_new(as.matrix(x_tr), mu, s)

      # Model is fit once; only the test-row normalization differs.
      fit <- builder(x_tr_s, y[tr_idx], SEEDS[[model_name]])

      for (norm_name in names(NORM_MODES)) {
        x_te <- std[[NORM_MODES[[norm_name]]]][, feats, drop = FALSE]
        x_te_s <- scale_new(as.matrix(x_te), mu, s)
        prob <- fit(x_te_s)

        fold_pred <- rbind(fold_pred, data.frame(
          sample = rownames(X)[te_idx],
          condition = as.character(y[te_idx]),
          dataset = ds[te_idx],
          direction = ext_plans[[d]]$name,
          normalization = norm_name,
          model = model_name, K = K, prob = prob
        ))
      }

      imp_mat[feats, d] <- 1
    }

    ext_preds[[paste(model_name, K, sep = "_K")]] <- fold_pred
    sel_freq <- rowSums(imp_mat) / length(ext_plans)
    ext_imp[[paste(model_name, K, sep = "_K")]] <-
      data.frame(gene = FEATURE_COLS, model = model_name, K = K,
                 selection_freq = sel_freq, stringsAsFactors = FALSE)
  }
}

# ============================================================
# 5. SECONDARY: Within-cell-line LOOCV (reference only)
# ============================================================
cat("\n==============================================\n")
cat("  SECONDARY: WITHIN-CELL-LINE LOOCV (reference)\n")
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
      # Leave-one-out WITHIN the held-out sample's own cell line: train on the
      # other 5 samples of that dataset only. Preprocessing (normalization and
      # feature selection) uses the 5 training samples alone.
      same <- which(ds == ds[i])
      tr_idx <- setdiff(same, i)
      te_idx <- i

      std <- standardize_train_test(X, tr_idx, te_idx)
      feats <- select_top_k(std$tr, y[tr_idx], K)
      if (length(feats) < 2) next

      x_tr <- std$tr[, feats, drop = FALSE]
      mu <- colMeans(x_tr); s <- apply(x_tr, 2, sd); s[s == 0] <- 1
      x_tr_s <- scale_new(as.matrix(x_tr), mu, s)
      x_te_s <- scale_new(as.matrix(std$te_train[, feats, drop = FALSE]), mu, s)

      fit <- builder(x_tr_s, y[tr_idx], SEEDS[[model_name]])
      prob <- fit(x_te_s)

      fold_pred <- rbind(fold_pred, data.frame(
        sample = rownames(X)[te_idx],
        condition = as.character(y[te_idx]),
        normalization = "train_stats",
        model = model_name, K = K, prob = prob
      ))

      imp_mat[feats, i] <- 1
    }

    loocv_preds[[paste(model_name, K, sep = "_K")]] <- fold_pred
    sel_freq <- rowSums(imp_mat) / nrow(X)
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

# LOOCV metrics (SECONDARY)
metrics_loocv <- lapply(loocv_preds, function(pd) summarize_metrics(pd, "LOOCV"))
ml_metrics_loocv <- bind_rows(metrics_loocv) %>%
  mutate(direction = NA_character_, normalization = "train_stats")

# External metrics (PRIMARY): computed PER DIRECTION AND NORMALIZATION. The two
# directions have opposite probability scales (each model is trained on a
# different cell line), so pooling them into a single "External" row is not
# interpretable and has been removed.
metric_row <- function(prob, condition) {
  m <- compute_metrics(prob, condition)
  data.frame(Accuracy  = m[["Accuracy"]],
             Precision = m[["Precision"]],
             Recall    = m[["Recall"]],
             F1        = m[["F1"]],
             ROC_AUC   = m[["ROC_AUC"]],
             n         = length(prob))
}

ext_by_dir <- bind_rows(ext_preds) %>%
  group_by(model, K, direction, normalization) %>%
  group_modify(~ metric_row(.x$prob, .x$condition)) %>%
  ungroup() %>%
  mutate(validation = "External") %>%
  relocate(validation, model, K, direction, normalization, n)

ml_metrics <- bind_rows(ext_by_dir, ml_metrics_loocv) %>%
  relocate(validation, model, K, direction, normalization)

write.csv(ml_metrics, file.path(MLOUT, "ml_metrics_summary.csv"), row.names = FALSE)
write.csv(ext_by_dir, file.path(MLOUT, "external_by_direction.csv"), row.names = FALSE)
write.csv(bind_rows(ext_preds),  file.path(MLOUT, "predictions_external.csv"), row.names = FALSE)
write.csv(bind_rows(loocv_preds), file.path(MLOUT, "predictions_LOOCV.csv"), row.names = FALSE)

cat("\n========== METRICS SUMMARY ==========\n")
cat("\n--- External Validation (PRIMARY, per direction x normalization) ---\n")
print(as.data.frame(ext_by_dir))
cat("\n--- LOOCV (SECONDARY, reference only) ---\n")
print(as.data.frame(ml_metrics_loocv))

# ============================================================
# 7. ROC curves
# ============================================================
plot_rocs <- function(pred_df, outfile, title_suffix) {
  has_dir <- "direction" %in% names(pred_df) &&
             length(unique(pred_df$direction)) > 1

  splits <- if (has_dir) {
    interaction(pred_df$model, pred_df$K, pred_df$direction, drop = TRUE)
  } else {
    interaction(pred_df$model, pred_df$K, drop = TRUE)
  }

  roc_all <- pred_df %>%
    split(splits) %>%
    lapply(function(sdf) {
      rc <- roc_points(sdf$prob, sdf$condition == "Resistant")
      rc$model <- sdf$model[1]; rc$K <- as.factor(sdf$K[1])
      if (has_dir) rc$direction <- sdf$direction[1]
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
    { if (has_dir) facet_wrap(~ model + direction) else facet_wrap(~ model) } +
    scale_color_manual(values = c("#377eb8", "#4daf4a", "#e41a1c", "#984ea3", "#ff7f00"),
                       name = "Top-K") +
    labs(x = "False Positive Rate", y = "True Positive Rate",
         title = paste("ROC Curves —", title_suffix)) +
    theme_bw(base_size = 14) +
    theme(legend.position = "top")
  ggsave(outfile, p, width = 10, height = 7, dpi = 300)
}

ext_all <- bind_rows(ext_preds)

plot_rocs(ext_all %>% filter(normalization == "target_z"),
          file.path(MLOUT, "ROC_external.png"),
          "Cross-Dataset Validation — target-domain z (Primary)")
plot_rocs(ext_all %>% filter(normalization == "train_stats"),
          file.path(MLOUT, "ROC_external_trainstats.png"),
          "Cross-Dataset Validation — training-stat z (Strict)")
plot_rocs(bind_rows(loocv_preds), file.path(MLOUT, "ROC_LOOCV.png"),
          "Within-cell-line LOOCV (Secondary)")

# ============================================================
# 8. Confusion matrix heatmap (External, target_z, K = CONFUSION_K)
# ============================================================
CONFUSION_K <- 100
conf_plot_df <- ext_all %>%
  filter(K == CONFUSION_K, normalization == "target_z") %>%
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
         title = paste("Confusion Matrices — Cross-Dataset (target_z, top-K =", CONFUSION_K, ")")) +
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

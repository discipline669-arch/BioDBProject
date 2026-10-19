#!/usr/bin/env Rscript
# ============================================================
# Phase 3 - Differential expression, cross-dataset validation, enrichment
#           (NSCLC / osimertinib)
#
#   per cohort:
#     raw NCBI counts -> DESeq2   (design ~ cell_line + condition)  [preferred]
#                     -> limma    (log2CPM + cell_line covariate)   [if installed]
#                     -> base-R OLS/Wald on log2CPM + cell_line    [offline fallback]
#   thresholds from config (FDR < 0.05, |log2FC| > 1)
#   volcano + top-DEG heatmap
#   enrichment: GO(BP), KEGG, Reactome  (clusterProfiler; skipped if unavailable)
#
#   cross-dataset: overlap + directional consistency -> validated DEG set
#                  with a 2-set UpSet / Venn summary
#
# Run: Rscript scripts/03_deg_enrichment.R
# ============================================================

set.seed(42)
suppressPackageStartupMessages({ library(yaml); library(data.table); library(ggplot2) })

source(file.path(if (dir.exists("scripts")) "scripts" else ".", "R_utils.R"))
PROJ <- resolve_root()
cfg  <- load_config(PROJ)
DATA <- file.path(PROJ, cfg$paths$data)
ANN  <- file.path(PROJ, cfg$paths$annotation)
TAB  <- file.path(PROJ, cfg$paths$tables)
FIG  <- file.path(PROJ, cfg$paths$figures)
for (d in c(TAB, FIG)) dir.create(d, recursive = TRUE, showWarnings = FALSE)

FDR <- cfg$deg$fdr
LFC <- cfg$deg$lfc

log2cpm <- function(counts) {
  cpm <- sweep(counts, 2, colSums(counts), "/") * 1e6
  log2(cpm + 1)
}

design_mat <- function(cell_line, condition) {
  cl <- factor(cell_line)
  cd <- factor(condition, levels = c("Sensitive", "Resistant"))
  model.matrix(~ cl + cd)
}

# --- DESeq2 (preferred) ---------------------------------------------------
deg_deseq2 <- function(counts, cell_line, condition) {
  if (!has_pkg("DESeq2")) return(NULL)
  cd <- data.frame(cell_line = factor(cell_line), condition = factor(condition))
  dds <- DESeq2::DESeqDataSetFromMatrix(round(counts), cd, ~ cell_line + condition)
  keep <- rowSums(DESeq2::counts(dds)) >= cfg$deg$min_count
  dds <- dds[keep, ]
  dds <- DESeq2::DESeq(dds, quiet = TRUE)
  res <- DESeq2::results(dds, contrast = c("condition", "Resistant", "Sensitive"),
                         alpha = FDR)
  out <- as.data.frame(res)
  out$gene <- rownames(out)
  out[order(out$padj), c("gene", "log2FoldChange", "pvalue", "padj")]
}

# --- limma (log2CPM + cell_line) -----------------------------------------
deg_limma <- function(l2c, cell_line, condition) {
  if (!has_pkg("limma")) return(NULL)
  D <- design_mat(cell_line, condition)
  fit <- limma::lmFit(l2c, D)
  fit <- limma::eBayes(fit)
  coef_idx <- ncol(D)   # Resistant vs Sensitive after adjusting cell_line
  tt <- limma::topTable(fit, coef = coef_idx, number = Inf, sort.by = "none")
  data.frame(gene = rownames(tt), log2FoldChange = tt$logFC,
             pvalue = tt$P.Value, padj = tt$adj.P.Val,
             row.names = NULL, stringsAsFactors = FALSE)
}

# --- base-R OLS / Wald fallback (no Bioconductor) ------------------------
deg_ols <- function(l2c, cell_line, condition) {
  D  <- design_mat(cell_line, condition)
  p  <- ncol(D); n <- nrow(D)
  df <- n - p
  Q  <- qr(D)
  coef <- qr.coef(Q, t(l2c))            # p x genes
  if (is.null(dim(coef))) coef <- matrix(coef, ncol = 1)
  fitted <- t(coef) %*% t(D)            # genes x n
  resid  <- l2c - fitted
  sigma2 <- rowSums(resid^2) / df
  XtX_inv <- chol2inv(chol(crossprod(D)))
  cond_idx <- p
  var_cond <- as.numeric(XtX_inv[cond_idx, cond_idx]) * sigma2
  beta_cond <- coef[cond_idx, ]
  t_stat <- beta_cond / sqrt(var_cond)
  pval <- 2 * stats::pt(-abs(t_stat), df)
  data.frame(gene = rownames(l2c), log2FoldChange = beta_cond,
             pvalue = pval, padj = stats::p.adjust(pval, "BH"),
             row.names = NULL, stringsAsFactors = FALSE)
}

choose_degs <- function(l2c, counts, cell_line, condition) {
  for (m in cfg$deg$method_priority) {
    res <- switch(m,
                  DESeq2 = deg_deseq2(counts, cell_line, condition),
                  limma  = deg_limma(l2c, cell_line, condition),
                  ols    = deg_ols(l2c, cell_line, condition))
    if (!is.null(res)) { cat("  DEG method:", m, "\n"); attr(res, "method") <- m; return(res) }
  }
  stop("No DEG engine available.")
}

threshold_degs <- function(df) {
  df$regulation <- "NS"
  df$regulation[df$padj < FDR & df$log2FoldChange >  LFC] <- "Up"
  df$regulation[df$padj < FDR & df$log2FoldChange < -LFC] <- "Down"
  df
}

volcano <- function(df, acc) {
  df$neglog <- -log10(pmax(df$padj, .Machine$double.xmin))
  p <- ggplot(df, aes(log2FoldChange, neglog, color = regulation)) +
    geom_point(alpha = 0.5, size = 1) +
    scale_color_manual(values = c(Up = "#e41a1c", Down = "#377eb8", NS = "grey70")) +
    geom_vline(xintercept = c(-LFC, LFC), linetype = "dashed", color = "grey40") +
    geom_hline(yintercept = -log10(FDR), linetype = "dashed", color = "grey40") +
    labs(title = paste("Volcano -", acc), x = expression(log[2]~FC),
         y = expression(-log[10]~adj~P)) +
    theme_bw(base_size = 13)
  ggsave(file.path(FIG, paste0(acc, "_volcano.png")), p, width = 7, height = 6, dpi = 300)
}

heatmap_top <- function(l2c, df, acc, cd) {
  top <- head(df$gene[df$regulation != "NS"], 50)
  if (length(top) < 2) return(invisible(NULL))
  m <- l2c[top, cd$sample, drop = FALSE]
  m <- t(scale(t(m)))
  long <- data.frame(
    gene = rep(rownames(m), times = ncol(m)),
    sample = rep(colnames(m), each = nrow(m)),
    value = as.vector(m))
  long$condition <- cd$condition[match(long$sample, cd$sample)]
  long$cell_line <- cd$cell_line[match(long$sample, cd$sample)]
  long$gene <- factor(long$gene, levels = rev(rownames(m)))
  p <- ggplot(long, aes(sample, gene, fill = value)) +
    geom_tile() +
    scale_fill_gradient2(low = "#377eb8", mid = "white", high = "#e41a1c") +
    facet_grid(~ condition, scales = "free_x", space = "free_x") +
    labs(title = paste("Top DEGs -", acc), x = NULL, y = NULL, fill = "z") +
    theme_bw(base_size = 8) +
    theme(axis.text.x = element_text(angle = 90, hjust = 1),
          axis.text.y = element_text(size = 5))
  ggsave(file.path(FIG, paste0(acc, "_heatmap_topDEG.png")), p,
         width = 9, height = max(6, length(top) * 0.18), dpi = 300)
}

run_enrichment <- function(genes, label, out_tag) {
  if (length(genes) < 10) { cat("  [enrich] too few genes for", label, "\n"); return(invisible(NULL)) }
  if (!isTRUE(cfg$deg$enrichment$run_in_r)) {
    cat("  [enrich] delegated to Stage 5 (Python 03b_enrichment.py);",
        "set deg.enrichment.run_in_r: true to also run clusterProfiler here.\n")
    return(invisible(NULL))
  }
  if (!has_pkg("clusterProfiler") || !has_pkg("org.Hs.eg.db")) {
    cat("  [enrich] clusterProfiler/org.Hs.eg.db not installed; skipping (offline)\n")
    return(invisible(NULL))
  }
  map <- tryCatch(clusterProfiler::bitr(genes, "SYMBOL", "ENTREZID",
                                        org.Hs.eg.db::org.Hs.eg.db), error = function(e) NULL)
  if (is.null(map) || nrow(map) < 5) return(invisible(NULL))
  eg <- map$ENTREZID
  ego <- clusterProfiler::enrichGO(eg, org.Hs.eg.db::org.Hs.eg.db, ont = "BP",
                                   pAdjustMethod = cfg$deg$enrichment$p_adjust,
                                   pvalueCutoff = cfg$deg$enrichment$pvalue_cutoff,
                                   readable = TRUE)
  if (!is.null(ego) && nrow(as.data.frame(ego))) {
    write.csv(as.data.frame(ego), file.path(TAB, paste0(out_tag, "_GO_BP.csv")), row.names = FALSE)
    ggsave(file.path(FIG, paste0(out_tag, "_GO_BP_dotplot.png")),
           dotplot(ego, showCategory = 15) + ggtitle(paste("GO BP -", label)), width = 9, height = 8, dpi = 300)
  }
}

analyse_cohort <- function(acc, cohort_cfg) {
  cat("\n========== DEG:", acc, "==========\n")
  dest <- file.path(DATA, acc)
  cd   <- read.csv(file.path(dest, "coldata.csv"), stringsAsFactors = FALSE)
  cd   <- cd[cd$condition %in% c("Sensitive", "Resistant"), , drop = FALSE]

  raw <- if (identical(cohort_cfg$data_type, "counts")) {
    load_ncbi_counts(acc, dest, ANN)
  } else load_raw_matrix(acc, cohort_cfg$data_type, dest)
  if (is.null(raw)) { cat("  [SKIP] no raw counts\n"); return(NULL) }

  keep_rows <- rowSums(raw) >= cfg$deg$min_count
  raw <- raw[keep_rows, , drop = FALSE]
  counts <- raw[, cd$sample, drop = FALSE]
  l2c <- log2cpm(counts)

  res <- choose_degs(l2c, counts, cd$cell_line, cd$condition)
  res <- threshold_degs(res)
  write.csv(res, file.path(TAB, paste0(acc, "_DEG_full.csv")), row.names = FALSE)
  sig <- res[res$regulation != "NS", ]
  write.csv(sig, file.path(TAB, paste0(acc, "_DEG_significant.csv")), row.names = FALSE)
  write.csv(res[res$regulation == "Up", ],   file.path(TAB, paste0(acc, "_DEG_up.csv")), row.names = FALSE)
  write.csv(res[res$regulation == "Down", ], file.path(TAB, paste0(acc, "_DEG_down.csv")), row.names = FALSE)
  cat("  DEGs:", nrow(sig), "(up", sum(res$regulation == "Up"),
      "/ down", sum(res$regulation == "Down"), ")\n")

  volcano(res, acc)
  heatmap_top(l2c, res, acc, cd)

  if (nrow(sig)) run_enrichment(sig$gene, acc, acc)
  attr(res, "expr") <- l2c
  res
}

deg_disc <- analyse_cohort(cfg$cohorts$discovery$accession,  cfg$cohorts$discovery)
deg_val  <- analyse_cohort(cfg$cohorts$validation$accession, cfg$cohorts$validation)

# --- Cross-dataset comparison ---------------------------------------------
if (!is.null(deg_disc) && !is.null(deg_val)) {
  cat("\n========== Cross-dataset DEG comparison ==========\n")
  d1 <- deg_disc[deg_disc$regulation != "NS", c("gene", "log2FoldChange", "regulation")]
  d2 <- deg_val[deg_val$regulation != "NS",   c("gene", "log2FoldChange", "regulation")]
  names(d1) <- c("gene", "lfc_disc", "reg_disc")
  names(d2) <- c("gene", "lfc_val",  "reg_val")

  only_d <- setdiff(d1$gene, d2$gene)
  only_v <- setdiff(d2$gene, d1$gene)
  m <- merge(d1, d2, by = "gene")
  m$consistent <- m$reg_disc == m$reg_val
  m$sign_agree <- sign(m$lfc_disc) == sign(m$lfc_val)

  write.csv(m, file.path(TAB, "cross_DEG_overlap.csv"), row.names = FALSE)
  cat("  discovery DEGs:", nrow(d1), " validation DEGs:", nrow(d2), "\n")
  cat("  shared:", nrow(m), " consistent direction:", sum(m$consistent), "\n")

  # Validated set: significant in BOTH with consistent regulation + sign
  validated <- m[m$consistent & m$sign_agree, ]
  validated <- validated[order(abs(validated$lfc_disc) + abs(validated$lfc_val),
                               decreasing = TRUE), ]
  write.csv(validated, file.path(TAB, "validated_DEGs.csv"), row.names = FALSE)
  cat("  VALIDATED DEGs (both, consistent):", nrow(validated), "\n")

  # Overlap summary bar chart (categories of the 2-way DEG comparison).
  # Note: this is deliberately NOT called an UpSet plot — it is a category bar
  # summary; a true set-intersection UpSet figure remains future work.
  n_only_d <- length(only_d)
  n_only_v <- length(only_v)
  n_cons   <- sum(m$consistent & m$sign_agree)
  n_disc   <- sum(!m$consistent | !m$sign_agree)
  up <- data.frame(
    category = factor(c("Only discovery", "Only validation",
                        "Both (consistent)", "Both (discordant)"),
                      levels = c("Only discovery", "Both (consistent)",
                                 "Both (discordant)", "Only validation")),
    n = c(n_only_d, n_cons, n_disc, n_only_v))
  p <- ggplot(up, aes(category, n, fill = category)) +
    geom_col(show.legend = FALSE) +
    geom_text(aes(label = n), vjust = -0.4, size = 4) +
    labs(title = "Cross-dataset DEG overlap (validated resistance signature)",
         x = NULL, y = "Number of genes") +
    theme_bw(base_size = 13)
  ggsave(file.path(FIG, "cross_DEG_overlap_bar.png"), p, width = 8, height = 5, dpi = 300)

  if (nrow(m) > 2) {
    p2 <- ggplot(m, aes(lfc_disc, lfc_val, color = consistent)) +
      geom_point(alpha = 0.6) +
      geom_hline(yintercept = 0, linetype = "dashed", color = "grey50") +
      geom_vline(xintercept = 0, linetype = "dashed", color = "grey50") +
      labs(title = "Shared DEG log2FC - discovery vs validation",
           x = "log2FC (GSE202859)", y = "log2FC (GSE193258)") +
      theme_bw(base_size = 13)
    ggsave(file.path(FIG, "cross_DEG_lfc.png"), p2, width = 7, height = 6, dpi = 300)
  }

  # Two-set Venn via counts
  cat("\n  ---- Venn ----\n")
  cat("  discovery only:", n_only_d, "| validation only:", n_only_v,
      "| both consistent:", n_cons, "| both discordant:", n_disc, "\n")
}

cat("\nPhase 3 complete. Tables in", TAB, ", figures in", FIG, "\n")

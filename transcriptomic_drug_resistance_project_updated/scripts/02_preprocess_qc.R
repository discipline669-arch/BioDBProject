#!/usr/bin/env Rscript
# ============================================================
# Phase 2 - Preprocessing and QC (per cohort, NSCLC / osimertinib)
#
#   * load NCBI raw counts (Entrez) and map to gene symbols
#   * low-expression filtering
#   * normalisation:
#       counts -> DESeq2 VST (blind) when available, else log2(CPM+1)
#   * QC: library size, detected genes, PCA, sample-correlation heatmap
#   * save samples x genes processed matrix for the ML track
#
#   No labels are used in any normalisation step.
#
# Run: Rscript scripts/02_preprocess_qc.R
# ============================================================

set.seed(42)
suppressPackageStartupMessages({ library(yaml); library(data.table) })

source(file.path(if (dir.exists("scripts")) "scripts" else ".", "R_utils.R"))
PROJ <- resolve_root()
cfg  <- load_config(PROJ)
DATA <- file.path(PROJ, cfg$paths$data)
ANN  <- file.path(PROJ, cfg$paths$annotation)
FIG  <- file.path(PROJ, cfg$paths$figures)
TAB  <- file.path(PROJ, cfg$paths$tables)
for (d in c(FIG, TAB)) dir.create(d, recursive = TRUE, showWarnings = FALSE)

MIN_COUNT <- cfg$deg$min_count

log2cpm <- function(counts) {
  cpm <- sweep(counts, 2, colSums(counts), "/") * 1e6
  log2(cpm + 1)
}

normalise_cohort <- function(mat, data_type) {
  # mat: genes x samples
  if (identical(data_type, "counts") && has_pkg("DESeq2")) {
    cat("  normalisation: DESeq2 VST (blind)\n")
    keep <- rowSums(mat) >= MIN_COUNT
    mat <- mat[keep, , drop = FALSE]
    coldata <- data.frame(condition = factor(rep("A", ncol(mat))),
                          row.names = colnames(mat))
    dds <- DESeq2::DESeqDataSetFromMatrix(round(mat), coldata, ~ 1)
    vsd <- DESeq2::vst(dds, blind = TRUE)
    return(list(norm = SummarizedExperiment::assay(vsd), method = "vst", filtered = mat))
  }
  if (identical(data_type, "tpm")) {
    cat("  normalisation: log2(TPM+1)\n")
    keep <- rowSums(mat > 1) >= max(2, floor(0.25 * ncol(mat)))
    mat <- mat[keep, , drop = FALSE]
    return(list(norm = log2(mat + 1), method = "log2tpm", filtered = mat))
  }
  cat("  normalisation: log2(CPM+1) (counts)")
  if (!identical(data_type, "counts")) cat(" [fallback]")
  cat("\n")
  keep <- rowSums(mat) >= MIN_COUNT
  mat <- mat[keep, , drop = FALSE]
  list(norm = log2cpm(mat), method = "log2cpm", filtered = mat)
}

corr_heatmap_ggplot <- function(corr, anno, title, path) {
  if (!has_pkg("ggplot2") || !has_pkg("tidyr")) return(invisible(NULL))
  ord <- hclust(as.dist(1 - corr))$order
  corr <- corr[ord, ord]
  long <- data.frame(
    x = rep(rownames(corr), times = ncol(corr)),
    y = rep(colnames(corr), each = nrow(corr)),
    value = as.vector(corr))
  long$x <- factor(long$x, levels = rownames(corr))
  long$y <- factor(long$y, levels = rev(colnames(corr)))
  p <- ggplot2::ggplot(long, ggplot2::aes(x, y, fill = value)) +
    ggplot2::geom_tile() +
    ggplot2::scale_fill_gradient2(low = "#377eb8", mid = "white", high = "#e41a1c",
                                  midpoint = stats::median(corr), limits = c(0, 1)) +
    ggplot2::labs(title = title, x = NULL, y = NULL) +
    ggplot2::theme_bw(base_size = 9) +
    ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 90, hjust = 1))
  ggplot2::ggsave(path, p, width = max(6, ncol(corr) * 0.35),
                  height = max(6, ncol(corr) * 0.35), dpi = 300)
}

qc_cohort <- function(acc, cohort_cfg) {
  dest <- file.path(DATA, acc)
  cat("\n========== QC:", acc, "(", cohort_cfg$system, ") ==========\n")
  coldata_file <- file.path(dest, "coldata.csv")
  if (!file.exists(coldata_file)) stop("coldata.csv missing for ", acc, "; run 01_build_metadata.R")
  cd <- read.csv(coldata_file, stringsAsFactors = FALSE)

  raw <- if (identical(cohort_cfg$data_type, "counts")) {
    load_ncbi_counts(acc, dest, ANN)
  } else NULL
  if (is.null(raw)) raw <- load_raw_matrix(acc, cohort_cfg$data_type, dest)
  if (is.null(raw)) {
    cat("  [SKIP] no raw matrix found under", dest, "\n")
    return(invisible(NULL))
  }
  cat("  raw matrix:", nrow(raw), "features x", ncol(raw), "samples\n")

  samples <- intersect(cd$sample, colnames(raw))
  if (length(samples) < 2) {
    cat("  [WARN] fewer than 2 overlapping samples; check sample ids.\n")
    cat("         coldata sample[1:5]:", paste(head(cd$sample, 5), collapse = ", "), "\n")
    cat("         matrix  colnames[1:5]:", paste(head(colnames(raw), 5), collapse = ", "), "\n")
    return(invisible(NULL))
  }
  raw <- raw[, samples, drop = FALSE]
  cd  <- cd[match(samples, cd$sample), , drop = FALSE]

  norm_obj <- normalise_cohort(raw, cohort_cfg$data_type)
  expr_gene_x_samp <- norm_obj$norm
  cat("  genes after filtering:", nrow(expr_gene_x_samp), "\n")

  # --- QC metrics ---
  lib_size <- if (!is.null(norm_obj$filtered)) colSums(norm_obj$filtered) else colSums(raw)
  detected <- colSums(expr_gene_x_samp > 0)
  qc_df <- data.frame(sample = colnames(expr_gene_x_samp),
                      cohort = acc,
                      cell_line = cd$cell_line,
                      condition = cd$condition,
                      lib_size = lib_size[colnames(expr_gene_x_samp)],
                      detected = detected)
  write.csv(qc_df, file.path(TAB, paste0(acc, "_qc_metrics.csv")), row.names = FALSE)

  # --- PCA ---
  v <- apply(expr_gene_x_samp, 1, stats::var)
  top <- order(v, decreasing = TRUE)[seq_len(min(2000, sum(is.finite(v))))]
  X <- t(expr_gene_x_samp[top, , drop = FALSE])
  X <- scale(X)
  pca <- stats::prcomp(X, center = FALSE, scale. = FALSE)
  pv <- round(100 * summary(pca)$importance[2, 1:2], 1)
  pca_df <- data.frame(PC1 = pca$x[, 1], PC2 = pca$x[, 2],
                       condition = cd$condition, cell_line = cd$cell_line,
                       sample = cd$sample)
  if (has_pkg("ggplot2")) {
    p <- ggplot2::ggplot(pca_df, ggplot2::aes(PC1, PC2, color = condition, shape = cell_line)) +
      ggplot2::geom_point(size = 3) +
      ggplot2::labs(title = paste("PCA -", acc),
                    x = paste0("PC1 (", pv[1], "%)"),
                    y = paste0("PC2 (", pv[2], "%)")) +
      ggplot2::theme_bw(base_size = 13)
    ggplot2::ggsave(file.path(FIG, paste0(acc, "_PCA.png")), p, width = 6.5, height = 5, dpi = 300)
  }

  # --- Sample correlation heatmap (ggplot; pheatmap optional) ---
  corr <- stats::cor(expr_gene_x_samp, method = "spearman")
  if (has_pkg("pheatmap")) {
    png(file.path(FIG, paste0(acc, "_sample_correlation.png")),
        width = max(6, ncol(corr) * 0.5) * 100, height = max(6, ncol(corr) * 0.5) * 100,
        res = 100)
    pheatmap::pheatmap(corr, main = paste("Sample correlation -", acc))
    dev.off()
  } else {
    corr_heatmap_ggplot(corr, cd, paste("Sample correlation (Spearman) -", acc),
                        file.path(FIG, paste0(acc, "_sample_correlation.png")))
  }

  # --- Save samples x genes processed matrix for ML ---
  expr_samp_x_gene <- t(expr_gene_x_samp)
  save_processed(expr_samp_x_gene, acc, dest)
  write.csv(cd, file.path(dest, "coldata.csv"), row.names = FALSE)  # keep aligned

  cat("  QC complete (method:", norm_obj$method, ")\n")
  invisible(expr_samp_x_gene)
}

qc_cohort(cfg$cohorts$discovery$accession,  cfg$cohorts$discovery)
qc_cohort(cfg$cohorts$validation$accession, cfg$cohorts$validation)

cat("\nPhase 2 complete. Figures in", FIG, "\n")

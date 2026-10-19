#!/usr/bin/env Rscript
# 02b - VST extension for the D7 washout sensitivity check.
#
# Refits DESeq2 VST on ALL samples of the validation cohort (kept + the excluded
# acute/washout time-course + HCC2935) WITHOUT touching the primary
# expression_processed.{rds,csv} produced by 02_preprocess_qc.R (18 samples).
# Same construction rules as the primary pipeline: load_ncbi_counts
# (Entrez->symbol, duplicate-symbol collapse + n_dup log), low-count filter
# (rowSums >= cfg$deg$min_count), blind VST (design ~ 1).
#
# Outputs (under data/<ACC>/):
#   expression_vst_extend.csv  genes x ALL samples (VST space)
#   washout_ext_coldata.csv    sample, cell_line, group, keep, title
#
# Run (Linux host): /path/to/Rscript scripts/02b_vst_extend.R
suppressPackageStartupMessages({ library(yaml); library(data.table) })
source(file.path(if (dir.exists("scripts")) "scripts" else ".", "R_utils.R"))
PROJ <- resolve_root()
cfg  <- load_config(PROJ)

ACC  <- cfg$cohorts$validation$accession
dest <- file.path(PROJ, cfg$paths$data, ACC)
ann  <- file.path(PROJ, cfg$paths$annotation)
MIN_COUNT <- cfg$deg$min_count

cat("== 02b VST extension:", ACC, "==\n")
m <- load_ncbi_counts(ACC, dest, ann)
stopifnot(!is.null(m))

cd <- data.table::fread(file.path(dest, "coldata_all.csv"), data.table = FALSE)
common <- intersect(colnames(m), cd$geo_id)
m  <- m[, common, drop = FALSE]
cd <- cd[match(common, cd$geo_id), , drop = FALSE]
cat("  samples in matrix x coldata_all:", length(common), "\n")

keep <- rowSums(m) >= MIN_COUNT
m2 <- m[keep, , drop = FALSE]
cat("  genes after low-count filter (rowSums >=", MIN_COUNT, "):", nrow(m2), "\n")

method <- "vst"
if (requireNamespace("DESeq2", quietly = TRUE)) {
  cat("  normalisation: DESeq2 VST (blind, refit on ALL samples)\n")
  coldata <- data.frame(condition = factor(rep("A", ncol(m2))),
                        row.names = colnames(m2))
  dds  <- DESeq2::DESeqDataSetFromMatrix(round(m2), coldata, ~ 1)
  vsd  <- DESeq2::vst(dds, blind = TRUE)
  X    <- SummarizedExperiment::assay(vsd)
} else {
  cat("  [WARN] DESeq2 not installed - falling back to log2(CPM+1)\n")
  method <- "log2cpm"
  cpm <- sweep(m2, 2, colSums(m2), "/") * 1e6
  X   <- log2(cpm + 1)
}

out <- data.frame(gene = rownames(X), X, check.names = FALSE)
data.table::fwrite(out, file.path(dest, "expression_vst_extend.csv"))
cat("  wrote expression_vst_extend.csv:", nrow(X), "genes x", ncol(X),
    "samples (method =", method, ")\n")

grp <- function(t) {
  t <- tolower(t)
  if (grepl("osi_dtp|[^a-z]dtp", t)) "DTP"
  else if (grepl("dmso|untreated|parental|cells rep", t)) "Parental_or_DMSO"
  else if (grepl("acute", t)) "osi_acute"
  else if (grepl("short_washout", t)) "short_washout"
  else if (grepl("72h", t)) "long_washout_72h"
  else if (grepl("96h", t)) "long_washout_96h"
  else if (grepl("10d", t)) "long_washout_10d"
  else if (grepl("7d", t)) "long_washout_7d"
  else if (grepl("washout", t)) "long_washout"
  else "other"
}
ext <- data.frame(
  sample    = cd$geo_id,
  cell_line = cd$cell_line,
  group     = vapply(cd$title, grp, character(1)),
  keep      = cd$keep,
  title     = cd$title,
  stringsAsFactors = FALSE
)
data.table::fwrite(ext, file.path(dest, "washout_ext_coldata.csv"))
cat("  group counts:\n"); print(table(ext$group, ext$keep))
cat("wrote washout_ext_coldata.csv\n")

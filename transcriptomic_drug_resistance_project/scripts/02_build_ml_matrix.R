#!/usr/bin/env Rscript
# ============================================================
# BioDB Project — Member 3: Build ML Feature Matrix
# Datasets: GSE303889 (SKOV-3) + GSE283381 (OVCAR5)
#
# Creates a samples x genes expression matrix using the FULL
# intersected gene space (all genes present in both datasets).
# Feature selection is deferred entirely to the ML script (03)
# so that it is nested inside each training fold — no gene
# filtering based on both datasets occurs here.
#
# The DEG-overlap panel (418 consistently regulated genes) is
# saved separately for reference but is NOT used to restrict
# the ML feature space.
#
# Outputs:
#   results/ml/expression_matrix.rds  (matrix: 12 samples x all genes, log2(CPM+1))
#   results/ml/expression_matrix.csv  (same, human-readable; slow to read back)
#   results/ml/labels.csv             (sample / dataset / condition)
# ============================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
})

set.seed(42)

# Resolve project root (works on the Linux host and this Windows machine)
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

DATA  <- file.path(PROJ, "data")
RESULTS <- file.path(PROJ, "results")
MLOUT <- file.path(RESULTS, "ml")

dir.create(MLOUT, recursive = TRUE, showWarnings = FALSE)

# ============================================================
# 1. Load shared DEG list (for reference only — not used to
#    restrict ML features)
# ============================================================
shared <- read.csv(file.path(RESULTS, "comparison", "overlapping_DEGs.csv"),
                   stringsAsFactors = FALSE)
cat("Shared DEGs total:", nrow(shared), "\n")
cat("  Up:  ", sum(shared$direction == "Up"), "\n")
cat("  Down:", sum(shared$direction == "Down"), "\n")
cat("  Mixed:", sum(shared$direction == "Mixed"), "\n")
cat("(DEG overlap saved for reference; ML uses full gene space)\n")

# ============================================================
# 2. Normalization helpers: log2(CPM + 1)
# ============================================================
log2_cpm <- function(mat) {
  cpm <- sweep(mat, 2, colSums(mat), "/") * 1e6
  log2(cpm + 1)
}

# Aggregate counts to unique gene symbols (sum duplicated rows), if any
collapse_to_symbols <- function(count_mat, symbol_vec) {
  if (anyDuplicated(symbol_vec) == 0) {
    rownames(count_mat) <- symbol_vec
    return(count_mat)
  }
  cat("  Aggregating duplicated gene symbols...\n")
  # rowsum() already assigns row names = the group levels, in its own
  # (sorted) order. Overwriting them with unique(symbol_vec) — which is in
  # first-appearance order — would permute the data onto the wrong genes.
  sums <- rowsum(count_mat, group = symbol_vec, reorder = TRUE)
  stopifnot(setequal(rownames(sums), unique(as.character(symbol_vec))),
            nrow(sums) == length(unique(as.character(symbol_vec))))
  sums
}

# ============================================================
# 3. Dataset 1: GSE303889 (SKOV-3), Ensembl IDs + gene names
#    Columns -> coldata: dKO_NT_* = Sensitive, CDDP/CDDK_NT_* = Resistant
# ============================================================
cat("\n== GSE303889 (SKOV-3) ==\n")
c1 <- read.csv(file.path(DATA, "GSE303889", "counts_filtered.csv"), check.names = FALSE)
samp1 <- c("dKO_NT_1", "dKO_NT_2", "dKO_NT_3",
           "CDDP_NT_1", "CDDK_NT_2", "CDDK_NT_3")
new1  <- c("Parental_rep1", "Parental_rep2", "Parental_rep3",
           "Resistant_rep1", "Resistant_rep2", "Resistant_rep3")

mat1_raw <- as.matrix(c1[, samp1])
mat1_raw <- collapse_to_symbols(mat1_raw, c1$gene_name)
mat1 <- log2_cpm(mat1_raw)
colnames(mat1) <- new1
cat("Samples:", ncol(mat1), " Genes:", nrow(mat1), "\n")

# ============================================================
# 4. Dataset 2: GSE283381 (OVCAR5), gene symbols
#    Map GEO ids -> conditions (from 01_DEG_analysis.R samples2)
# ============================================================
cat("\n== GSE283381 (OVCAR5) ==\n")
c2 <- read.csv(file.path(DATA, "GSE283381", "counts_filtered.csv"), check.names = FALSE)
samp2 <- c("GSM8661174", "GSM8661175", "GSM8661176",
           "GSM8661180", "GSM8661181", "GSM8661182")
new2  <- c("OVCAR5_Sensitive_rep1", "OVCAR5_Sensitive_rep2", "OVCAR5_Sensitive_rep3",
           "OVCAR5_Resistant_rep1", "OVCAR5_Resistant_rep2", "OVCAR5_Resistant_rep3")

mat2_raw <- as.matrix(c2[, samp2])
mat2_raw <- collapse_to_symbols(mat2_raw, c2$gene_name)
mat2 <- log2_cpm(mat2_raw)
colnames(mat2) <- new2
cat("Samples:", ncol(mat2), " Genes:", nrow(mat2), "\n")

# ============================================================
# 5. Intersect feature space + combine samples
#    NOTE: Use ALL genes present in both datasets.
#          No DEG-based filtering — that would leak information
#          from both datasets into the ML feature space.
# ============================================================
features <- intersect(rownames(mat1), rownames(mat2))
cat("\nFull intersected gene space (no DEG filter):", length(features), "\n")
cat("  Of which are consistently-regulated shared DEGs:",
    sum(features %in% (shared %>% filter(direction %in% c("Up","Down")) %>%
                         pull(gene_name))), "\n")

expr <- cbind(mat1[features, , drop = FALSE],
              mat2[features, , drop = FALSE])
X <- as.data.frame(t(expr))      # samples (rows) x genes (cols)
X$sample <- rownames(X)
X <- X[, c("sample", setdiff(colnames(X), "sample"))]

# ============================================================
# 6. Labels/metadata
# ============================================================
labels <- data.frame(
  sample    = rownames(X),
  dataset   = c(rep("GSE303889_SKOV3", 6), rep("GSE283381_OVCAR5", 6)),
  condition = c(rep(c("Sensitive", "Sensitive", "Sensitive",
                      "Resistant", "Resistant", "Resistant"), 2)),
  stringsAsFactors = FALSE
)

# Numeric matrix (samples x genes) with rownames = sample id. This is the
# format the ML script (03) loads via readRDS(), which is ~1000x faster than
# read.csv() on a 57k-column table of the same data.
expr_mat <- as.matrix(X[, setdiff(colnames(X), "sample"), drop = FALSE])
storage.mode(expr_mat) <- "double"
rownames(expr_mat) <- X$sample

saveRDS(expr_mat, file.path(MLOUT, "expression_matrix.rds"))
write.csv(X,     file.path(MLOUT, "expression_matrix.csv"), row.names = FALSE)
write.csv(labels, file.path(MLOUT, "labels.csv"), row.names = FALSE)

cat("\nWrote:\n")
cat("  ", file.path(MLOUT, "expression_matrix.rds"), "\n")
cat("  ", file.path(MLOUT, "expression_matrix.csv"), "\n")
cat("  ", file.path(MLOUT, "labels.csv"), "\n")
cat("Dimensions:", nrow(X), "samples x", ncol(X) - 1, "genes\n")
cat("  (Full intersected gene space — feature selection deferred to 03_ML_biomarkers.R)\n")
cat("\nML feature matrix build complete.\n")
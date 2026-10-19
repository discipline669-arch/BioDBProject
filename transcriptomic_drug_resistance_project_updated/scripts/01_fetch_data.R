#!/usr/bin/env Rscript
# ============================================================
# Phase 1a - Dataset acquisition (NSCLC / osimertinib)
#   discovery : GSE202859  (parental vs -OR, PC9/H1975/HCC827)
#   validation: GSE193258  (DMSO vs osi_DTP 3w, PC9/H1975/HCC827)
#
# Downloads, per cohort:
#   * NCBI uniformly-reprocessed raw counts (GRCh38.p13, Entrez GeneID)
#       URL pattern: geo/download?type=rnaseq_counts&acc=<ACC>&format=file&file=<ACC>_raw_counts_GRCh38.p13_NCBI.tsv.gz
#   * GEO series matrix (sample metadata)
#   * (optional) author supplementary matrices, kept for provenance
# Plus a shared gene annotation (NCBI gene_info, GeneID -> Symbol).
#
# Idempotent: existing files are skipped. Network failures fall back to
# manual-download instructions.
#
# Run: Rscript scripts/01_fetch_data.R
# ============================================================

suppressPackageStartupMessages({ library(yaml) })
set.seed(42)

resolve_root <- function() {
  p <- Sys.getenv("BIODB_PROJ_UPDATED", unset = "")
  if (p != "" && dir.exists(p)) return(p)
  here <- getwd()
  # No absolute machine paths are baked in (portability); see R_utils.R.
  if (file.exists(file.path(here, "config", "config.yaml")))
    return(normalizePath(here))
  here
}
PROJ <- resolve_root()
cfg  <- yaml::read_yaml(file.path(PROJ, "config", "config.yaml"))
DATA <- file.path(PROJ, cfg$paths$data)
ANN  <- file.path(PROJ, cfg$paths$annotation)
dir.create(ANN, recursive = TRUE, showWarnings = FALSE)

accessions <- c(cfg$cohorts$discovery$accession,
                cfg$cohorts$validation$accession)
cat("Cohorts to fetch:", paste(accessions, collapse = ", "), "\n")

`%||%` <- function(a, b) if (is.null(a)) b else a

series_folder <- function(acc) sub("[0-9]{3}$", "nnn", acc)
ncbi_counts_url <- function(acc) sprintf(
  "https://www.ncbi.nlm.nih.gov/geo/download/?type=rnaseq_counts&acc=%s&format=file&file=%s_raw_counts_GRCh38.p13_NCBI.tsv.gz",
  acc, acc)
series_matrix_url <- function(acc) sprintf(
  "https://ftp.ncbi.nlm.nih.gov/geo/series/%s/%s/matrix/%s_series_matrix.txt.gz",
  series_folder(acc), acc, acc)
suppl_url <- function(acc, file) sprintf(
  "https://ftp.ncbi.nlm.nih.gov/geo/series/%s/%s/suppl/%s",
  series_folder(acc), acc, file)

AUTHOR_SUPPL <- list(
  GSE202859 = c("GSE202859_TPMs_allsamples.txt.gz"),
  GSE193258 = c("GSE193258_RNAseq_estimated_counts.tsv.gz",
                "GSE193258_RNAseq_log2TPM_abundance.tsv.gz")
)

download_if_missing <- function(url, dest, label = NULL) {
  dir.create(dirname(dest), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(dest) && file.info(dest)$size > 0) {
    cat("  present:", basename(dest), "\n"); return(TRUE)
  }
  cat("  downloading", label %||% basename(dest), "...\n")
  ok <- tryCatch({
    utils::download.file(url, dest, mode = "wb", quiet = TRUE)
    file.exists(dest) && file.info(dest)$size > 0
  }, error = function(e) {
    cat("    [WARN]", conditionMessage(e), "\n"); FALSE
  })
  if (ok) cat("    ->", basename(dest), "(", round(file.info(dest)$size/1e6, 2), "MB )\n")
  ok
}

fetch_cohort <- function(acc) {
  dest <- file.path(DATA, acc)
  dir.create(dest, recursive = TRUE, showWarnings = FALSE)
  cat("\n== Fetching", acc, "==\n")
  ok_counts <- download_if_missing(
    ncbi_counts_url(acc),
    file.path(dest, paste0(acc, "_raw_counts_GRCh38.p13_NCBI.tsv.gz")),
    paste(acc, "NCBI raw counts"))
  ok_series <- download_if_missing(
    series_matrix_url(acc),
    file.path(dest, paste0(acc, "_series_matrix.txt.gz")),
    paste(acc, "series matrix"))
  for (f in AUTHOR_SUPPL[[acc]]) {
    tryCatch(download_if_missing(suppl_url(acc, f), file.path(dest, f), f),
             error = function(e) cat("    [WARN] author file skipped:", f, "\n"))
  }
  isTRUE(ok_counts) && isTRUE(ok_series)
}

# Shared annotation for GeneID -> Symbol
download_if_missing(
  "https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz",
  file.path(ANN, "Homo_sapiens.gene_info.gz"), "Homo_sapiens gene_info")

results <- vapply(accessions, function(a) isTRUE(fetch_cohort(a)), logical(1))

if (any(!results)) {
  cat("\n============================================================\n")
  cat("  MANUAL DOWNLOAD FALLBACK\n")
  cat("============================================================\n")
  for (acc in accessions[!results]) {
    cat("\n", acc, ":\n", sep = "")
    cat("  counts :", ncbi_counts_url(acc), "\n")
    cat("  matrix :", series_matrix_url(acc), "\n")
    cat("  place both under data/", acc, "/\n", sep = "")
  }
}

cat("\nPhase 1a complete (fetch). Next: scripts/01_build_metadata.R\n")

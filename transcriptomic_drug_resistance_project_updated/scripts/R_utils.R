#!/usr/bin/env Rscript
# ============================================================
# Shared helpers for the R track (Phase 1-3).
# Source from scripts with: source(file.path(PROJ, "scripts", "R_utils.R"))
# ============================================================

suppressPackageStartupMessages({
  if (requireNamespace("yaml", quietly = TRUE)) library(yaml)
})

resolve_root <- function() {
  p <- Sys.getenv("BIODB_PROJ_UPDATED", unset = "")
  if (p != "" && dir.exists(p)) return(normalizePath(p))
  here <- getwd()
  cands <- c(here,
             "E:/BioDBProject/BioDBProject/transcriptomic_drug_resistance_project_updated",
             "/home/nianderbrox/BioDB_Project/transcriptomic_drug_resistance_project_updated")
  hit <- cands[dir.exists(cands) &
                 file.exists(file.path(cands, "config", "config.yaml"))]
  if (length(hit)) return(normalizePath(hit[1]))
  cands[dir.exists(cands)][1]
}

load_config <- function(PROJ) {
  yaml::read_yaml(file.path(PROJ, "config", "config.yaml"))
}

has_pkg <- function(p) requireNamespace(p, quietly = TRUE)

# ---------------------------------------------------------------
# Gene annotation: NCBI GeneID -> HGNC Symbol
# ---------------------------------------------------------------
# Reads data/annotation/Homo_sapiens.gene_info.gz (NCBI gene_info, tax 9606)
# and returns a data.frame(GeneID = character, Symbol = character).
load_gene_info <- function(annotation_dir) {
  path <- file.path(annotation_dir, "Homo_sapiens.gene_info.gz")
  if (!file.exists(path)) return(NULL)
  dt <- data.table::fread(path, header = TRUE, sep = "\t",
                          select = c(2L, 3L), showProgress = FALSE)
  names(dt) <- c("GeneID", "Symbol")
  dt$GeneID <- as.character(dt$GeneID)
  dt$Symbol <- as.character(dt$Symbol)
  unique(dt, by = "GeneID")
}

# ---------------------------------------------------------------
# Raw counts loader: NCBI uniformly-reprocessed matrix
#   <ACC>_raw_counts_GRCh38.p13_NCBI.tsv.gz
#   first column "GeneID" (Entrez), remaining columns are GSM ids.
# Returns a genes x samples numeric matrix with SYMBOL rownames
# (duplicate symbols are collapsed by summing counts).
# ---------------------------------------------------------------
load_ncbi_counts <- function(acc, dest, annotation_dir) {
  cands <- list.files(dest, pattern = "raw_counts.*NCBI.*\\.tsv\\.gz$",
                      full.names = TRUE)
  if (!length(cands)) return(NULL)
  pick <- cands[1]
  cat("  reading NCBI raw counts:", basename(pick), "\n")
  dt <- data.table::fread(pick, header = TRUE, data.table = FALSE,
                          check.names = FALSE)
  gene_ids <- as.character(dt[[1]])
  m <- as.matrix(dt[, -1, drop = FALSE])
  storage.mode(m) <- "double"
  rownames(m) <- gene_ids                       # Entrez GeneID

  ann <- load_gene_info(annotation_dir)
  if (!is.null(ann)) {
    sym <- ann$Symbol[match(rownames(m), ann$GeneID)]
    keep <- !is.na(sym)
    m <- m[keep, , drop = FALSE]
    rownames(m) <- make.unique(sym[keep])       # guarantee unique before collapse
    # collapse exact-duplicate symbols by summing
    m <- rowsum(m, group = sym[keep], reorder = TRUE)
    cat("  mapped", nrow(m), "gene symbols\n")
  } else {
    cat("  [WARN] gene_info missing; keeping Entrez GeneID rownames\n")
  }
  attr(m, "source") <- pick
  m
}

# ---------------------------------------------------------------
# Format-tolerant raw matrix loader (fallback: explicit matrix.csv
# or a user-supplied text/CSV matrix under data/<ACC>/).
# ---------------------------------------------------------------
load_raw_matrix <- function(acc, data_type, dest) {
  explicit <- file.path(dest, "matrix.csv")
  if (file.exists(explicit)) {
    m <- as.matrix(read.csv(explicit, row.names = 1, check.names = FALSE))
    attr(m, "source") <- "matrix.csv"
    return(m)
  }

  files <- list.files(dest, full.names = TRUE,
                      pattern = "\\.(txt|tsv|csv)(\\.gz)?$", recursive = TRUE)
  files <- files[!grepl("coldata|TEMPLATE|series_matrix|matrix\\.csv|raw_counts",
                        basename(files), ignore.case = TRUE)]
  if (!length(files)) return(NULL)

  hint <- switch(data_type,
                 tpm    = "TPM|tpm|profile",
                 counts = "count|Count|read|expr|matrix|FPKM|RPKM",
                 "expr")
  pref <- files[grepl(hint, basename(files))]
  pick <- if (length(pref)) pref[1] else files[1]
  cat("  reading raw matrix (fallback):", pick, "\n")

  df <- tryCatch(
    data.table::fread(pick, data.table = FALSE, check.names = FALSE),
    error = function(e) NULL
  )
  if (is.null(df) || ncol(df) < 2) return(NULL)

  rn <- as.character(df[[1]])
  m  <- as.matrix(df[, -1, drop = FALSE])
  rownames(m) <- rn
  storage.mode(m) <- "double"
  attr(m, "source") <- pick
  m
}

# ---------------------------------------------------------------
# Series matrix parser (no GEOquery needed).
# Returns list(gsm, title, chars = data.frame of characteristics).
# ---------------------------------------------------------------
read_series_matrix <- function(path) {
  if (!file.exists(path)) return(NULL)
  con <- gzfile(path, "rt")
  on.exit(close(con))
  lines <- readLines(con, warn = FALSE)

  grab <- function(tag) {
    ln <- lines[startsWith(lines, tag)]
    if (!length(ln)) return(NULL)
    vals <- strsplit(ln[1], "\t", fixed = TRUE)[[1]][-1]
    gsub('^"|"$', "", vals)
  }
  gsm   <- grab("!Sample_geo_accession")
  title <- grab("!Sample_title")
  if (is.null(gsm)) return(NULL)

  char_lines <- lines[startsWith(lines, "!Sample_characteristics_ch1")]
  chars <- NULL
  for (ln in char_lines) {
    vals <- strsplit(ln, "\t", fixed = TRUE)[[1]][-1]
    vals <- gsub('^"|"$', "", vals)
    key <- sub(":.*$", "", vals[1])
    val <- sub("^[^:]*:\\s*", "", vals)
    if (is.null(chars)) chars <- data.frame(row.names = gsm)
    chars[[make.names(key)]] <- val
  }
  list(gsm = gsm, title = title, chars = chars)
}

# ---------------------------------------------------------------
# Save a processed samples x genes matrix (RDS + CSV sidecar).
# The CSV sidecar is what the Python ML track reads.
# ---------------------------------------------------------------
save_processed <- function(mat_samp_by_gene, acc, dest, tag = "expression_processed") {
  rds <- file.path(dest, paste0(tag, ".rds"))
  saveRDS(mat_samp_by_gene, rds)
  df <- data.frame(sample = rownames(mat_samp_by_gene),
                   mat_samp_by_gene, check.names = FALSE)
  csv <- file.path(dest, paste0(tag, ".csv"))
  write.csv(df, csv, row.names = FALSE)
  cat("  wrote:", rds, "\n")
  cat("  wrote:", csv, "\n")
  invisible(rds)
}

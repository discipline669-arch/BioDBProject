#!/usr/bin/env Rscript
# ============================================================
# Phase 1b - Metadata / coldata construction (NSCLC / osimertinib)
#
# For each cohort, parse the GEO series matrix into a clean coldata and apply
# the label policy from docs/class_labels_resolved.md:
#     Sensitive : parental / DMSO (vehicle)
#     Resistant : -OR / osimertinib DTP 3w.
#     EXCLUDE   : acute 24 h, short/long washout, shRNA/perturbations,
#                 and any cell line not shared with the discovery cohort.
#
# Only the three shared lines (PC9, H1975, HCC827) are retained -> 9 vs 9.
# Sample identity is derived programmatically from the series matrix
# (never hard-coded), because the GSM lists in the strategy doc are offset.
#
# Outputs (per cohort, under data/<ACC>/):
#     coldata.csv       kept samples (Sensitive/Resistant), for modelling
#     coldata_all.csv   every sample with its raw label and keep/exclude reason
#
# Run: Rscript scripts/01_build_metadata.R
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

source(file.path(PROJ, "scripts", "R_utils.R"))

any_token <- function(x, toks) {
  if (!length(toks)) return(rep(FALSE, length(x)))
  pat <- paste(toks, collapse = "|")
  grepl(pat, x, ignore.case = TRUE)
}

line_from_title <- function(t) {
  t <- sub("\\(.*", "", t)
  first <- strsplit(trimws(t), "[ _]")[[1]][1]
  sub("-OR$", "", first, ignore.case = TRUE)
}

replicate_from_title <- function(t) {
  m <- regmatches(t, regexpr("(rep\\s*)?[0-9]+\\s*(\\)|$)", t))
  if (!length(m)) return(NA_integer_)
  as.integer(gsub("[^0-9]", "", m))
}

build_cohort <- function(acc, cohort_cfg) {
  dest <- file.path(DATA, acc)
  sm_file <- file.path(dest, paste0(acc, "_series_matrix.txt.gz"))
  cat("\n=== ", acc, " (", cohort_cfg$role, ") ===\n", sep = "")
  sm <- read_series_matrix(sm_file)
  if (is.null(sm)) { cat("  [SKIP] series matrix not found:", sm_file, "\n"); return(NULL) }

  n <- length(sm$gsm)
  title <- if (is.null(sm$title)) rep(NA_character_, n) else sm$title
  chars <- sm$chars
  cell_line_char <- if (!is.null(chars) && "cell.line" %in% names(chars)) {
    as.character(chars[["cell.line"]])
  } else rep(NA_character_, n)
  cell_line <- ifelse(is.na(cell_line_char) | cell_line_char == "",
                      vapply(title, line_from_title, character(1)), cell_line_char)

  lm_map <- cohort_cfg$label_map
  excluded <- any_token(title, lm_map$exclude_tokens)
  resistant <- any_token(title, lm_map$resistant_tokens)
  sensitive <- any_token(title, lm_map$sensitive_tokens)
  in_lines <- cell_line %in% cohort_cfg$lines
  off_lines <- !in_lines

  cond <- rep(NA_character_, n)
  cond[!excluded & resistant] <- "Resistant"
  cond[!excluded & !resistant] <- "Sensitive"    # non-excluded non-resistant = parental/DMSO

  reason <- rep("kept", n)
  reason[excluded]   <- "excluded_token"
  reason[off_lines]  <- "non_shared_line"
  keep <- cond %in% c("Sensitive", "Resistant") & in_lines

  all_df <- data.frame(
    sample    = sm$gsm,
    title     = title,
    cell_line = cell_line,
    condition = cond,
    cohort    = acc,
    donor     = cell_line,
    replicate = vapply(title, replicate_from_title, integer(1)),
    keep      = keep,
    reason    = reason,
    geo_id    = sm$gsm,
    stringsAsFactors = FALSE
  )
  kept <- all_df[all_df$keep, , drop = FALSE]

  cat("  parsed", n, "samples;", nrow(kept), "kept\n")
  print(table(kept$condition))
  exp <- cohort_cfg$expected
  if (!is.null(exp)) {
    for (c in names(exp)) {
      got <- sum(kept$condition == c, na.rm = TRUE)
      cat(sprintf("  %-10s expected %2d  got %2d  [%s]\n",
                  c, exp[[c]], got, if (got == exp[[c]]) "OK" else "CHECK"))
    }
  }

  write.csv(all_df[, c("sample", "title", "cell_line", "condition", "cohort",
                       "donor", "replicate", "keep", "reason", "geo_id")],
            file.path(dest, "coldata_all.csv"), row.names = FALSE)
  write.csv(kept[, c("sample", "title", "cell_line", "condition", "cohort",
                     "donor", "replicate", "geo_id")],
            file.path(dest, "coldata.csv"), row.names = FALSE)
  cat("  wrote: coldata.csv and coldata_all.csv\n")
  kept
}

cd_disc <- build_cohort(cfg$cohorts$discovery$accession,  cfg$cohorts$discovery)
cd_val  <- build_cohort(cfg$cohorts$validation$accession, cfg$cohorts$validation)

# --- cross-cohort shared-line sanity check -------------------------------
if (!is.null(cd_disc) && !is.null(cd_val)) {
  shared <- intersect(unique(cd_disc$cell_line), unique(cd_val$cell_line))
  cat("\nShared cell lines across cohorts:", paste(shared, collapse = ", "), "\n")
}

cat("\nPhase 1b complete. Next: scripts/02_preprocess_qc.R\n")

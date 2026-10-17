#!/usr/bin/env Rscript
# ============================================================
# Phase 0 - Project setup and governance
#   * create the directory skeleton
#   * record the environment / session info for reproducibility
#   * echo the leakage rules (from config/leakage_checklist.md)
#
# Run: Rscript scripts/00_setup.R
# ============================================================

suppressPackageStartupMessages({
  if (requireNamespace("yaml", quietly = TRUE)) library(yaml)
})

set.seed(42)

# --- Resolve project root -------------------------------------------------
resolve_root <- function() {
  p <- Sys.getenv("BIODB_PROJ_UPDATED", unset = "")
  if (p != "" && dir.exists(p)) return(p)
  here <- getwd()
  cands <- c(
    file.path(here),
    "E:/BioDBProject/BioDBProject/transcriptomic_drug_resistance_project_updated",
    "/home/nianderbrox/BioDB_Project/transcriptomic_drug_resistance_project_updated"
  )
  # Prefer a directory that contains config/config.yaml
  hit <- cands[dir.exists(cands) &
                 file.exists(file.path(cands, "config", "config.yaml"))]
  if (length(hit)) return(normalizePath(hit[1]))
  # Fall back to the first existing candidate
  cands[dir.exists(cands)][1]
}
PROJ <- resolve_root()
cat("Project root:", PROJ, "\n")

# --- Read config ----------------------------------------------------------
cfg_file <- file.path(PROJ, "config", "config.yaml")
if (file.exists(cfg_file) && requireNamespace("yaml", quietly = TRUE)) {
  cfg <- yaml::read_yaml(cfg_file)
  seed <- cfg$project$seed
  cat("Config loaded. seed =", seed, "\n")
} else {
  cfg <- NULL
  seed <- 42
  cat("config.yaml not found or 'yaml' missing; using defaults.\n")
}
set.seed(seed)

# --- Directory skeleton ---------------------------------------------------
dirs <- c(
  "config", "env", "scripts",
  "data", "data/_synthetic",
  "results", "results/figures", "results/tables",
  "results/models", "results/reports", "results/logs"
)
for (d in dirs) {
  dir.create(file.path(PROJ, d), recursive = TRUE, showWarnings = FALSE)
}
cat("Directory skeleton ensured under", PROJ, "\n")

# --- Reproducibility record ----------------------------------------------
if (!is.null(cfg)) {
  logdir <- file.path(PROJ, "results", "logs")
  dir.create(logdir, recursive = TRUE, showWarnings = FALSE)
  si <- file.path(logdir, "sessionInfo_setup.txt")
  sink(si)
  cat("Project:", cfg$project$name, "\n")
  cat("Generated:", format(Sys.time()), "\n\n")
  print(sessionInfo())
  sink()
  cat("Session info written to", si, "\n")
}

# --- Leakage rules echo ---------------------------------------------------
rules <- c(
  "Keep discovery and clinical cohorts separate (never pool for CV).",
  "Split by donor/patient; never split an isogenic pair.",
  "Feature selection, scaling and tuning happen inside training folds only.",
  "Touch the external clinical cohort exactly once, after locking the pipeline.",
  "Report the full model x feature-count grid and bootstrap confidence intervals.",
  "Fix seeds; two runs must produce identical predictions."
)
cat("\nLeakage rules (binding):\n")
for (r in rules) cat("  -", r, "\n")

cat("\nPhase 0 setup complete.\n")

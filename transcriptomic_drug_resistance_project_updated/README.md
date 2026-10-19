# Transcriptomic Profiling of Osimertinib-Resistant EGFR-mutant NSCLC

Leakage-safe RNA-seq classification built on two independent public bulk datasets
profiling the **same three EGFR-mutant NSCLC cell lines** (PC9, H1975, HCC827).

| Role | Accession | System | Comparison |
|---|---|---|---|
| Discovery | **GSE202859** | NSCLC cell lines | parental vs osimertinib-resistant (`-OR`) |
| Validation | **GSE193258** | NSCLC cell lines | DMSO vs osimertinib DTP (3 weeks) |

Scientific rationale, stage-by-stage plan and leakage controls live in `plan.md`.
Binding leakage rules are in `config/leakage_checklist.md`.

> **Claim discipline:** Only 3 cell lines (36 samples total, 18+18). Results are
> exploratory for candidate biomarker discovery, not clinical validation. Do not
> infer causality.

## Repository layout

```text
config/        config.yaml (single source of truth), leakage_checklist.md
env/           requirements.txt, R_packages.R
scripts/       R track (01-03, NCBI counts) + Python track (03b enrichment, 04-08) + 02b/03c/09/10 extension scripts + helpers
results/       tables/ figures/ models/ reports/ logs/
data/          <ACC>/... (NCBI counts, matrices, coldata, processed)
data/annotation/  Homo_sapiens.gene_info.gz, GO/KEGG/Reactome gene-set files
data/_synthetic/  synthetic smoke-test tree (never real data)
report.qmd     Quarto report
```

## Two tracks

- **R track (Phases 1-3)** — `scripts/01_fetch_data.R`, `01_build_metadata.R`, `02_preprocess_qc.R`, `03_deg_enrichment.R`.
  Downloads NCBI-harmonised raw counts/matrices (GEO FTP, no reCAPTCHA) and builds
  `coldata.csv` + `expression_processed.{rds,csv}`. DEG engine prioritizes DESeq2 if
  available; otherwise falls back to base-R OLS (`method` recorded per run). Functional
  enrichment is handled in the Python track (below), so no Bioconductor gene sets are needed.
- **Python track (Stage 5 + Phases 4-8)** — `scripts/03b_enrichment.py`, then
  `scripts/04_feature_selection.py` ... `08_report.py`. Stage 5 runs GO-BP (Enrichr GMT),
  KEGG and Reactome over-representation (hypergeometric + BH FDR) plus pre-ranked GSEA on
  the DEGs; group-aware (cell_line) nested CV, feature selection inside folds, once-only
  external validation (discovery→validation), SHAP interpretation, and report generation
  use scikit-learn/xgboost/shap. Locked models are persisted to `results/models/*.joblib`
  (`05_train_models.py`, via `ml.cv.fit_full`).

- **Extensions.** `02b_vst_extend.R` (blind VST refit on all 60 GSE193258 samples incl. the
  excluded osimertinib time-course arm, enabling D7), `10_washout_sensitivity.py` (applies locked
  discovery models to acute/washout samples; no accuracy claim — unsupervised drift analysis),
  `03c_fgsea_crosscheck.R` (R `fgsea` cross-check of the Python GSEA engine, D3),
  `09_upset.py` (deterministic UpSet-style overlap figure).

## Quick start (synthetic smoke test)

No Bioconductor needed. Generates fake NSCLC-shaped data (3 lines, 18+18 samples):

```bash
BIODB_SYNTHETIC=1 .venv/bin/python scripts/run_pipeline.py --synthetic --make
```

or on Windows/PowerShell:

```powershell
$env:BIODB_SYNTHETIC = "1"
python scripts/run_pipeline.py --synthetic --make
```

Outputs land in `results/tables`, `results/figures`, `results/models`, `results/reports/`.

## Running on real data (Windows)

Real data was downloaded via NCBI URLs/FTP (counts + series matrix + gene_info). R scripts
are self-contained and parse series matrices without GEOquery. The expected order is:

1. **Fetch + metadata + preprocess + DEGs** (R):
   ```r
   source("scripts/R_utils.R")
   source("scripts/01_fetch_data.R")
   source("scripts/01_build_metadata.R")  # -> data/<ACC>/coldata.csv, coldata_all.csv
   source("scripts/02_preprocess_qc.R")   # -> expression_processed.rds/csv
   source("scripts/03_deg_enrichment.R")   # -> DEG + cross-dataset overlap
   ```

2. **Enrichment + ML track** (Python, run in order; `run_pipeline.py` chains all steps):
   ```powershell
   $env:BIODB_SYNTHETIC = $null  # or unset
   python scripts/03b_enrichment.py   # Stage 5: GO-BP/KEGG/Reactome ORA + GSEA
   python scripts/run_pipeline.py
   ```

## Environment variables

| Variable | Effect |
|---|---|
| `BIODB_PROJ_UPDATED` | Override project root detection. All scripts resolve the project root from this variable or the current working directory (no hard-coded drive letters). |
| `BIODB_SYNTHETIC=1` | Read/write synthetic tree instead of `data/` |

All paths, cohorts, label maps, DEG thresholds, models/grid and CV are in `config/config.yaml`.

## Leakage controls (summary)

- Cohorts never pooled for CV; discovery and validation kept strictly separate.
- Splits group by `cell_line` (LOO-like 3-fold); replicates of a line never split.
- Feature selection, scaling and hyperparameter tuning run **inside training folds**.
- External validation cohort evaluated **once**, after the pipeline is locked.
- Full model × K grid reported, with stratified-bootstrap 95% CIs for external metrics.
- Label policy enforced by token-based KEEP/EXCLUDE (no acute/washout/shRNA).

## Quarto report

```bash
quarto render report.qmd
```
(Quarto optional; `rmarkdown/knitr` present in R 4.6.1.)

## Status

- R track (Phases 1-3) was re-run with **DESeq2/Bioconductor (April 2026)**: DEGs refreshed, the
  cross-dataset **validated DEG set is now 1112 genes** (previously 348 from the OLS era).
- The repo `.venv` (Linux) is the current Python host: `.venv/bin/python scripts/run_pipeline.py --synthetic`
  is the regression command; real-data re-runs of Stage 5 + Phases 4-8 are tracked in
  `docs/tasks_left.md` (A1/A2).
- Heavy data artefacts (downloaded counts/matrices, `data/annotation/` gene sets, the full-space
  `nested_cv_selection_freq.csv`) are **not committed** — reproduce them with
  `scripts/01_fetch_data.R` (sources documented in `docs/plan.md` §2) and
  `scripts/03b_enrichment.py` / `run_pipeline.py`.

See `plan.md` for full NSCLC scope and `roadmap.md` for phase gates.
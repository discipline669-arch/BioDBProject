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
scripts/       R track (01-03, NCBI counts) + Python track (03b enrichment, 04-08) + helpers
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
  use scikit-learn/xgboost/shap.

## Quick start (synthetic smoke test)

No Bioconductor needed. Generates fake NSCLC-shaped data (3 lines, 18+18 samples):

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
| `BIODB_PROJ_UPDATED` | Override project root detection |
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

Phases 1–3 (R) produce processed matrices and DEGs on real data. Stage 5 enrichment
(GO-BP/KEGG/Reactome ORA + GSEA) and Phases 4–8 (Python) are verified and run on real
NSCLC cohorts; see `results/tables/` for the deliverables.
See `plan.md` for full NSCLC scope and `roadmap.md` for phase gates.
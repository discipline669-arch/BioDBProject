# Roadmap — NSCLC osimertinib resistance

## Prerequisites
- Rscript = `C:\Program Files\R\R-4.6.1\bin\Rscript.exe`
- Python = `C:\Program Files\Python311\python.exe`
- Packages: see `env/R_packages.R` and `env/requirements.txt`

## Phases 1–3 (R, NCBI-based, no reCAPTCHA dependency)

### 1) Fetch data
- `scripts/01_fetch_data.R` downloads NCBI counts (`*_raw_counts_GRCh38.p13_NCBI.tsv.gz`), GEO series matrices, and `Homo_sapiens.gene_info.gz`. Falls back to manual if files exist.
- Exit: files in `data/<GSE>/` + `data/annotation/` present.

### 2) Build metadata
- `scripts/01_build_metadata.R` derives GSMs from series matrix, applies label policy (KEEP: parental/DMSO vs -OR/osi_DTP 3w), drops acute 24h/washout/shRNA/HCC2935. Enforces shared lines PC9/H1975/HCC827.
- Exit: `coldata.csv`, `coldata_all.csv`; 18/18 each.

### 3) Preprocess + QC + DEGs
- `02_preprocess_qc.R`: loads NCBI counts, maps Entrez→Symbol (gene_info), filters low-count, normalises. DESeq2 VST if Bioconductor present, else log2(CPM+1).
- `03_deg_enrichment.R`: `DESeq2→limma→ols` priority; cross-dataset overlap (consistent direction). Functional enrichment runs in Stage 5 (Python) instead.
- Exit: `expression_processed.{rds,csv}`, DEG CSVs, `cross_DEG_overlap.csv`, `validated_DEGs.csv`, QC/figures.

## Stage 5 — Functional enrichment (Python)

### 5) GO-BP / KEGG / Reactome ORA + GSEA
- `03b_enrichment.py`: downloads gene sets once into `data/annotation/` (GO-BP from an Enrichr GMT; KEGG from REST; Reactome from NCBI2Reactome). Runs hypergeometric over-representation with BH FDR and pre-ranked GSEA on discovery, validation and the validated signature, in gene-symbol space.
- Exit: `enrichment_<TAG>_<SOURCE>.csv`, `gsea_<TAG>_<SOURCE>.csv`, and dotplot/barplot figures.

## Phases 4–8 (Python, leakage-safe)

### 4) Feature selection
- `04_feature_selection.py`: univariate + elastic-net stability (grouped? EN on full cohort discovery but selection frequency recorded; thresholds configurable). Exports `feature_candidates_validation.csv`.
- Exit: candidates exist per (model-context/K).

### 5) Nested CV
- `05_train_models.py`: StratifiedGroupKFold by `cell_line`. For each fold: select → scale → tune (GridSearchCV, grouped inner CV) → predict. Reports OOF metrics, ROC/PR, confusion matrices, AUC-vs-K.
- Exit: `nested_cv_metrics.csv`, `oof_predictions.csv`, figures.

### 6) External validation (once)
- `06_validate_clinical.py`: lock pipeline to discovery; evaluate on GSE193258 under `train_stats` and `target_z` normalisation. Bootstrap 95% CIs. Includes `external_confusion.png`.
- Exit: `external_validation.csv`, transfer results, figures.

### 7) Interpretation
- `07_interpret.py`: SHAP for LR/RF/XGB (TreeExplainer/LinearExplainer). Builds composite `biomarker_panel.csv` (EN freq + nested selection freq + mean |SHAP|). SVM skipped gracefully.
- Exit: panel, SHAP plots.

### 8) Report
- `08_report.py`: writes `summary.md`, `session_info.txt`.
- Exit: reports present.

## Verify commands (real data)

```powershell
$env:BIODB_SYNTHETIC = $null
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" scripts/01_fetch_data.R
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" scripts/01_build_metadata.R
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" scripts/02_preprocess_qc.R
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" scripts/03_deg_enrichment.R
& "C:\Program Files\Python311\python.exe" scripts/03b_enrichment.py
& "C:\Program Files\Python311\python.exe" scripts/04_feature_selection.py
& "C:\Program Files\Python311\python.exe" scripts/05_train_models.py
& "C:\Program Files\Python311\python.exe" scripts/06_validate_clinical.py
& "C:\Program Files\Python311\python.exe" scripts/07_interpret.py
& "C:\Program Files\Python311\python.exe" scripts/08_report.py
# optional: quarto render report.qmd
```

## Quality gates

- Leakage checklist: all items OK.
- Cell-line balance: each cohort 9S/9R across 3 lines.
- Discovery vs validation kept separate.
- Confusion matrices rendered for nested and external.
- Claims are conservative (candidate biomarkers).

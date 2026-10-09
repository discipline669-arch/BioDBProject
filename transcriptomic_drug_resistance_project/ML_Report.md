# Machine Learning & Biomarker Discovery — Report Scaffold

**Status:** Pipeline authored and executed (R 4.4.2). Results below are from
`results/ml/` after running `02_build_ml_matrix.R` + `03_ML_biomarkers.R`.
Figures/metrics are also embedded in `scripts/DEG_Report.Rmd` →
`DEG_Report.html`.

---

## 1. Objective

Build supervised classifiers that distinguish **cisplatin-resistant** from
**cisplatin-sensitive** ovarian cancer cells using the cross-dataset validated
DEGs, and rank a small, biologically interpretable candidate **biomarker
panel** (proposal §7, §10).

## 2. Inputs

| Input | File | Notes |
|---|---|---|
| Feature matrix | `results/ml/expression_matrix.csv` | 12 samples × genes, `log2(CPM+1)` |
| Labels | `results/ml/labels.csv` | sample / dataset / condition |
| Candidate features | `results/comparison/overlapping_DEGs.csv` | Only **Up/Down** (418 genes); **Mixed** excluded |
| DESeq2 log2FC | `results/comparison/dataset{1,2}_annotated.csv` | For panel tie-breaking / biological context |

Feature-matrix construction:
`scripts/02_build_ml_matrix.R` — normalizes each dataset to CPM, transforms to
`log2(CPM+1)`, collapses duplicate symbols, and intersects the consistently
regulated shared DEGs.

## 3. Models & Validation

- **Models:** Logistic Regression (L1 / glmnet), Random Forest (ranger),
  SVM radial (e1071).
- **Nested feature selection:** inside every training fold only, top-K genes by
  |two-sample t-statistic|, K ∈ {10, 20, 30}. Test folds never inform feature
  or model selection (leakage prevention).
- **Validation:**
  1. **LOOCV** on all 12 samples.
  2. **Leave-one-dataset-out (external):** train on all 6 samples of one cell
     line, predict the other 6 (SKOV-3 → OVCAR5 and OVCAR5 → SKOV-3).
- **Metrics:** Accuracy, Precision, Recall, F1, ROC-AUC, confusion matrix.

## 4. How to Run

Requires **R** (≥ 4.2) on the analysis host with:

```r
install.packages(c("glmnet", "ranger", "e1071", "ggplot2", "dplyr", "tidyr"))
```

Run in order from the project root. The scripts auto-detect the project root
(Linux `/home/nianderbrox/BioDB_Project` **or** Windows
`E:/BioDBProject/transcriptomic_drug_resistance_project`); override with the
`BIODB_PROJ` environment variable if needed:

```bash
Rscript scripts/02_build_ml_matrix.R
Rscript scripts/03_ML_biomarkers.R
```

`03_ML_biomarkers.R` also writes a console log to `results/ml/run_log.txt`.

To regenerate the full report (DEG + ML) after the ML run:

```bash
Rscript -e 'rmarkdown::render("scripts/DEG_Report.Rmd")'
```

## 5. Expected Outputs (`results/ml/`)

| Output | Description |
|---|---|
| `expression_matrix.csv` | Sample × gene feature matrix |
| `labels.csv` | Sample metadata / labels |
| `ml_metrics_summary.csv` | Metrics per model × top-K × validation |
| `external_by_direction.csv` | External metrics per train→test direction |
| `predictions_LOOCV.csv` | Per-fold held-out predictions |
| `predictions_external.csv` | External predictions |
| `ROC_LOOCV.png`, `ROC_external.png` | ROC curves |
| `confusion_LOOCV.png` | Confusion matrix heatmaps |
| `feature_importance.csv`, `feature_importance.png` | Selection frequencies per gene/model |
| `biomarker_panel.csv` | Top-30 ranked candidate biomarkers |
| `run_log.txt` | Console log |

## 6. Results

### 6.1 Model performance (LOOCV, top-K = 20, n = 12)

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Random Forest | 0.917 | 0.857 | 1.000 | 0.923 | 1.000 |
| SVM | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

All K ∈ {10, 20, 30} give LOOCV accuracies ≥ 0.92 (see
`results/ml/ml_metrics_summary.csv`).

### 6.2 External validation (train one cell line → test the other; n = 6 training / 6 test)

Pooled across both directions (12 test samples), top-K = 20:

| Model | Accuracy | Recall | ROC-AUC | Note |
|---|---|---|---|---|
| Logistic Regression | 0.500 | 1.000 | 0.639 | Predicts all samples as Resistant (Precision 0.5) |
| Random Forest | 0.500 | 0.000 | 0.500 | Predicts all samples as Sensitive (K≥20) |
| SVM | 0.500 | 1.000 | 0.569 | RBF (radial) kernel, K∈{10,20} |

Per-direction AUCs are inconsistent (e.g., LR AUC = 1.0 for `SKOV3→OVCAR5`
but 0.0 for `OVCAR5→SKOV3`; SVM AUC 0.78 vs 0.5–0.33) — see
`results/ml/external_by_direction.csv`. **No model generalizes across cell
lines at chance-beating accuracy**, consistent with the small n and the
distinct resistance mechanisms of SKOV-3 vs OVCAR5.

### 6.3 Candidate biomarker panel (top 20)

Ranked by LOOCV selection frequency across models × K, tie-broken by mean
|log2FC| (source: `results/ml/biomarker_panel.csv`):

| Rank | Gene | Selected (of 9 slots) | Mean \|log2FC\| |
|---|---|---|---|
| 1 | MAGEB17 | 9 | 7.37 |
| 2 | WNT10A | 9 | 4.43 |
| 3 | FXYD2 | 9 | 4.01 |
| 4 | ELMO1 | 9 | 3.94 |
| 5 | NPTX1 | 9 | 2.86 |
| 6 | ZNF320 | 9 | 2.73 |
| 7 | SERPINF1 | 9 | 1.72 |
| 8 | LINC02454 | 9 | 2.21 |
| 9 | AFF3 | 9 | 2.78 |
| 10 | SLC5A10 | 9 | 4.72 |
| 11 | LHX6 | 9 | 1.36 |
| 12 | MSLN | 9 | 4.96 |
| 13 | KRTAP2-3 | 9 | 6.37 |
| 14 | AC005256.1 | 9 | 4.66 |
| 15 | GASAL1 | 9 | 2.11 |
| 16 | LINC01559 | 9 | 4.46 |
| 17 | FAM83B | 9 | 4.49 |
| 18 | AC109492.1 | 9 | 5.51 |
| 19 | KRT17 | 9 | 6.40 |
| 20 | TRPM8 | 9 | 3.78 |

Note: these are the 418 consistently-regulated DEGs that ranked consistently
during nested feature selection — candidates for follow-up, **not** a
clinically validated diagnostic panel.

## 7. Interpretation & Caveats

1. n = 12 total samples (6 per cell line); results are **exploratory biomarker
   discovery**, not clinical diagnostic validation (proposal §7).
2. The 418-gene candidate space derives from cross-dataset DESeq2 validation;
   ML feature selection is additionally nested inside folds to avoid leakage.
3. Within-CV separability may be inflated by cell-line (batch) background;
   external validation and direction-consistency of top biomarkers partially
   mitigate this.
4. **External generalization failed** (chance-level accuracy in both
   directions) at this n — the within-dataset ML signal is strong, but the two
   cell lines do not share a predictive cross-study transcriptomic signature
   under this design. This is an honest, reproducible null result that should
   be reported alongside the biomarker panel rather than hidden.
5. To discuss in the report: model ranking, feature-importance stability
   across K, and overlap of the biomarker panel with the GO/KEGG results
   (EMT / collagen remodeling, inflammation, PI3K-Akt).

Windows note: if `Rscript` is not on PATH, call it directly, e.g.
`& "C:\Program Files\R\R-4.4.2\bin\Rscript.exe" scripts/02_build_ml_matrix.R`.
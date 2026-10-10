# Machine Learning & Biomarker Discovery — Report

**Status:** Pipeline fixed and executed (R 4.4.2). Results below are from
`results/ml/` after running `02_build_ml_matrix.R` + `03_ML_biomarkers.R`.
Raw console output is in `results/ml/run_log.txt`. Figures/metrics are also
embedded in `scripts/DEG_Report.Rmd` → `DEG_Report.html`.

> See `fix_pipeline.md` for the defect list that was corrected in this pass
> (scrambled gene labels, a 30-min `read.csv` hang, NULL model seeds, a
> no-split Random Forest, lasso degeneracy at n = 6, an invalid pooled external
> metric, and cross-dataset scale mismatch).
>
> A follow-up methodology pass (see `documents/updated_plan.md`) made
> normalization fold-aware and reported a second, strictly non-transductive
> external scheme. See §3 for details.

---

## 1. Objective

Build supervised classifiers that distinguish **cisplatin-resistant** from
**cisplatin-sensitive** ovarian cancer cells and rank a small, interpretable
candidate **biomarker panel** (proposal §7, §10). The design prioritises
**cross-dataset validation**: the primary evidence is how well a model trained on
one cell line predicts the other, reported under both a batch-corrected
(`target_z`) and a strictly non-transductive (`train_stats`) normalization.

## 2. Inputs

| Input | File | Notes |
|---|---|---|
| Feature matrix (fast) | `results/ml/expression_matrix.rds` | 12 samples × **57,357** intersected genes, `log2(CPM+1)`; loaded with `readRDS` |
| Feature matrix (portable) | `results/ml/expression_matrix.csv` | Same matrix as a CSV sidecar (slow to read at this width) |
| Labels | `results/ml/labels.csv` | sample / dataset / condition |
| DESeq2 log2FC | `results/comparison/dataset{1,2}_annotated.csv` | For panel tie-breaking / biological context only |

Feature-matrix construction (`scripts/02_build_ml_matrix.R`): CPM-normalize each
dataset independently, transform to `log2(CPM+1)`, collapse duplicate symbols
with `rowsum(..., reorder = TRUE)` (DS1: 59,542 → 58,321; DS2: 58,734 unique),
then intersect → **57,357 shared genes**.

**Feature space:** the **full 57,357-gene space**, not a pre-selected DEG panel.
Any DEG-based pre-filtering would let test information leak into feature
selection, so feature selection is done **inside each training fold** instead.
The 418 consistently-regulated DEGs remain available as a reference panel only.

## 3. Models & Validation

- **Models:** Logistic Regression (ridge / L2, `glmnet`), Random Forest
  (`ranger`, `min.node.size = 1`), SVM radial (`e1071`).
- **Per-fold cross-dataset normalization:** the two studies were CPM-normalized
  independently, so genes sit on different scales (measured variance 0.172 vs
  0.047). Within each fold, **training rows are z-scored with training-row
  statistics**, and two test-row normalizations are reported:
  - **`target_z` (PRIMARY, transductive):** test rows are z-scored with the
    **test cell line's own** mean/SD. This batch-corrects the two datasets and is
    the reference result.
  - **`train_stats` (secondary, strict):** test rows are z-scored with the
    **training cell line's** mean/SD. It uses no information whatever from the
    held-out dataset — the leak-free number.

  The model is fit once per fold on the identically normalized training rows;
  only test-row normalization differs between the two schemes. No labels are used
  anywhere in normalization.
- **Nested feature selection:** inside every training fold only, top-K genes by
  |two-sample t-statistic|, **K ∈ {20, 50, 100, 200, 500}**. Test folds never
  inform feature or model selection.
- **Validation:**
  1. **PRIMARY — cross-dataset external:** train on all 6 samples of one cell
     line, predict the other 6 (SKOV-3 → OVCAR5 and OVCAR5 → SKOV-3), under both
     normalizations above.
  2. **SECONDARY — within-cell-line LOOCV:** leave-one-out **inside each cell
     line** (5 training samples, 1 held out), with feature selection and
     normalization recomputed from the training samples only. Not a pooled
     12-sample CV.
- **Metrics:** Accuracy, Precision, Recall, F1, ROC-AUC. External metrics are
  computed **per direction × normalization** (`external_by_direction.csv`). The
  two directions have opposite probability scales, so pooling them into a single
  "External" row is not interpretable and is not reported.
- **Determinism:** fixed seeds per model; two consecutive runs produce
  byte-identical predictions and metrics.

### Model choices

- **LR — ridge (L2), `cv.glmnet`** with leave-one-out inner folds. Lasso
  (alpha = 1) is degenerate at n = 6: both fixed-λ and CV lasso paths collapse to
  near-constant / inverted test probabilities. Ridge is stable and matches the
  independent Python reference (`sklearn.LogisticRegression`, L2).
- **RF — `min.node.size = 1`.** `ranger(probability = TRUE)` defaults to
  `min.node.size = 10`; with only 6 training samples no node can ever split and
  every prediction is the constant root proportion.
- **SVM — radial kernel**, `scale = FALSE` (inputs are already standardized).

## 4. How to Run

Requires **R** (≥ 4.2) with:

```r
install.packages(c("dplyr","tidyr","ggplot2","glmnet","ranger","e1071"))
# DEG stage (separate host) additionally needs Bioconductor:
# BiocManager::install(c("DESeq2","EnhancedVolcano","clusterProfiler","org.Hs.eg.db"))
```

Run in order from the project root. The scripts auto-detect the project root
(Linux `/home/nianderbrox/BioDB_Project` or Windows
`E:/BioDBProject/BioDBProject/transcriptomic_drug_resistance_project`); override
with the `BIODB_PROJ` environment variable if needed:

```bash
Rscript scripts/02_build_ml_matrix.R
Rscript scripts/03_ML_biomarkers.R
```

`03_ML_biomarkers.R` writes a console log to `results/ml/run_log.txt` and
completes in ~25 s. To regenerate the combined report:

```bash
Rscript -e 'rmarkdown::render("scripts/DEG_Report.Rmd")'
```

## 5. Outputs (`results/ml/`)

| Output | Description |
|---|---|
| `expression_matrix.rds` | Sample × gene feature matrix (fast load) |
| `expression_matrix.csv` | Same matrix, CSV sidecar |
| `labels.csv` | Sample metadata / labels |
| `ml_metrics_summary.csv` | Metrics per validation × model × top-K × direction × normalization |
| `external_by_direction.csv` | **Primary** external metrics per train→test direction × normalization (60 rows) |
| `predictions_external.csv` | Per-sample external predictions, both normalizations (360 rows) |
| `predictions_LOOCV.csv` | Per-sample held-out within-cell-line LOOCV predictions (180 rows) |
| `ROC_external.png`, `ROC_external_trainstats.png`, `ROC_LOOCV.png` | ROC curves (external target_z, external strict, LOOCV) |
| `confusion_external.png` | External confusion matrix heatmaps (target_z) |
| `feature_importance.csv`, `feature_importance.png` | Selection frequencies per gene/model |
| `biomarker_panel.csv` | Top-30 ranked candidate biomarkers |
| `run_log.txt` | Full console log |

## 6. Results

### 6.1 Within-cell-line LOOCV (secondary, n = 12)

Leave-one-out inside each cell line, with preprocessing recomputed per fold
(`ml_metrics_summary.csv`, `validation = LOOCV`):

| Model | K = 20 | K = 50 | K = 100 | K = 200 | K = 500 |
|---|---|---|---|---|---|
| Logistic Regression (Acc / AUC) | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| Random Forest (Acc / AUC) | 1.000 / 1.000 | 1.000 / 1.000 | 0.917 / 1.000 | 0.917 / 0.972 | 0.917 / 1.000 |
| SVM (Acc / AUC) | 1.000 / 1.000 | 1.000 / 1.000 | 0.833 / 0.972 | 0.833 / 0.972 | 0.833 / 0.889 |

Minimum across the grid: **Accuracy 0.833, ROC-AUC 0.889**. The two phenotypes
remain almost trivially separable *within* a cell line; because this CV no longer
pools the two cell lines (and no longer lets the held-out sample contribute to
its own normalization), it is a legitimate within-study reference rather than an
inflated one.

### 6.2 Cross-dataset external validation — `target_z` (primary, n = 6 train / 6 test)

Accuracy / ROC-AUC per train → test direction (`external_by_direction.csv`,
`normalization = target_z`):

| Model | K | SKOV3→OVCAR5 (Acc / AUC) | OVCAR5→SKOV3 (Acc / AUC) |
|---|---|---|---|
| Logistic Regression | 20 | **1.000 / 1.000** | 0.500 / 0.556 |
| Logistic Regression | 50 | **1.000 / 1.000** | 0.333 / 0.444 |
| Logistic Regression | 100 | 0.667 / 0.556 | 0.500 / 0.556 |
| Logistic Regression | 200 | 0.000 / 0.000 | 0.667 / 0.667 |
| Logistic Regression | 500 | 0.333 / 0.222 | 0.667 / 0.667 |
| Random Forest | 20 | **1.000 / 1.000** | 0.333 / 0.556 |
| Random Forest | 50 | **1.000 / 1.000** | 0.500 / 0.611 |
| Random Forest | 100 | 0.833 / 0.778 | 0.500 / 0.444 |
| Random Forest | 200 | 0.333 / 0.000 | 0.667 / 0.667 |
| Random Forest | 500 | 0.167 / 0.000 | **1.000 / 1.000** |
| SVM | 20 | **1.000 / 1.000** | 0.500 / 0.556 |
| SVM | 50 | **1.000 / 1.000** | 0.500 / 0.444 |
| SVM | 100 | 0.500 / 0.556 | 0.500 / 0.556 |
| SVM | 200 | 0.333 / 0.000 | 0.500 / 0.667 |
| SVM | 500 | 0.333 / 0.222 | 0.500 / 0.778 |

Key observations:

1. **SKOV3→OVCAR5 carries a transferable signal at small K**: all three models
   hit AUC = 1.000 at K = 20 (LR/SVM also at K = 50). This is the clean case
   that matches the independent Python replication (LR K = 20 probs
   `0.423 / 0.420 / 0.395` for sensitive vs `0.555 / 0.612 / 0.595` for
   resistant → AUC 1.0).
2. **The signal collapses as K grows**: at K = 200–500, adding weakly-informative
   genes drives AUC to 0.0–0.22 — a classic n ≪ p overfitting signature with a
   6-sample training set.
3. **OVCAR5→SKOV3 does not generalize** (AUC ≈ 0.44–0.78, mostly near chance).
   Only RF at K = 500 crosses AUC = 1.0, which is not consistent across models
   or K and should not be over-interpreted.
4. **Direction asymmetry** is the dominant feature of the results: the model
   learned on SKOV-3 transfers to OVCAR5 at small K, but not vice versa.

These numbers are **unchanged** from the pre-pass pipeline: `target_z` reproduces
the previous output exactly (per-gene differences 0).

### 6.3 Cross-dataset external validation — `train_stats` (strict, leak-free)

Same models, but the test cell line is normalized with the **training** line's
statistics, so not a single value from the held-out dataset informs
preprocessing. Summary over the 3 × 5 × 2 = 30 grid
(`external_by_direction.csv`, `normalization = train_stats`):

- Mean ROC-AUC **≈ 0.61**; 12 of 30 cells hit AUC = 1.0 but these are not
  consistent across K, model, or direction.
- **Accuracy is never 1.0** (all cells ≤ 0.83, median 0.50): because the test
  features are centred/scaled by the *training* line, the predicted probabilities
  are miscalibrated and cluster on one side of 0.5, so thresholding at 0.5
  assigns essentially one class. AUC (rank-based) is the meaningful metric here;
  Accuracy/Precision are threshold artefacts under this scheme.

Interpretation: once cross-dataset normalization is made strictly
non-transductive, the SKOV3→OVCAR5 transfer at small K weakens or disappears for
most cells. The earlier `target_z` AUC = 1.0 result depends on standardizing the
held-out batch with its own statistics, which is common practice in cross-study
batch correction but is **not** a locked, deployable model.

### 6.4 Candidate biomarker panel (top 20)

Ranked by cross-dataset selection frequency across models × K, tie-broken by
mean |log2FC| (`results/ml/biomarker_panel.csv`). `n_select_slots` is out of 15
model×K slots:

| Rank | Gene | Slots (of 15) | Mean freq | Mean \|log2FC\| |
|---|---|---|---|---|
| 1 | MAL2 | 15 | 0.80 | 6.55 |
| 2 | GALNT6 | 15 | 0.70 | 5.95 |
| 3 | LDOC1 | 15 | 0.50 | 13.07 |
| 4 | SH2D4A | 15 | 0.50 | 11.93 |
| 5 | FBXL21P | 15 | 0.50 | 11.31 |
| 6 | EPB41L3 | 15 | 0.50 | 11.05 |
| 7 | TMEM218 | 15 | 0.50 | 10.89 |
| 8 | CALB1 | 15 | 0.50 | 9.75 |
| 9 | LINC02582 | 15 | 0.50 | 9.71 |
| 10 | CELF2 | 15 | 0.50 | 9.04 |
| 11 | DCAF12L2 | 15 | 0.50 | 8.95 |
| 12 | ZNF845 | 15 | 0.50 | 8.22 |
| 13 | TCF4 | 15 | 0.50 | 7.84 |
| 14 | PAEPP1 | 15 | 0.50 | 7.79 |
| 15 | GRHL2 | 15 | 0.50 | 6.81 |
| 16 | MBNL3 | 15 | 0.50 | 6.80 |
| 17 | ARHGEF9 | 15 | 0.50 | 6.48 |
| 18 | ZNF462 | 15 | 0.50 | 6.35 |
| 19 | ZNF518A | 15 | 0.50 | 6.19 |
| 20 | OVOL1 | 15 | 0.50 | 5.91 |

These genes are consistently selected from the **full 57,357-gene space** during
nested cross-dataset feature selection. Selection frequency is dominated by the
SKOV3→OVCAR5 direction (hence the 0.50 plateau), so the panel reflects
candidates for follow-up rather than a validated, directionally-consistent
signature. **Not a clinically validated diagnostic panel.**

## 7. Interpretation & Caveats

1. n = 12 total samples (6 per cell line). These results are **exploratory
   biomarker discovery**, not clinical diagnostic validation (proposal §7).
2. **Leakage control:** feature selection is nested inside every training fold.
   Two normalization schemes are reported: `target_z` (test line standardized
   with its own statistics — *transductive*, common in cross-study batch
   correction but not deployable on a single unseen sample) and `train_stats`
   (test line standardized with training statistics — strictly non-transductive).
   Only the latter is fully leak-free; the two bracket the possible range.
3. **Within-cell-line separability is near-complete** (LOOCV min AUC = 0.889)
   but likely inflated by cell-line (batch) background; the external,
   per-direction test is the meaningful yardstick.
4. **Cross-dataset generalization is partial and asymmetric, and depends on the
   normalization:** under `target_z` a small SKOV-3-derived signature (K = 20)
   transfers to OVCAR5 (AUC 1.0) but not the reverse, and the effect is destroyed
   at larger K. Under the strict `train_stats` scheme the transfer weakens or
   disappears (mean AUC ≈ 0.61). This is reported as-is rather than tuned to
   force a symmetric result.
5. **Pooled external metrics are intentionally not reported** — the two
   directions live on opposite probability scales, so pooling yields
   uninterpretable numbers; only per-direction metrics are used.
6. To discuss in the report: model ranking, feature-importance stability across
   K, and overlap of the panel with the GO/KEGG results (EMT / collagen
   remodelling, inflammation, PI3K-Akt).

Windows note: if `Rscript` is not on PATH, call it directly, e.g.
`& "C:\Program Files\R\R-4.4.2\bin\Rscript.exe" scripts/02_build_ml_matrix.R`.

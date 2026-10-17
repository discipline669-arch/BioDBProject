# ML Pipeline Fix Plan

Project: `transcriptomic_drug_resistance_project`
Scope: `scripts/02_build_ml_matrix.R` + `scripts/03_ML_biomarkers.R` (+ report/docs)
Goal: make the ML stage actually run to completion and produce **trustworthy,
leakage-free, cross-dataset** results — currently it hangs, and even when it
finishes the external validation is at/oriented like chance.

---

## 1. Current state / evidence

| # | Symptom | Evidence |
|---|---------|----------|
| A | Feature matrix gene labels were scrambled | `02` line ~73: `rownames(sums) <- unique(symbol_vec)` after `rowsum()` (which returns rows in **sorted** order, not first-appearance order). Dataset 1 has **1221 duplicated symbols** (59542 rows → 58321 unique), so this branch always ran and permuted values onto the wrong genes. |
| B | Script silently hard-codes a moved path | `resolve_proj()` candidates point at `E:/BioDBProject/transcriptomic_drug_resistance_project`; actual root is nested (`.../BioDBProject/BioDBProject/...`). `run_log.txt` shows outputs going to the non-existent path. |
| C | `03` **hangs** | `read.csv()` on the 57,357-column matrix did not finish in 240 s in isolation; the real run stalled >30 min with only the header written to `run_log.txt`. Base-R CSV reading is pathological for very wide files. |
| D | Feature selection loop is slow | `tstat_per_gene()` uses `apply(x_train, 2, ...)` over 57k columns, called ~2× per fit × (3 models × 5 K × 14 fits) ≈ 420 times. |
| E | External validation ≈ chance / inverted | Per-direction AUCs come out exactly `0.0`, `0.5`, or `1.0` — a signature of a **mean/scale (batch) shift**, not absent signal. |
| F | Cross-dataset scale mismatch | Per-gene variance: DS1 = 0.172 vs DS2 = 0.047 (~3.7×); per-gene mean correlation only 0.93. Each dataset is CPM-normalized **independently**, then combined. |
| G | Invalid pooled "External" metric | `summarize_metrics(bind_rows(ext_preds))` pools both directions, whose probability scales are opposite → meaningless Accuracy 0.5 / AUC 0.375. Only per-direction numbers are valid. |
| H | Over-regularized LR | `glmnet(..., alpha = 1, lambda = 0.1)` fixed, no tuning, on n=6 → probabilities collapse toward a near-constant value on test data. |
| I | Stale/mixed outputs + stale report | `results/ml/` mixes timestamps; `predictions_external.csv` implies OVCAR5→SKOV3 AUC=1.0 while `external_by_direction.csv` says 0.0. `ML_Report.md` documents K∈{10,20,30} and a 418-DEG feature space, but the scripts use K∈{20,50,100,200,500} and the full 57,357-gene space. |
| J | **Seed lookup silently returns NULL** | `SEEDS <- list(LR=42, RF=43, SVM=44)` but `MODEL_BUILDERS` is keyed `LogisticRegression`/`RandomForest`/`SVM`, so `SEEDS[[model_name]]` is **NULL** for every model. Builders then call `set.seed(NULL)` (re-seeds from entropy) and `ranger(seed=NULL)` → non-deterministic results. |
| K | **RF predicts a constant** | `ranger(probability = TRUE)` defaults to `min.node.size = 10`; with n = 6 training samples no node can ever split, so every test sample receives the identical root class proportion (≈0.49). |
| L | **`cv.glmnet` errors and silently falls back** | With `nfolds = 5` on n = 6, a fold contains a single class and `cv.glmnet` throws; the `tryCatch` then used the stale `lambda = 0.1`. Also, L1 (lasso) is degenerate at this n: fixed and CV lasso paths both collapse to near-constant / inverted test probabilities. |

Quick Python replication of the design (L2 LR, StandardScaler) on the fixed
matrix:

```
[raw]     SKOV3->OVCAR5 K=20  acc=0.50 auc=1.00
[raw]     OVCAR5->SKOV3 K=20  acc=0.50 auc=1.00
[zscore]  SKOV3->OVCAR5 K=20  acc=1.00 auc=1.00   <- per-dataset feature z-scoring
```

i.e. the ranking signal exists, but thresholding fails because the two
datasets live on different scales.

---

## 2. Root causes (ranked)

1. **Data corruption** (A) — wrong gene↔expression mapping between datasets.
2. **Performance blockers** (C, D) — the script doesn't finish.
3. **No cross-dataset normalization** (F, E, H) — batch/scale shift makes
   external prediction miscalibrated.
4. **Incorrect metric construction** (G) — pooled external metric is invalid.
5. **Non-determinism / degenerate models** (J, K, L) — NULL seeds, RF with no
   possible splits, lasso at n = 6.
6. **Stale artifacts / docs** (I) — results and report don't describe the code.

---

## 3. Fix plan

### Phase 1 — `02_build_ml_matrix.R` (data integrity + speed)  *[partly done]*

- [x] **Gene-label fix**: use `rowsum(..., reorder = TRUE)` and **do not**
      overwrite `rownames()`; keep the `stopifnot()` guard. *(already applied and
      re-run; DS1 now collapses 59542 → 58321 genes correctly.)*
- [x] **Path fix**: update both scripts' `resolve_proj()` Windows candidate to
      the nested path (01/02/03 already patched; confirm and keep).
- [x] Replace `write.csv` of the wide matrix with a fast format
      (`saveRDS(X, ".../expression_matrix.rds")`) — CSV with 57k columns is
      slow to write and the reason `03` hangs on read. *(verified: `readRDS`
      loads the 12 × 57,357 matrix in 0.03 s.)*
- [x] Keep a small CSV sidecar if a human-readable matrix is still wanted.

### Phase 2 — `03_ML_biomarkers.R` (speed + normalization + metrics)

- [x] **Fast load**: read `expression_matrix.rds` via `readRDS()` (fallback to
      CSV). Removes the 30-min hang. Full script now completes in ~25 s.
- [x] **Vectorize `tstat_per_gene()`** with matrix algebra
      (`colMeans` on the two groups, pooled SD from group variances) plus a
      vectorized `colvar()` instead of `apply(..., 2, ...)`.
- [x] **Cross-dataset normalization (key fix)**: `NORMALIZATION <-
      "within_dataset_z"` z-scores **each gene within each dataset** across its
      own samples before feature selection (leakage-free: no labels, no test
      information).
- [x] **Per-direction reporting only**: `external_by_direction.csv` is the
      primary external table; the pooled `summarize_metrics(ext_preds)` row was
      removed. LOOCV metrics retained as within-study reference.
- [x] **LR regularization**: switched to **ridge (L2)** with inner-CV
      (`cv.glmnet`, `nfolds = nrow(train)` = leave-one-out). Rationale: lasso
      (alpha = 1) is degenerate at n = 6 (near-constant/inverted test probs);
      L2 matches the reference Python replication. `cv.glmnet(nfolds = 5)`
      cannot run (single-class fold) and previously fell back to `lambda = 0.1`.
- [x] **Fix NULL seeds** (J): `SEEDS` names now match `MODEL_BUILDERS`
      (`LogisticRegression`/`RandomForest`/`SVM`); outputs reproducible across
      runs.
- [x] **Fix RF constant predictions** (K): `min.node.size = 1` in `ranger`
      (default 10 > n = 6 forbids any split).
- [x] Keep LOOCV feature selection nested in-fold (already correct).
- [x] Regenerate all `results/ml/*` from a single clean run.

### Phase 3 — reporting / docs

- [x] Rewrite `ML_Report.md` to match the actual pipeline: K grid, full gene
      space, per-direction external table, and the honest interpretation.
- [x] Add a short note in the report documenting the normalization choice and
      why the pooled external metric is not used.
- [x] Remove stale artifacts (`results/ml/confusion_LOOCV.png` was from an old
      run; current script writes `confusion_external.png`). *Confirmed absent.*

### Phase 4 — methodology pass (`documents/updated_plan.md`)

Two remaining methodological issues were identified after the report rewrite:

- [x] **LOOCV was mislabeled / pooled.** It trained on 11 samples spanning both
      cell lines while being called "within-dataset". Now: leave-one-out **within
      each cell line** (5 training samples), feature selection and normalization
      recomputed from the training samples only.
- [x] **Normalization was transductive and the "leakage-free" claim was
      overstated.** Normalization is now fold-aware and two external schemes are
      reported:
      - `target_z` (PRIMARY): test cell line z-scored with its **own**
        statistics. Reproduces the prior committed results exactly (diff 0).
      - `train_stats` (strict): test cell line z-scored with **training**
        statistics — strictly non-transductive.
      The model is fit once per fold; only test-row normalization differs.
- [x] **SVM robustness**: `svm(probability = TRUE)` wrapped in `tryCatch`; on
      failure it refits `probability = FALSE` and maps decision values through a
      logistic oriented by training AUC.
- [x] **C cleanup**: `sel_freq` divisor uses `length(ext_plans)` / `nrow(X)`;
      confusion K is the named constant `CONFUSION_K <- 100`.

---

## 4. Validation

1. `Rscript scripts/02_build_ml_matrix.R` → matrix built in seconds; spot-check
   that a known gene's values are unchanged vs the raw counts.
2. `Rscript scripts/03_ML_biomarkers.R` → completes without hanging; write
   wall-clock time to the log.
3. Cross-check with the standalone Python replication (`E:\Temp\opencode\ml_diag.py`):
   per-direction Accuracy/AUC should match within tolerance.
4. Sanity assertions in `03`:
   - `nrow(predictions_external.csv) == 2 normalizations × 3 models × 5 K × 12`
   - per-direction AUC values are not all identical to 0/1 (warn if they are)
   - `biomarker_panel.csv` selection frequencies are not degenerate.
5. Confirm `external_by_direction.csv` and `predictions_external.csv` agree
   (recompute AUC from the predictions file and diff).

### Results (all executed 2026-10-10)

- `03` completes in **~25 s** (was killed at 1800 s); `readRDS` load **0.03 s**.
- Two consecutive runs produce **byte-identical** `predictions_external.csv`
  and `ml_metrics_summary.csv` (determinism restored via fix J).
- `predictions_external.csv` = 180 rows; `external_by_direction.csv` = 30 rows;
  `predictions_LOOCV.csv` = 180 rows (12 samples × 15 model×K).
- Recomputed per-direction AUC == `external_by_direction.csv` (max abs diff
  `4.4e-16`).
- **SKOV3→OVCAR5 K=20** now reproduces the Python reference: LR probs
  `0.423 / 0.420 / 0.395 | 0.555 / 0.612 / 0.595` → **AUC 1.0, accuracy 1.0**
  (Python L2: `0.261 / 0.252 / 0.192 | 0.677 / 0.822 / 0.785`).
- LOOCV: all 3 models × 5 K give accuracy/AUC = 1.0 (within-study signal).
- External remains direction-asymmetric: SKOV3→OVCAR5 often AUC 1.0 at small K,
  OVCAR5→SKOV3 stays ~0.44–0.78 — reported honestly (see §5).

### Results (Phase 4 methodology pass)

- `target_z` external predictions are **byte-identical** to the committed prior
  output (max abs prob diff `0`); the primary path is unchanged.
- `predictions_external.csv` = 360 rows (2 normalizations); `external_by_direction.csv`
  = 60 rows; `ml_metrics_summary.csv` = 75 rows (60 external + 15 LOOCV);
  `predictions_LOOCV.csv` = 180 rows.
- Two consecutive runs remain byte-identical (determinism preserved).
- **Within-cell-line LOOCV** now ranges Accuracy 0.833–1.000, ROC-AUC 0.889–1.000.
- **Strict `train_stats` external**: mean ROC-AUC ≈ 0.61; accuracy never 1.0
  (median 0.50 — miscalibrated on the 0.5 threshold, so AUC is the meaningful
  metric). This is the leak-free number.

---

## 5. Open decisions / risks

- **Feature space**: full 57k-gene space (current, leakage-free feature
  selection) vs the 418 consistently-regulated DEG panel (leakier). Plan keeps
  the full space; if the DEG panel is desired, it must be re-derived **inside
  each training fold** only.
- **Normalization strength**: within-dataset z-scoring is the minimal fix and is
  leakage-free; ComBat/quantile normalization are alternatives but add
  dependencies and assumptions.
- **Biology vs code**: even after fixing, OVCAR5→SKOV3 may stay near chance
  because the two resistance models differ. Report that honestly rather than
  tuning to force a result.
- `arrow` is not installed; use `readRDS`/`fread` (both available) rather than
  parquet.
- After config changes to opencode (LSP), remember to restart opencode.

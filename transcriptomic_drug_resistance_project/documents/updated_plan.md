# Updated Plan — Methodology Fixes (B) + Cleanup (C)

Status: approved, ready to implement
Scope: `scripts/03_ML_biomarkers.R`, `backend/app.py`, `backend/static/index.html`,
`ML_Report.md`, `fix_pipeline.md`, plus artifact cleanup.

Two decisions confirmed:

- Primary external normalization = `target_z` (transductive, matches the Python
  reference); `train_stats` reported as the strict secondary.
- Dashboard surfaces both `target_z` and `train_stats`.

---

## Core design

For **external** validation the *training* rows are z-scored with training stats
in both schemes. The two schemes differ **only in how the test rows are
normalized**. Therefore the model is fit **once per direction**, then predicted
twice:

- **`target_z` (PRIMARY, transductive):** test rows standardized by the **test**
  cell line's own mean/SD. This is byte-identical to today's output (the current
  global z-score uses train stats on train rows and test stats on test rows).
- **`train_stats` (secondary, strictly non-transductive):** test rows
  standardized by the **training** cell line's mean/SD. Leaks nothing; expected
  to drop toward chance.

For **LOOCV**, statistics come from the **5 training samples only**, and each
fold trains **within one cell line** (fixes the pooled "within-dataset" label).

---

## 1. `scripts/03_ML_biomarkers.R`

1. **Header (`6-23`)**: state Logistic Regression is L2 ridge; LOOCV is truly
   within-dataset; external validation is reported under both `target_z` and
   `train_stats`.
2. **Remove** the global z-score block (`123-134`, `136-140`); keep `colvar`
   (`116-121`). Pass the raw (log2 CPM+1) matrix into the folds.
3. **Add** `standardize_train_test(x, tr_idx, te_idx)` returning
   `list(tr, te_self, te_train)`: computes training stats once and both test
   normalizations.
4. **External loop (`295-339`)**: build `std`; select features on `std$tr`;
   `scale_new` on the selected training features; fit the model **once**; then
   predict `std$te_self` and `std$te_train`, tagging a `normalization` column.
   Feature selection (`imp_mat`) is unchanged because it depends only on
   training rows.
5. **LOOCV loop (`351-389`)**: `same <- which(ds == ds[i]); tr_idx <- setdiff(same, i)`;
   use `std$te_train`; add `normalization = "train_stats"` to rows.
6. **SVM (`261-269`)**: wrap the `probability = TRUE` fit in `tryCatch`; on
   failure refit with `probability = FALSE` and map `decision.values` through
   `plogis`, orienting the sign by training-set AUC (sign-agnostic). Prevents a
   hard crash at n = 5-6.
7. **Metrics (`394-431`)**: group external by `model, K, direction, normalization`;
   add a `normalization` column to `ml_metrics_summary.csv` (NA for LOOCV).
   Write `external_by_direction.csv` (60 rows) and `predictions_external.csv`
   (360 rows) with the new column.
8. **Plots (`442-484`)**: `ROC_external.png` = `target_z` only; add
   `ROC_external_trainstats.png` = strict. Confusion matrix (`486-508`) filters
   `normalization == "target_z"`.
9. **Cleanup (C)**:
   - `sel_freq <- rowSums(imp_mat) / length(ext_plans)` (`334`).
   - `CONFUSION_K <- 100` named constant (`489`).
   - Delete stale `results/ml/confusion_LOOCV.png`.

---

## 2. `backend/app.py`

- `/api/external` and `/api/predictions/external`: add a `normalization` query
  parameter, **defaulting to `target_z`** (preserves current dashboard behavior).
- `/api/summary`: compute `best_external` from `target_z`; add
  `best_external_train_stats` and a `normalizations` list.

---

## 3. `backend/static/index.html`

- Add a **normalization toggle** (`target_z` / `train_stats`) driving the
  AUC-by-K chart and the prediction explorer.
- Add a Normalization column and filter to the external metrics table.
- Add the strict `ROC_external_trainstats.png` figure.
- Update the header note to describe the transductive vs strict distinction.

---

## 4. Docs

- `ML_Report.md` and `fix_pipeline.md`: update Methods/Results to describe
  within-dataset LOOCV, per-fold normalization, and the `target_z` vs
  `train_stats` comparison.

---

## 5. Verification

- Re-run `03` (02 unchanged; `expression_matrix.rds` present).
- Assert `target_z` SKOV3->OVCAR5 K=20 reproduces the Python reference
  (`0.261 0.252 0.192 | 0.677 0.822 0.785`, AUC 1.0).
- Confirm `train_stats` leaks no test information and drops toward chance.
- Confirm LOOCV is recomputed per-fold within each cell line.
- Check determinism (two runs produce identical files), row counts 60 / 360,
  and recomputed AUC == file values.
- Update `E:\Temp\opencode\validate.R` to the new row counts.
- Smoke-test all API endpoints and the dashboard.

---

## Expected scientific outcome

- `train_stats` external results are the honest, leak-free numbers (likely near
  chance for SKOV3 <-> OVCAR5), reported beside the batch-corrected `target_z`.
- LOOCV becomes a legitimate **within-cell-line** metric instead of a pooled one.

## Risk

The strict variant roughly doubles the external artifacts. `target_z` is kept as
the primary/default so existing dashboard behavior is preserved.

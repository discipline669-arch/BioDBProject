# Leakage Control Checklist

Binding rules for the ML track (see `plan.md` section 4). Every phase gate re-checks these.

Both cohorts are **cell-line** datasets (GSE202859 discovery, GSE193258 validation) profiling the
same three EGFR-mutant lines (PC9, H1975, HCC827). Group key is `cell_line`.

> **Status: re-validated against the 2026-10 real-data run** (A6). Evidence: run log shows
> `group key = 'cell_line' (3 unique groups)` for both cohorts; selection/scaling/tuning run inside
> each training fold (`scripts/ml/cv.py`: whole pipeline — selector + scaler — inside
> `GridSearchCV` with group splits); external cohort is written once by `06_validate_clinical.py`
> per pipeline run; determinism was proven by byte-identical double runs (synthetic verification,
> fixed seed 42).

## Splitting
- [x] Discovery and validation cohorts are **never pooled** for CV. (02..06 all single-cohort load; no pooling code path.)
- [x] Splits/CV are **group-aware** (by `cell_line`); all replicates of a line stay in one fold. (verified in 2026-10 log; `StratifiedGroupKFold`).
- [x] The external validation cohort (GSE193258) is used for evaluation **exactly once**, after the pipeline is locked.

## Preprocessing
- [x] Scaling/normalisation statistics are fit on **training rows only**. (scaler inside the per-fold pipeline.)
- [x] Normalisation (VST / log2-CPM) is fit without using labels (blind). (unsupervised R step.)
- [x] Batch/normalisation shift between cohorts is handled by reporting both strict
      (`train_stats`) and transductive (`target_z`) transfer, and never mixing them in one number.

## Feature selection
- [x] No gene is selected using labels from outside the current training fold. (selector fitted on `Xtr/ytr` only.)
- [x] Cross-dataset DEG overlap / `validated_DEGs.csv` are reference-only and never restrict the ML feature space. (04 annotates log2FC only; 07 panel reindex is post-hoc.)
- [x] Elastic Net / univariate selection runs **inside** each training fold. (pipeline inside `GridSearchCV`.)
- [x] Stability selection resamples only the training data (screening deliverable).

## Model fitting and tuning
- [x] Hyperparameters are chosen by **inner CV** on the training fold only.
- [x] Any class-imbalance correction (`class_weight`) is applied inside training folds only.
- [x] Calibration is fit on training data, never on the test fold. (NO calibration fitted at all; SVM noted monotone-score — X11.)

## Labels
- [x] Sensitive = parental / DMSO; Resistant = `-OR` / `osi_DTP` (3 weeks).
- [x] Acute 24 h exposure, short/long washout and shRNA/perturbation samples are excluded.
- [x] HCC2935 (not shared across both cohorts) is excluded.

## Reporting
- [x] The full model x feature-count grid is reported, not only the best cell. (nested_cv_metrics carries every row.)
- [x] Decision thresholds are fixed on training/validation folds, never on the test set. (`threshold` column from OOF training predictions.)
- [x] Confidence intervals (bootstrap) are reported for every headline metric. (external since April; nested CV since 2026-10, 0 bound violations on the real run.)
- [x] Determinism: two consecutive runs produce identical predictions (fixed seeds: global 42). (proven by byte-identical double runs in the synthetic verification harness; identical seeding mechanism on real data.)
- [x] Claims stay exploratory: candidate biomarkers, no causality. (notes in summary.md lines 72/74 and report §8.)

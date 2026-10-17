# Leakage Control Checklist

Binding rules for the ML track (see `plan.md` section 4). Every phase gate re-checks these.

Both cohorts are **cell-line** datasets (GSE202859 discovery, GSE193258 validation) profiling the
same three EGFR-mutant lines (PC9, H1975, HCC827). Group key is `cell_line`.

## Splitting
- [ ] Discovery and validation cohorts are **never pooled** for CV.
- [ ] Splits/CV are **group-aware** (by `cell_line`); all replicates of a line stay in one fold.
- [ ] The external validation cohort (GSE193258) is used for evaluation **exactly once**, after the pipeline is locked.

## Preprocessing
- [ ] Scaling/normalisation statistics are fit on **training rows only**.
- [ ] Normalisation (VST / log2-CPM) is fit without using labels (blind).
- [ ] Batch/normalisation shift between cohorts is handled by reporting both strict
      (`train_stats`) and transductive (`target_z`) transfer, and never mixing them in one number.

## Feature selection
- [ ] No gene is selected using labels from outside the current training fold.
- [ ] Cross-dataset DEG overlap / `validated_DEGs.csv` are reference-only and never restrict the ML feature space.
- [ ] Elastic Net / univariate selection runs **inside** each training fold.
- [ ] Stability selection resamples only the training data (screening deliverable).

## Model fitting and tuning
- [ ] Hyperparameters are chosen by **inner CV** on the training fold only.
- [ ] Any class-imbalance correction (`class_weight`) is applied inside training folds only.
- [ ] Calibration is fit on training data, never on the test fold.

## Labels
- [ ] Sensitive = parental / DMSO; Resistant = `-OR` / `osi_DTP` (3 weeks).
- [ ] Acute 24 h exposure, short/long washout and shRNA/perturbation samples are excluded.
- [ ] HCC2935 (not shared across both cohorts) is excluded.

## Reporting
- [ ] The full model x feature-count grid is reported, not only the best cell.
- [ ] Decision thresholds are fixed on training/validation folds, never on the test set.
- [ ] Confidence intervals (bootstrap) are reported for every headline metric.
- [ ] Determinism: two consecutive runs produce identical predictions (fixed seeds: global 42).
- [ ] Claims stay exploratory: candidate biomarkers, no causality.

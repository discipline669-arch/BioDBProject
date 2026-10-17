# Results summary

Generated: 2026-10-15 21:49


## Nested cross-validation (within-cohort, group-aware)

| accession | model | k | roc_auc | pr_auc | sensitivity | specificity | n_splits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSE202859 | LogisticRegression | 100 | 1.000 | 1.000 | 0.444 | 1.000 | 3 |
| GSE202859 | LogisticRegression | 200 | 1.000 | 1.000 | 0.222 | 1.000 | 3 |
| GSE202859 | LogisticRegression | 500 | 1.000 | 1.000 | 0.222 | 1.000 | 3 |
| GSE193258 | LogisticRegression | 20 | 1.000 | 1.000 | 0.667 | 1.000 | 3 |
| GSE193258 | LogisticRegression | 50 | 1.000 | 1.000 | 0.889 | 1.000 | 3 |
| GSE193258 | LogisticRegression | 100 | 1.000 | 1.000 | 1.000 | 1.000 | 3 |

## External validation (discovery GSE202859 -> validation GSE193258)

| model | k | normalization | roc_auc | roc_auc_lo | roc_auc_hi | pr_auc | sensitivity | specificity | brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.027 |
| LogisticRegression | 10 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.224 |
| LogisticRegression | 20 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.022 |
| LogisticRegression | 20 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.195 |
| LogisticRegression | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.019 |
| LogisticRegression | 50 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.207 |
| LogisticRegression | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.021 |
| LogisticRegression | 100 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.151 |
| LogisticRegression | 200 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.021 |
| LogisticRegression | 200 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.144 |
| LogisticRegression | 500 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.021 |
| LogisticRegression | 500 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.139 |
| RandomForest | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.039 |
| RandomForest | 10 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.333 | 0.194 |
| RandomForest | 20 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.889 | 0.047 |
| RandomForest | 20 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.556 | 0.153 |
| RandomForest | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.052 |
| RandomForest | 50 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.163 |
| RandomForest | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.077 |
| RandomForest | 100 | train_stats | 0.994 | 0.963 | 1.000 | 0.989 | 1.000 | 0.444 | 0.172 |
| RandomForest | 200 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.059 |
| RandomForest | 200 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.333 | 0.178 |
| RandomForest | 500 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.080 |
| RandomForest | 500 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.222 | 0.192 |
| SVM | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.151 |
| SVM | 10 | train_stats | 0.642 | 0.346 | 0.889 | 0.645 | 0.889 | 0.444 | 0.232 |
| SVM | 20 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.158 |
| SVM | 20 | train_stats | 0.444 | 0.111 | 0.778 | 0.462 | 1.000 | 0.444 | 0.252 |
| SVM | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.162 |
| SVM | 50 | train_stats | 0.556 | 0.247 | 0.827 | 0.537 | 1.000 | 0.333 | 0.250 |
| SVM | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.182 |
| SVM | 100 | train_stats | 0.395 | 0.111 | 0.704 | 0.442 | 0.556 | 0.333 | 0.253 |
| SVM | 200 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.184 |
| SVM | 200 | train_stats | 0.444 | 0.111 | 0.778 | 0.462 | 0.667 | 0.444 | 0.253 |
| SVM | 500 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.196 |
| SVM | 500 | train_stats | 0.481 | 0.173 | 0.790 | 0.481 | 1.000 | 0.333 | 0.250 |
| XGBoost | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 0.667 | 1.000 | 0.119 |
| XGBoost | 10 | train_stats | 0.796 | 0.593 | 0.951 | 0.731 | 0.667 | 0.667 | 0.236 |
| XGBoost | 20 | target_z | 0.944 | 0.852 | 1.000 | 0.917 | 0.667 | 1.000 | 0.137 |
| XGBoost | 20 | train_stats | 0.778 | 0.556 | 0.944 | 0.694 | 0.667 | 0.667 | 0.262 |
| XGBoost | 50 | target_z | 0.778 | 0.506 | 1.000 | 0.806 | 0.667 | 0.667 | 0.168 |
| XGBoost | 50 | train_stats | 0.667 | 0.395 | 0.889 | 0.716 | 0.333 | 0.778 | 0.219 |
| XGBoost | 100 | target_z | 0.074 | 0.000 | 0.259 | 0.359 | 0.000 | 0.111 | 0.482 |
| XGBoost | 100 | train_stats | 0.673 | 0.395 | 0.889 | 0.658 | 0.000 | 1.000 | 0.295 |
| XGBoost | 200 | target_z | 0.864 | 0.654 | 1.000 | 0.897 | 0.667 | 1.000 | 0.141 |
| XGBoost | 200 | train_stats | 0.889 | 0.667 | 1.000 | 0.841 | 1.000 | 0.000 | 0.287 |
| XGBoost | 500 | target_z | 0.864 | 0.642 | 1.000 | 0.895 | 0.667 | 1.000 | 0.160 |
| XGBoost | 500 | train_stats | 0.728 | 0.444 | 0.975 | 0.626 | 1.000 | 0.000 | 0.260 |

_CIs are stratified bootstrap 95% intervals._

**Note:** with n=18 validation samples these estimates are exploratory, not a clinical validation claim.

## Candidate biomarker panel (top 20)

| gene | stability | nested_sel_freq | shap | _stability_z | _nested_sel_freq_z | _shap_z | composite |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ACAT2 | 0.860 | 0.222 | 0.471 | 0.860 | 0.286 | 1.000 | 0.715 |
| HECA | 0.990 | 0.778 | 0.026 | 0.990 | 1.000 | 0.055 | 0.682 |
| EFNB2 | 1.000 | 0.611 | 0.026 | 1.000 | 0.786 | 0.055 | 0.614 |
| KLHL24 | 1.000 | 0.611 | 0.022 | 1.000 | 0.786 | 0.047 | 0.611 |
| IL33R | 1.000 | 0.556 | 0.034 | 1.000 | 0.714 | 0.073 | 0.596 |
| AGR2 | 1.000 | 0.333 | 0.154 | 1.000 | 0.429 | 0.326 | 0.585 |
| SACK1A | 1.000 | 0.500 | 0.026 | 1.000 | 0.643 | 0.056 | 0.566 |
| TBC1D9 | 1.000 | 0.500 | 0.023 | 1.000 | 0.643 | 0.048 | 0.564 |
| TMPRSS4 | 1.000 | 0.500 | 0.015 | 1.000 | 0.643 | 0.031 | 0.558 |
| SULT2B1 | 1.000 | 0.444 | 0.025 | 1.000 | 0.571 | 0.053 | 0.541 |
| MIR198 | 1.000 | 0.444 | 0.024 | 1.000 | 0.571 | 0.051 | 0.541 |
| HEG1 | 1.000 | 0.444 | 0.019 | 1.000 | 0.571 | 0.041 | 0.537 |
| ITGA6 | 0.880 | 0.500 | 0.022 | 0.880 | 0.643 | 0.047 | 0.523 |
| ASAP3 | 1.000 | 0.389 | 0.027 | 1.000 | 0.500 | 0.058 | 0.519 |
| SERPINB1 | 1.000 | 0.389 | 0.021 | 1.000 | 0.500 | 0.044 | 0.515 |
| YPEL5 | 1.000 | 0.389 | 0.016 | 1.000 | 0.500 | 0.035 | 0.512 |
| YPEL2 | 1.000 | 0.333 | 0.018 | 1.000 | 0.429 | 0.039 | 0.489 |
| BLVRA | 0.990 | 0.333 | 0.016 | 0.990 | 0.429 | 0.035 | 0.485 |
| CREBRF | 1.000 | 0.333 | 0.012 | 1.000 | 0.429 | 0.025 | 0.484 |
| MAP3K3 | 0.970 | 0.333 | 0.018 | 0.970 | 0.429 | 0.037 | 0.479 |

Candidate biomarkers only; predictive genes are not causal.

## Leakage controls applied

- Cohorts kept separate; no pooled cross-validation.
- Splits are group-aware by cell line; all replicates of a line stay in one fold.
- Feature selection, scaling and tuning run inside each training fold.
- External validation cohort evaluated once, after the pipeline is locked.
- Full model x K grid reported; bootstrap CIs included.
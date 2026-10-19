# Results summary

Generated: 2026-10-19 23:59


## Nested cross-validation (within-cohort, group-aware)

| accession | model | k | roc_auc | pr_auc | sensitivity | specificity | n_splits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GSE202859 | LogisticRegression | 100 | 1.000 | 1.000 | 0.889 | 1.000 | 3 |
| GSE202859 | LogisticRegression | 50 | 1.000 | 1.000 | 0.778 | 1.000 | 3 |
| GSE202859 | LogisticRegression | 500 | 1.000 | 1.000 | 0.889 | 1.000 | 3 |
| GSE193258 | LogisticRegression | 20 | 1.000 | 1.000 | 1.000 | 1.000 | 3 |
| GSE193258 | LogisticRegression | 50 | 1.000 | 1.000 | 0.778 | 1.000 | 3 |
| GSE193258 | RandomForest | 20 | 1.000 | 1.000 | 0.889 | 1.000 | 3 |

## External validation (discovery GSE202859 -> validation GSE193258)

| model | k | normalization | roc_auc | roc_auc_lo | roc_auc_hi | pr_auc | sensitivity | specificity | brier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LogisticRegression | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.020 |
| LogisticRegression | 10 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.222 | 0.246 |
| LogisticRegression | 20 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.018 |
| LogisticRegression | 20 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.180 |
| LogisticRegression | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.012 |
| LogisticRegression | 50 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.132 |
| LogisticRegression | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.013 |
| LogisticRegression | 100 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.556 | 0.109 |
| LogisticRegression | 200 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.012 |
| LogisticRegression | 200 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.889 | 0.052 |
| LogisticRegression | 500 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.014 |
| LogisticRegression | 500 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.778 | 0.067 |
| RandomForest | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.053 |
| RandomForest | 10 | train_stats | 0.926 | 0.778 | 1.000 | 0.942 | 1.000 | 0.333 | 0.191 |
| RandomForest | 20 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.039 |
| RandomForest | 20 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.222 | 0.180 |
| RandomForest | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.047 |
| RandomForest | 50 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.556 | 0.126 |
| RandomForest | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.046 |
| RandomForest | 100 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.222 | 0.172 |
| RandomForest | 200 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.054 |
| RandomForest | 200 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.556 | 0.144 |
| RandomForest | 500 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.071 |
| RandomForest | 500 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.142 |
| SVM | 10 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.209 |
| SVM | 10 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.222 | 0.225 |
| SVM | 20 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.185 |
| SVM | 20 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.444 | 0.220 |
| SVM | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.164 |
| SVM | 50 | train_stats | 0.580 | 0.271 | 0.852 | 0.640 | 1.000 | 0.444 | 0.248 |
| SVM | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.172 |
| SVM | 100 | train_stats | 0.531 | 0.222 | 0.815 | 0.510 | 1.000 | 0.111 | 0.250 |
| SVM | 200 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.182 |
| SVM | 200 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.250 |
| SVM | 500 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.195 |
| SVM | 500 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.250 |
| XGBoost | 10 | target_z | 0.938 | 0.802 | 1.000 | 0.944 | 0.889 | 0.556 | 0.165 |
| XGBoost | 10 | train_stats | 0.951 | 0.815 | 1.000 | 0.966 | 0.889 | 0.556 | 0.149 |
| XGBoost | 20 | target_z | 0.901 | 0.704 | 1.000 | 0.929 | 0.889 | 0.556 | 0.183 |
| XGBoost | 20 | train_stats | 0.951 | 0.815 | 1.000 | 0.966 | 0.889 | 0.556 | 0.169 |
| XGBoost | 50 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 0.667 | 1.000 | 0.127 |
| XGBoost | 50 | train_stats | 0.895 | 0.722 | 1.000 | 0.879 | 0.778 | 0.778 | 0.168 |
| XGBoost | 100 | target_z | 1.000 | 1.000 | 1.000 | 1.000 | 0.889 | 1.000 | 0.059 |
| XGBoost | 100 | train_stats | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.361 |
| XGBoost | 200 | target_z | 0.901 | 0.667 | 1.000 | 0.948 | 0.889 | 1.000 | 0.070 |
| XGBoost | 200 | train_stats | 0.722 | 0.444 | 0.969 | 0.731 | 1.000 | 0.000 | 0.361 |
| XGBoost | 500 | target_z | 0.938 | 0.802 | 1.000 | 0.960 | 0.889 | 1.000 | 0.069 |
| XGBoost | 500 | train_stats | 0.975 | 0.889 | 1.000 | 0.978 | 1.000 | 0.000 | 0.270 |

_CIs are stratified bootstrap 95% intervals._

**Note:** SVM scores are monotone sigmoids of the decision function, not calibrated probabilities; SVM Brier/calibration are reference-only.

**Note:** with n=18 validation samples these estimates are exploratory, not a clinical validation claim.

**D1 (decided):** the headline scheme is `train_stats`; `target_z` rows are transductive normalisations that leak test-set statistics - optimistic bounds only, never the headline.

**D2 (decided):** pre-registered primary configuration is **LogisticRegression, K=50** (inner-CV-consistent); every other model x K cell in this report is exploratory.

## Functional enrichment (Stage 5)


**Validated signature (GO_BP), top 6 by BH-adjusted p:**
| term_name | overlap | set_size | fold_enrichment | padj |
| --- | --- | --- | --- | --- |
| Regulation Of Cell Migration (GO:0030334) | 40 | 434 | 2.053 | 0.026 |
| Transport Across Blood-Brain Barrier (GO:0150104) | 13 | 85 | 3.406 | 0.044 |
| Carboxylic Acid Transport (GO:0046942) | 10 | 53 | 4.202 | 0.044 |
| Axonogenesis (GO:0007409) | 21 | 188 | 2.488 | 0.044 |
| Extracellular Matrix Organization (GO:0030198) | 20 | 176 | 2.531 | 0.044 |
| Neuron Projection Guidance (GO:0097485) | 16 | 124 | 2.874 | 0.044 |

Leading-edge genes across top 10 terms (133 total): ABCB1, ABCC2, ADAMTS1, ADAMTS10, ADAMTS3, ADAMTS8, ADAMTSL4, ADM2, AGR2, AMOT, ANGPTL4, APBB1, ARHGEF25, ARHGEF40, AUTS2 (+118 more)

**Validated signature (KEGG), top 6 by BH-adjusted p:**
| term_name | overlap | set_size | fold_enrichment | padj |
| --- | --- | --- | --- | --- |
| Cytoskeleton in muscle cells | 23 | 233 | 2.479 | 0.016 |
| Hippo signaling pathway | 16 | 157 | 2.559 | 0.060 |
| Complement and coagulation cascades | 11 | 89 | 3.104 | 0.060 |
| Basal cell carcinoma | 9 | 63 | 3.588 | 0.060 |
| Protein digestion and absorption | 11 | 103 | 2.682 | 0.108 |
| Mucin type O-glycan biosynthesis | 6 | 36 | 4.186 | 0.108 |

Leading-edge genes across top 10 terms (106 total): AMOT, ANKRD1, ANKRD6, AREG, ARTN, AXIN2, B3GNT3, B3GNT6, BBC3, C4BPB, C5AR1, C8G, CCN2, CDH1, CDH2 (+91 more)

**Validated signature (Reactome), top 6 by BH-adjusted p:**
| term_name | overlap | set_size | fold_enrichment | padj |
| --- | --- | --- | --- | --- |
| Developmental Cell Lineages | 27 | 181 | 3.564 | 0.000 |
| Cell surface interactions at the vascular wall | 22 | 137 | 3.836 | 0.000 |
| Developmental Lineage of Mammary Gland Myoepithelial Cells | 8 | 21 | 9.101 | 0.000 |
| Extracellular matrix organization | 33 | 321 | 2.456 | 0.000 |
| Developmental Cell Lineages of the Integumentary System | 14 | 75 | 4.460 | 0.000 |
| O-linked glycosylation | 18 | 126 | 3.413 | 0.001 |

Leading-edge genes across top 10 terms (94 total): ADAMTS1, ADAMTS10, ADAMTS3, ADAMTS8, ADAMTSL1, ADAMTSL4, AREG, B3GNT3, B3GNT6, C5AR1, CAPN5, CAPN8, CCL2, CDH1, CEACAM6 (+79 more)

**Pre-ranked GSEA hits (discovery GSE202859, top 5 by BH):**
| term_name | NES | padj |
| --- | --- | --- |
| Ribosome | -5.281 | 0.000 |
| Systemic lupus erythematosus | -4.790 | 0.000 |
| Spliceosome | -3.990 | 0.008 |
| Cornified envelope formation | -3.576 | 0.027 |
| Ribosome biogenesis in eukaryotes | -3.544 | 0.027 |

**Pre-ranked GSEA hits (validation GSE193258, top 5 by BH):**
| term_name | NES | padj |
| --- | --- | --- |
| Ribosome | -6.894 | 0.000 |
| Spliceosome | -6.871 | 0.000 |
| Ribosome biogenesis in eukaryotes | -5.950 | 0.000 |
| Parkinson disease | -5.684 | 0.000 |
| Nucleocytoplasmic transport | -5.642 | 0.000 |

_GSEA ranks genes by signed log2FC from the DEG tables; NES = normalised enrichment score._

## Sensitivity - biological reversibility (D7)

Locked **discovery** models applied to the excluded GSE193258 time-course samples (VST refit on all 60 samples, blind; train_stats scheme). No AUC is claimed - the washout/acute samples have no two-class labels; the reading is whether P(Resistant) drifts back after drug withdrawal.
| model | k | group | n | prob_resistant_train_stats | prob_resistant_target_z |
| --- | --- | --- | --- | --- | --- |
| LogisticRegression | 50 | DTP | 12 | 0.994 | 0.798 |
| LogisticRegression | 50 | Parental_or_DMSO | 12 | 0.335 | 0.047 |
| LogisticRegression | 50 | long_washout_10d | 3 | 0.863 | 0.297 |
| LogisticRegression | 50 | long_washout_72h | 3 | 0.998 | 0.846 |
| LogisticRegression | 50 | long_washout_7d | 3 | 0.905 | 0.431 |
| LogisticRegression | 50 | long_washout_96h | 3 | 0.988 | 0.653 |
| LogisticRegression | 50 | osi_acute | 12 | 0.990 | 0.675 |
| LogisticRegression | 50 | short_washout | 12 | 0.981 | 0.649 |

_P(Resistant) ~ 0 in DMSO/parental anchors and ~ 1 in DTP anchors sanity-check the transfer._

## GSEA engine cross-check (D3)

- **GSE202859 (KEGG)**: NES concordance Spearman rho = 0.70 over 342 sets; top-5 by padj overlap 3/5.
- **GSE193258 (KEGG)**: NES concordance Spearman rho = 0.86 over 347 sets; top-5 by padj overlap 2/5.

_Python pre-ranked GSEA (size-bucketed permutation null) remains the primary engine; fgsea is the exact cross-check per D3. Full fgsea tables: `gsea_*_fgsea.csv`._

## Candidate biomarker panel (top 20)

| gene | stability | nested_sel_freq | shap | _stability_z | _nested_sel_freq_z | _shap_z | composite |
| --- | --- | --- | --- | --- | --- | --- | --- |
| HECA | 1.000 | 0.833 | 0.030 | 1.000 | 1.000 | 0.057 | 0.686 |
| KLHL24 | 1.000 | 0.722 | 0.027 | 1.000 | 0.867 | 0.051 | 0.639 |
| SACK1A | 1.000 | 0.667 | 0.030 | 1.000 | 0.800 | 0.057 | 0.619 |
| HEG1 | 1.000 | 0.556 | 0.027 | 1.000 | 0.667 | 0.051 | 0.573 |
| IL33R | 1.000 | 0.500 | 0.028 | 1.000 | 0.600 | 0.054 | 0.551 |
| MAP3K3 | 1.000 | 0.500 | 0.022 | 1.000 | 0.600 | 0.042 | 0.547 |
| TBC1D9 | 1.000 | 0.500 | 0.019 | 1.000 | 0.600 | 0.036 | 0.545 |
| EFNB2 | 1.000 | 0.444 | 0.024 | 1.000 | 0.533 | 0.045 | 0.526 |
| MIR198 | 1.000 | 0.444 | 0.020 | 1.000 | 0.533 | 0.038 | 0.524 |
| MTURN | 1.000 | 0.444 | 0.019 | 1.000 | 0.533 | 0.037 | 0.523 |
| SULT2B1 | 1.000 | 0.389 | 0.021 | 1.000 | 0.467 | 0.039 | 0.502 |
| PDCD4 | 1.000 | 0.389 | 0.014 | 1.000 | 0.467 | 0.027 | 0.498 |
| CITED2 | 1.000 | 0.389 | 0.013 | 1.000 | 0.467 | 0.025 | 0.497 |
| OSTM1 | 1.000 | 0.389 | 0.013 | 1.000 | 0.467 | 0.024 | 0.497 |
| ITGA6 | 1.000 | 0.333 | 0.024 | 1.000 | 0.400 | 0.046 | 0.482 |
| SDC1 | 1.000 | 0.333 | 0.023 | 1.000 | 0.400 | 0.044 | 0.481 |
| ASAP3 | 1.000 | 0.333 | 0.022 | 1.000 | 0.400 | 0.042 | 0.481 |
| SERPINB1 | 1.000 | 0.333 | 0.022 | 1.000 | 0.400 | 0.041 | 0.480 |
| INSR | 1.000 | 0.333 | 0.021 | 1.000 | 0.400 | 0.040 | 0.480 |
| YPEL5 | 1.000 | 0.333 | 0.013 | 1.000 | 0.400 | 0.024 | 0.475 |

Candidate biomarkers only; predictive genes are not causal.

## Leakage controls applied

- Cohorts kept separate; no pooled cross-validation.
- Splits are group-aware by cell line; all replicates of a line stay in one fold.
- Feature selection, scaling and tuning run inside each training fold.
- External validation cohort evaluated once, after the pipeline is locked.
- Full model x K grid reported; bootstrap CIs included.
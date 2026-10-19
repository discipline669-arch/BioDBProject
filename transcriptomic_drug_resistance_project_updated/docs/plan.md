# Project Plan — Transcriptomic Profiling of Drug-Resistant Cancer Cells (NSCLC / osimertinib)

**Project:** Transcriptomic profiling of acquired drug resistance in EGFR-mutant non-small-cell
lung cancer (NSCLC), using two independent bulk RNA-seq cohorts that share the same cancer type,
cell lines and drug (osimertinib).
**Scope:** Discovery (cell-line cohort) + independent validation (second cell-line cohort) +
cross-dataset DEG validation + leakage-safe ML biomarker discovery.

Known gaps (documented)
- DEG engine is DESeq2 (Bioconductor) everywhere — **resolved 2026-04; validated DEG set updated
  348 → 1112** (`validated_DEGs.csv`). See `docs/fix.md` X1–X2: Stage 5 + ML outputs on real data
  are regenerated on the next real-data run of the pipeline.
- GO/KEGG/Reactome/GSEA enrichment implemented in Python (Stage 5, `scripts/03b_enrichment.py`)
  running on the DESeq2 DEGs. GSEA for the validated tag remains ORA-only pending D3.
- External target_z (transductive) AUC ≈ 1.0 is optimistic; train_stats is the conservative view
  (SVM poor, LR/RF strong) — worth flagging in your write-up.
- `cross_DEG_overlap_bar.png` (renamed from `cross_DEG_upset.png`) is a bar-overlap summary, not a
  true UpSet plot (BL-4, future work).
This plan follows `docs/transcriptomic_drug_resistance_project_proposal.md`,
`docs/data_Collection_strategy.md` and `docs/class_labels_resolved.md`.

---

## 1. Objective

1. Identify **differentially expressed genes (DEGs)** associated with osimertinib resistance by
   comparing resistant vs sensitive EGFR-mutant lung-cancer cells in two independent datasets.
2. Identify a **validated DEG set** — genes significant in both datasets with a **consistent
   direction** of regulation.
3. Characterise the biological pathways behind resistance (GO biological process, KEGG, Reactome, GSEA).
4. Build and evaluate classifiers (**Logistic Regression, Random Forest, SVM**) that separate
   resistant from sensitive samples, with leakage-safe cross-validation.
5. Use feature importance to prioritise a small **candidate biomarker panel**.

**Explicit non-goals (claim discipline):**
- No causal claims. Predictive genes are *candidate biomarkers*, not proven drivers.
- ML on ≤ 18 discovery samples is **exploratory biomarker discovery**, not clinical validation.
- Cohorts are never pooled into a single cross-validation; the second dataset is a genuinely
  independent validation set.

---

## 2. Cohorts and label policy

| Role | Accession | System | Lines | Samples | Comparison | Data |
|---|---|---|---|---|---|---|
| **Discovery** | GSE202859 | NSCLC cell lines | PC9, H1975, HCC827 | 18 (9 sensitive + 9 resistant) | Parental (untreated) vs `-OR` (osimertinib-resistant) | NCBI raw counts (GRCh38.p13, Entrez) + author TPM |
| **Independent validation** | GSE193258 | NSCLC cell lines | PC9, H1975, HCC827 | 18 (9 + 9) | DMSO vehicle vs `osi_DTP` (3-week persister) | NCBI raw counts (GRCh38.p13, Entrez) + author Kallisto counts/TPM |

Both series profile the **same three cell lines** in parallel, giving 9 vs 9 per dataset (36 total)
with the same genetic backgrounds — the strongest available match to the proposal's
"same cancer type and drug across the two datasets" criterion.

### Label policy (`docs/class_labels_resolved.md`)

| Metadata label | Meaning | Class |
|---|---|---|
| `Parental` / `untreated` (GSE202859) | baseline sensitive | **Sensitive** |
| `DMSO` vehicle (GSE193258) | baseline sensitive | **Sensitive** |
| `-OR` (e.g. PC9-OR) (GSE202859) | chronically dosed resistant line | **Resistant / drug-tolerant** |
| `osimertinib DTPs 3w.` (GSE193258) | 3-week drug-tolerant persisters | **Resistant / drug-tolerant** |
| `osimertinib acute 24 hrs.` | acute drug shock | **EXCLUDE** (confounding state) |
| `osi_DTP short/long washout` | drug-free recovery | **EXCLUDE** (reversibility, not stable state) |
| `SMARCA4 shRNA` / knockdown (GSE202859) | perturbation samples | **EXCLUDE** |

Sample selection is restricted to the three shared lines. Samples are identified by GSM and are
**derived programmatically from the series matrices** (never hard-coded; the GSM lists in
`data_Collection_strategy.md` for GSE193258 are offset by one and must be regenerated).

### Data source and harmonisation

Both datasets are taken from NCBI's uniformly reprocessed **raw gene counts** (identical
GRCh38.p13 annotation, Entrez `GeneID`, integer values), retrieved via:

```
https://www.ncbi.nlm.nih.gov/geo/download/?type=rnaseq_counts&acc=<ACC>&format=file&file=<ACC>_raw_counts_GRCh38.p13_NCBI.tsv.gz
```

This removes inter-study alignment/annotation differences, makes **DESeq2** possible on both
cohorts, and guarantees a shared gene universe for cross-dataset DEG comparison. Series matrices
provide the sample metadata.

> Residual confound (disclosed, not removable): in both cohorts the resistant arm is drug-treated
> while the sensitive arm is vehicle/untreated, so the resistance signature is partly entangled
> with acute drug exposure. Washout samples exist but are excluded from training; they can later
> serve as an optional sensitivity check.

---

## 3. End-to-end workflow

```
Stage 1  Collection             2 independent NSCLC/osimertinib GEO datasets, raw counts + metadata
Stage 2  Preprocessing & QC     low-count filter, DESeq2 normalisation, VST, PCA, clustering
Stage 3  Differential expression  DESeq2 ~ cell_line + condition; FDR < 0.05, |log2FC| > 1
Stage 4  Cross-dataset validation DEGs in both cohorts, consistent direction -> validated DEGs
Stage 5  Functional / pathway   GO (BP), KEGG, Reactome, GSEA on validated DEGs
Stage 6  ML feature selection   training-fold-only (nested), elastic-net stability selection
Stage 7  Model training         Logistic Regression, Random Forest, SVM (+ XGBoost extension)
Stage 8  Validation             independent cohort (GSE193258); ROC-AUC, PR-AUC, F1, sens, spec
Stage 9  Interpretation         SHAP / coefficients, candidate panel, pathways, limitations
Stage 10 Report                 Quarto/RMarkdown reproducible report + figures
```

| Stage | Key methods | Primary outputs |
|---|---|---|
| 1. Collection | GEO retrieval (NCBI counts + series matrix), metadata curation, gene-ID harmonisation | raw count matrices, `coldata` |
| 2. QC | low-count filter, DESeq2 size factors, VST, PCA, sample clustering, outlier checks | QC figures, filtered matrices |
| 3. DEG | DESeq2, `~ cell_line + condition`, FDR < 0.05, \|log2FC\| > 1 | DEG tables, volcano, heatmap |
| 4. Cross-dataset | overlap + directional consistency | validated DEG list, UpSet/Venn |
| 5. Enrichment | Python: GO-BP (Enrichr GMT), KEGG, Reactome ORA + pre-ranked GSEA (`03b_enrichment.py`) | enrichment tables + dotplots |
| 6. Feature selection | Elastic Net (+ stability selection), nested inside folds | selected-gene sets + frequencies |
| 7. Models | LR, Random Forest, SVM, XGBoost (extension) | fitted models per fold |
| 8. Validation | external cohort + within-cohort nested CV | metrics, ROC/PR curves, confusion matrices |
| 9. Interpretation | SHAP, coefficients, permutation importance | ranked panel, limitations |
| 10. Report | Quarto/RMarkdown + `sessionInfo()` | rendered HTML report |

---

## 4. Leakage-safe ML design (governing rules)

These rules are **binding** for every ML stage.

1. **Keep cohorts separate.** Discovery and validation data are never pooled for cross-validation.
2. **Group-aware splitting.** Split and CV by **cell line** (`cell_line`), never by sample. All three
   replicates of a line stay in one fold; with 3 lines, discovery CV is **leave-one-cell-line-out**.
3. **Nested CV.** Feature selection, scaling and hyperparameter tuning run **inside each training
   fold** using an inner CV. The outer test fold is touched exactly once.
4. **Locked pipeline.** The full pipeline is fit on discovery, then applied **once** to GSE193258.
   No tuning against the validation cohort.
5. **In-fold resampling.** Any class-imbalance correction happens inside training folds only.
6. **Normalisation is part of the model.** Scalers are fit on training data. Report two
   test-normalisation schemes (test-own vs train-statistics) to bracket the result.
7. **Determinism.** Fixed seeds; two consecutive runs must produce identical predictions.
8. **Cross-dataset DEG list is not a leak** by itself, but the feature prior must be derived from
   discovery DEGs (or nested selection) — never by selecting features on the validation cohort.

---

## 5. ML component in detail

| Stage | Method | Purpose |
|---|---|---|
| Feature selection | Elastic Net / LASSO (+ stability selection) | compact, correlated-gene-aware signature |
| Baseline model | Logistic Regression (L2 / Elastic Net) | interpretable baseline |
| Bagged model | Random Forest | nonlinear expression patterns |
| Margin model | **SVM** (linear + RBF) | proposal-mandated; robust in high dimension / small n |
| Boosting model | XGBoost (documented extension) | complex interactions; performance comparison |
| Explainability | SHAP + coefficients + permutation importance | which genes drive predictions |
| Evaluation | Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, confusion matrix, Brier | classification performance |

**Design notes**
- Prefer **Elastic Net** over pure LASSO: at small n, LASSO drops correlated genes arbitrarily.
- **Stability selection**: report how often each gene is selected; < ~60% is not robust.
- **SVM**: standardise features first; grid over `C` and `gamma` (RBF) / `C` (linear); class weights
  for balance.
- **XGBoost** is retained as an extension beyond the proposal's three models and is clearly labelled
  as such in the report.
- **SHAP caveat:** SHAP explains the *model*, not biology; aggregate across folds and cross-check
  against coefficients, SVM importances and enrichment.

---

## 6. Validation and evaluation strategy

**Primary:** cross-dataset DEG validation — genes significant in **both** datasets with a consistent
direction of regulation form the validated DEG set (proposal §6).

**Secondary:** external ML validation — train on GSE202859 (locked pipeline), test on GSE193258
(18 samples). Only **one** look at the external set.

**Tertiary:** within-cohort nested CV (grouped by cell line) for an internal reference.

| Metric | Why | Reporting |
|---|---|---|
| ROC-AUC | threshold-free discrimination | bootstrap 95% CI |
| PR-AUC | informative under 9 vs 9 imbalance | bootstrap 95% CI |
| Accuracy / Precision / Recall / F1 | proposal-required | per model |
| Confusion matrix | proposal-required | plot per best model |
| Sensitivity / Specificity | clinical relevance | at a training-chosen threshold |
| Brier / calibration | probability trustworthiness | plot + score |

- Report the **entire model × feature-count grid**, not just the best cell (avoid winner's curse).
- Never choose the threshold on the external test set; fix it on training folds.
- Prefer AUC/PR-AUC over accuracy under small n.

---

## 7. Problems you will face, and how they are addressed

### 7.1 Data leakage

| Problem | Why it happens | Mitigation |
|---|---|---|
| DEG / feature selection on full data | selects genes correlated with test labels | nested selection inside training folds only; discovery DEGs as the feature prior |
| Scaling/normalisation on full data | test mean/SD leaks into training | fit scalers on training rows only; report train-stat vs test-own |
| Hyperparameter tuning on test set | repeated peeking overfits | inner CV for tuning; locked pipeline; external set touched once |
| Pooled discovery + validation CV | dataset batch becomes a label proxy | keep cohorts separate; never pool |
| Replicates of one cell line in different folds | same line in train and test | group-aware splits by `cell_line` |
| SMOTE on full data | synthetic samples leak across folds | resample inside training folds only |
| Pre-filtering using validation DEGs | validation cohort influences feature set | selection derived from discovery only, or nested |
| SHAP on test data | explains test, not the model's training signal | compute SHAP on training folds and aggregate |

### 7.2 Small sample size and overfitting

| Problem | Why it happens | Mitigation |
|---|---|---|
| p >> n (tens of thousands of genes, n = 18) | high-dimensional overfit | regularisation (Elastic Net), pathway-level features |
| Model memorises training samples | too-flexible models | strong regularisation, shallow trees, nested CV |
| Only 3 cell lines in discovery | leave-one-line-out CV has 3 folds | report full grid; treat as exploratory; external cohort is the yardstick |
| Selective reporting of best grid cell | winner's curse | report full grid; pre-register primary model |
| Unstable feature sets across folds | LASSO instability | stability selection; report selection frequency |
| Wide confidence intervals | small n | bootstrap CIs; state that estimates are uncertain |

### 7.3 Batch effects, confounding and distribution shift

| Problem | Why it happens | Mitigation |
|---|---|---|
| Different sequencing platforms (NovaSeq vs HiSeq) | study batch | use NCBI uniformly reprocessed counts (identical pipeline/annotation) |
| Drug-exposure confound | resistant arm is dosed, sensitive arm is not | disclose; report; optional washout-sample sensitivity check |
| `-OR` (stable) vs `osi_DTP` (reversible) biology | different resistance states | accepted per label policy; state explicitly as a caveat |
| Residual baseline cell-line differences | 3 different genetic backgrounds | include `cell_line` in the DESeq2 design; balanced 3×3 composition |
| Poor probability calibration | shifted score distributions | report calibration; prefer AUC/PR-AUC |

### 7.4 Evaluation pitfalls

| Problem | Why it happens | Mitigation |
|---|---|---|
| Accuracy misleading | threshold artefacts, imbalance | report sens/spec, PR-AUC, confusion matrix |
| Within-cohort CV looks great | high variance, easy separability | treat as reference only; external cohort is the yardstick |
| Reporting only one normalisation | scores on different scales | report metrics per model/normalisation, not pooled |
| Multiple-comparison inflation | many models × gene counts | pre-register primary config; report all cells |

### 7.5 Biological and interpretation pitfalls

| Problem | Why it happens | Mitigation |
|---|---|---|
| Confusing correlation with causation | predictive != causal | no causal language; label genes as candidate biomarkers |
| Multiple testing in DEG | thousands of genes | FDR (Benjamini-Hochberg) control |
| Gene-ID ambiguity / duplicates | Entrez vs HGNC, version drift | harmonise via NCBI Entrez IDs; map to symbols for reporting |
| Cross-dataset DEG discordance | different resistance states | require consistent direction; report discordant genes too |
| Pathway over-interpretation | enrichment noise at small n | use FDR; cross-check GO/KEGG/Reactome/GSEA |

### 7.6 Engineering and reproducibility

| Problem | Why it happens | Mitigation |
|---|---|---|
| Non-reproducible runs | random seeds, package versions | fixed seeds; pin versions; record `sessionInfo()` |
| Wide count matrices | tens of thousands of genes | RDS sidecar; documented reader |
| Environment drift (R + Python) | mixed toolchain | lock files / requirements; document versions |
| Data provenance loss | confusion over raw vs processed | record accession, NCBI counts URL, format, download date |

---

## 8. Deliverables

| Output | Description |
|---|---|
| Two GEO datasets | independent resistant vs sensitive bulk RNA-seq (GSE202859, GSE193258) |
| Clean count matrices | preprocessed gene × sample matrices for both cohorts |
| QC results | PCA, sample clustering, QC metrics |
| DEG tables | significant up/down genes per dataset |
| Validated DEG list | genes significant in both, consistent direction |
| GO / KEGG results | enriched biological processes and pathways |
| ML models | Logistic Regression, Random Forest, SVM (+ XGBoost extension) |
| Performance metrics | Accuracy, Precision, Recall, F1, ROC-AUC + CIs, confusion matrices |
| Biomarker panel | ranked candidate genes, cross-referenced to pathways |
| Publication-quality figures | PCA, volcano, heatmap, UpSet/Venn, GO/KEGG, ROC, confusion, feature importance |
| Reproducible report | Quarto/RMarkdown HTML report + `sessionInfo()` |
| Code repository | scripts 01–08, documented and seeded |

---

## 9. Claims policy and limitations

- ML on 18 discovery / 18 validation samples is **exploratory biomarker discovery**; no clinical or
  diagnostic claim.
- The signature is a **hypothesis generator**; cross-dataset agreement is evidence of reproducibility,
  not proof of mechanism.
- Report the full result surface, including null/asymmetric outcomes, unchanged.
- The `-OR` vs `osi_DTP` endpoint difference and the drug-exposure confound are stated as limitations.
- To strengthen any clinical claim, a larger independent NSCLC cohort (preferably patient tumours)
  would be required as a further validation set.

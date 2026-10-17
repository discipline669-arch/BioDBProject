# Fixes

Actionable defects / gaps in the current pipeline and artefacts. Each: **what → where → action → priority**.

Priority: P0 (correctness), P1 (completeness), P2 (cosmetic/docs).

---

## Correctness (P0)

### X1. Stale Stage 5 enrichment artefacts
**What.** `enrichment_*` and `gsea_*` tables/figures were generated from the **pre-DESeq2 (OLS)
DEGs**; the validated set changed from 348 → 1112 genes.
**Where.** `results/tables/enrichment_*`, `results/tables/gsea_*`, matching figures;
produced by `scripts/03b_enrichment.py`.
**Action.** Re-run `python scripts/03b_enrichment.py` on the DESeq2 DEGs. Confirm the validated-set
gene count logged matches `validated_DEGs.csv`.
**Priority.** P0.

### X2. Stale ML artefacts (phases 4–8)
**What.** All machine-learning outputs were produced from the previous log2CPM matrix and OLS DEG
prior. The expression matrix is now **VST** and the DEG prior changed.
**Where.** `results/tables/{nested_cv_*,external_*,biomarker_panel,feature_*_*,shap_*,*_qc_metrics}`,
ML figures; produced by `scripts/04..08`.
**Action.** Re-run `python scripts/run_pipeline.py` on real data.
**Priority.** P0.

### X3. Entrez→symbol duplicate handling
**What.** `load_ncbi_counts` collapses many Entrez IDs onto symbols; duplicate symbols could create
duplicated matrix rows and inflate/deflate DEG tests.
**Where.** `scripts/R_utils.R` (`load_ncbi_counts`), used by `02_preprocess_qc.R`, `03_deg_enrichment.R`.
**Action.** Verify whether duplicates exist; if so, collapse deterministically (e.g. keep max-mean
row) and log the number dropped.
**Priority.** P0 (verify; likely benign because NCBI already maps 1:1-ish, but confirm).

### X4. Volcano NA handling
**What.** DESeq2 independent filtering leaves `padj = NA`; the volcano emits
"Removed N rows containing missing values" and those genes are silently dropped from the plot.
**Where.** `volcano()` in `scripts/03_deg_enrichment.R`.
**Action.** Confirm dropped genes are only low-count/independent-filtered ones (expected). Optionally
annotate NA genes as a separate "filtered" category rather than dropping.
**Priority.** P1.

### X5. `align_gene_space` variance filter after VST
**What.** `align_gene_space` drops zero-variance genes. VST can produce near-zero variance genes;
confirm the filter only removes true constants and does not silently shrink the feature space.
**Where.** `scripts/ml/data.py`.
**Action.** Log number of genes dropped and confirm it matches zero-variance count only.
**Priority.** P1.

### X6. GSEA missing for the validated set
**What.** `03b_enrichment.py` skips GSEA for the validated tag (`rank=None`); there is no
`gsea_validated_*`.
**Where.** `scripts/03b_enrichment.py`.
**Action.** Decide (see D3): either build a rank metric for the validated set (e.g. signed mean
log2FC) and run GSEA, or document explicitly why it is ORA-only.
**Priority.** P1.

---

## Completeness (P1)

### X7. Stage 5 not in the report
**What.** `summary.md` and `report.qmd` do not surface enrichment / GSEA results.
**Where.** `scripts/08_report.py`, `report.qmd`.
**Action.** Add sections listing top enriched terms per source (validated set) + GSEA hits, and embed
the dotplots/barplots.
**Priority.** P1.

### X8. `cross_DEG_upset.png` is not an UpSet plot
**What.** The file named "upset" is a 4-bar summary, not a set-intersection matrix; the plan §8 asks
for UpSet/Venn.
**Where.** `03_deg_enrichment.R` (bar chart) vs plan §8.
**Action.** Either produce a real UpSet (R `UpSetR`/`ComplexUpset`, or Python `upsetplot`) or rename
the artifact to `cross_DEG_overlap_bar.png` and adjust the plan to accept the bar summary.
**Priority.** P1.

### X9. No explicit Venn figure
**What.** Two-set overlap is only printed to the console.
**Where.** `03_deg_enrichment.R`.
**Action.** Add a small 2-set Venn/overlap figure, or rely on the UpSet/bar from X8 and document.
**Priority.** P2.

### X10. Nested-CV confidence intervals
**What.** `nested_cv_metrics.csv` lacks bootstrap 95% CIs (external validation has them).
**Where.** `scripts/05_train_models.py`.
**Action.** Add bootstrap CIs for AUC/PR-AUC/F1 to the nested-CV metrics.
**Priority.** P1.

### X11. SVM probability calibration
**What.** `ProbabilitySVC` derives probabilities via `sigmoid(decision_function)`; these are not
calibrated probabilities.
**Where.** `scripts/ml/models.py`.
**Action.** Either wrap in `CalibratedClassifierCV` inside training folds, or document that SVM
probabilities are monotone scores (use rank-based metrics, not Brier, for SVM).
**Priority.** P1.

### X12. Empty `results/models/`
**What.** Fitted models are not persisted (joblib gitignored).
**Where.** `results/models/`, `.gitignore`.
**Action.** Document the exact reproduction command (fixed seeds) in README/report, per D9.
**Priority.** P2.

---

## Docs / hygiene (P2)

### X13. `plan.md` "Known gaps" is out of date
**What.** It still says DEGs come from the "base-R OLS fallback (no DESeq2/limma — no Bioconductor
host)".
**Where.** `docs/plan.md` lines ~9–12.
**Action.** Replace with "DESeq2 (Bioconductor installed)". Keep the enrichment-in-Python and
target_z caveats.
**Priority.** P2.

### X14. `roadmap.md` prerequisites drift
**What.** Prerequisites list does not mention Bioconductor; the `03_deg_enrichment.R` line is
correct but should note `run_in_r` default.
**Where.** `docs/roadmap.md`.
**Action.** Add Bioconductor to prerequisites; note `deg.enrichment.run_in_r: false`.
**Priority.** P2.

### X15. `README.md` consistency
**What.** Verify no stale mention of OLS/no-Bioconductor and that Stage 5 is listed as the first
Python step.
**Where.** `README.md`.
**Action.** Re-read and align with current state.
**Priority.** P2.

### X16. `docs/` is gitignored
**What.** Root `.gitignore` ignores `docs/`, so this set of documents (including `goal.md`,
`decisions.md`, `tasks_left.md`, `fix.md`, `tedious_fix.md`, `non_fixable.md`) will not be tracked.
**Where.** root `.gitignore`.
**Action.** Confirm intent with the user: keep ignored, or add a negation rule to track selected docs.
**Priority.** P2.

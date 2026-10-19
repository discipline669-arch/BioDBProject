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
**Status (2026-10).** Fix has been applied — `load_ncbi_counts` discards rows whose symbol fails to
resolve and **logs `n_dup` (the number of duplicate symbols collapsed)** so duplicates can no longer
be created silently. Whether/where duplicates actually occur is confirmed on the next real-data run.

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
**Status (2026-10).** Done — `align_gene_space` now logs the gene-space intersection size, per-cohort
zero-variance genes (names capped at 20 with "+N more"), genes measured only in one cohort, and the
total drop count. Final feature space is unchanged.

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
**Status (2026-10).** Done — `08_report.py` writes the "Functional enrichment (Stage 5)" section in
`summary.md` (top-6 validated terms per source + leading-edge genes + GSEA top-5 per cohort);
`report.qmd` gained section 3b embedding the same tables and the dotplot/GSEA figures. Verified
against the real-data run (BH-selected terms render; synthetic mode skips gracefully).

### X8. `cross_DEG_upset.png` is not an UpSet plot
**What.** The file named "upset" is a 4-bar summary, not a set-intersection matrix; the plan §8 asks
for UpSet/Venn.
**Where.** `03_deg_enrichment.R` (bar chart) vs plan §8.
**Action.** Either produce a real UpSet (R `UpSetR`/`ComplexUpset`, or Python `upsetplot`) or rename
the artifact to `cross_DEG_overlap_bar.png` and adjust the plan to accept the bar summary.
**Priority.** P1.
**Status (2026-10).** Renamed to `cross_DEG_overlap_bar.png` in `scripts/03_deg_enrichment.R`
(figure name + `report.qmd` reference) so the artifact name no longer overstates what it is, AND
a **true UpSet-style figure now ships**: `scripts/09_upset.py` writes
`cross_DEG_overlap_upset.png` (Discovery / Validation / Validated-intersection set structure,
counts on top, constellation matrix). `upsetplot` 0.9.0 proved incompatible with the project's
pandas 3.x stack, so 09 contains a hand-rolled deterministic renderer (documented in the module
docstring). Embedded in `report.html` (A4) and audited OK in `docs/tasks_left.md` A5.

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
**Status (2026-10).** Done — `05_train_models.py` computes stratified-bootstrap 95% CIs
(`roc_auc_lo/hi`, `pr_auc_lo/hi`, `f1_lo/hi`, reusing `ml.metrics.bootstrap_ci`) for every
cohort x model x K row and appends them to `nested_cv_metrics.csv`. Verified on synthetic runs
(lo <= point <= hi on all 12+12 rows; see verification ledger).

### X11. SVM probability calibration
**What.** `ProbabilitySVC` derives probabilities via `sigmoid(decision_function)`; these are not
calibrated probabilities.
**Where.** `scripts/ml/models.py`.
**Action.** Either wrap in `CalibratedClassifierCV` inside training folds, or document that SVM
probabilities are monotone scores (use rank-based metrics, not Brier, for SVM).
**Priority.** P1.
**Status (2026-10).** Done (documentation route) — `ProbabilitySVC` docstring and the report/summary
notes state explicitly that SVM "probabilities" are monotone scores unsuitable for Brier-style
calibration claims; rank metrics stay valid. CalibratedClassifierCV remains an option (D-open).

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
**Status (2026-10).** Done — known-gaps block rewritten (DESeq2 resolved 2026-04; VST matrix +
stage-5/ML regenerations pending re-run; enrichment caveat, target_z caveat, and the renamed
overlap-bar note kept).

### X14. `roadmap.md` prerequisites drift
**What.** Prerequisites list does not mention Bioconductor; the `03_deg_enrichment.R` line is
correct but should note `run_in_r` default.
**Where.** `docs/roadmap.md`.
**Action.** Add Bioconductor to prerequisites; note `deg.enrichment.run_in_r: false`.
**Priority.** P2.
**Status (2026-10).** Done — prerequisites now cover the Windows R host (Rscript 4.6.1 +
Bioconductor) and the current Linux Python host (repo `.venv` + `run_pipeline.py` via the venv),
plus the `deg.enrichment.run_in_r: false` note.

### X15. `README.md` consistency
**What.** Verify no stale mention of OLS/no-Bioconductor and that Stage 5 is listed as the first
Python step.
**Where.** `README.md`.
**Action.** Re-read and align with current state.
**Priority.** P2.
**Status (2026-10).** Done — README was already consistent (DESeq2-first with OLS fallback is the
live mechanism, not a stale claim); added a Linux quick-start block (repo `.venv`) and a data
re-fetch note covering untracked data artefacts.

### X16. `docs/` is gitignored
**What.** Root `.gitignore` ignores `docs/`, so this set of documents (including `goal.md`,
`decisions.md`, `tasks_left.md`, `fix.md`, `tedious_fix.md`, `non_fixable.md`) will not be tracked.
**Where.** root `.gitignore`.
**Action.** Confirm intent with the user: keep ignored, or add a negation rule to track selected docs.
**Priority.** P2.
**Status (2026-10).** Resolved as outdated — `git ls-files docs/` shows the whole `docs/` directory
IS tracked (the `.gitignore` pattern `docs/` never matched the root-level `docs/` folder; and
`decisions.md`, `fix.md` files exist and are covered). No negation rule needed.

# Decisions

Open and recently-made decisions that affect results, claims, or reproducibility.
Each entry: **context → options → recommendation → status**.

Status legend: `DECIDED` · `OPEN` · `DEFERRED`

---

## D1. Primary evaluation normalisation for external validation — `OPEN`
**Context.** External validation reports two schemes: `train_stats` (test rows rescaled with the
**training** mean/SD) and `target_z` (test rows rescaled with **their own** stats, transductive).
`target_z` gives AUC ≈ 1.0 which is optimistic; `train_stats` is conservative and realistic.

**Options.**
1. Headline `train_stats`; report `target_z` as a secondary optimistic bound.
2. Headline `target_z`; report `train_stats` as a stress test.
3. Report both as co-equal, no headline.

**Recommendation.** Option 1 — `train_stats` is the honest generalisation estimate; `target_z` is a
transductive upper bound that leaks test-set statistics.

**Status.** DECIDED (2026-10, user confirmation): Option 1 kept — `train_stats` is the headline;
`target_z` reported as optimistic bound only. Summary/report wording updated (08_report.py).

---

## D2. Pre-registered primary model and feature count K — `OPEN`
**Context.** The report enumerates a model × K grid; picking the best cell post hoc is the winner's
curse.

**Options.** (a) pre-register one model+K and treat the rest as exploratory; (b) report the full
grid only.

**Recommendation.** (a) pre-register a single primary config (e.g. **LogReg + a fixed K chosen by
inner CV**), and label everything else exploratory. Choose it from the recovered run, then freeze.

**Status.** DECIDED (2026-10, user confirmation): **LogisticRegression, K=50** pre-registered;
all other model x K cells are exploratory. Stated in 08_report.py output and report.

---

## D3. GSEA engine: Python bucket-permutation vs R `fgsea` — `OPEN`
**Context.** Stage 5 GSEA uses a size-bucketed permutation null in Python (an approximation).
`fgsea` is now installed in R (exact, well-tested).

**Options.**
1. Keep Python GSEA (self-contained; approximate p-values).
2. Switch GSEA to R `fgsea` (exact; adds an R↔Python handoff and a second toolchain dependency).
3. Keep Python, add R `fgsea` as a cross-check on the validated set only.

**Recommendation.** Option 3 if time allows, else Option 1 with an explicit "approximate
permutation null" caveat. Do not silently present Python GSEA as exact.

**Status.** DECIDED (2026-10, user confirmation): Option 3 implemented — Python GSEA stays
primary; `scripts/03c_fgsea_crosscheck.R` (R `fgsea`, micromamba env) re-ranks the same signed
log2FC vectors against the same GMT collections exported by Stage 5
(`results/tables/gene_sets/gene_sets_{GO_BP,KEGG,Reactome}.gmt`), writing
`gsea_<ACC>_<SRC>_fgsea.csv`; 08_report.py reports NES concordance + top-5 overlap.

---

## D4. GO-BP source: Enrichr GMT (Python) vs GO.db (R) — `DECIDED`
**Context.** User instruction: use GO from Enrichr; do **not** use `gene2go`. Gene sets unified on
**symbols**.

**Decision.** GO-BP from the Enrichr `GO_Biological_Process_2023` GMT, run in Python. R-side
clusterProfiler GO is disabled by default (`deg.enrichment.run_in_r: false`) to keep a single source
of truth; it may be re-enabled only as a cross-check (see D11 / B5).

**Status.** DECIDED.

---

## D5. Definition and ranking of the "validated DEG set" — `DECIDED`
**Context.** Validated = significant in both cohorts with consistent direction. Ranking currently
uses `|log2FC_disc| + |log2FC_val|`.

**Decision.** Keep the intersection-with-consistent-direction definition. Ranking by summed |log2FC|
is acceptable; document it. Do not require identical LFC magnitude.

**Status.** DECIDED (revisit if D11 shrinkage changes LFCs).

---

## D6. XGBoost status in the deliverable — `DECIDED`
**Context.** Proposal mandates LR/RF/SVM; XGBoost is an extension.

**Decision.** Keep XGBoost as a clearly-labelled **extension**, not a co-primary model. All claims
reference LR/RF/SVM first.

**Status.** DECIDED.

---

## D7. Washout samples as a sensitivity analysis — `DEFERRED`
**Context.** Washout samples were excluded from training (reversibility, not a stable state). They
could test whether the signature reverts.

**Options.** (a) leave excluded; (b) add an optional sensitivity check applying the locked model to
washout samples.

**Recommendation.** (b) as an optional, clearly-labelled sensitivity section if time permits; do not
fold into the main result.

**Status.** UN-DEFERRED and implemented (2026-10, user confirmation): the validation cohort DOES
carry an excluded time-course arm (osi_acute / short_washout / long_washout 72h-96h-7d-10d per
line; HCC2935 excluded as non-shared). The extended blind VST is refit on all 60 samples by
`scripts/02b_vst_extend.R` (primary matrix untouched), and `scripts/10_washout_sensitivity.py`
applies the LOCKED discovery models (D9 persistence) under both `train_stats` and `target_z`
schemes. Outputs: `washout_sensitivity{,_groups}.csv` + `washout_sensitivity.png`; reported by
08_report.py. No accuracy claim is made for these samples (no two-class labels by design).

---

## D8. Add a patient-tumour validation cohort — `DEFERRED`
**Context.** All conclusions are cell-line based. A patient cohort would materially strengthen any
translational claim.

**Recommendation.** Out of scope for this project (requires new data acquisition + label
harmonisation + re-run). Keep listed as future work.

**Status.** DEFERRED.

---

## D9. Persist fitted models (joblib) — `OPEN`
**Context.** `results/models/` is empty; `*.joblib` is gitignored. Report must either ship models or
state they are reproducible artefacts.

**Options.** (a) leave gitignored, document the reproduction command; (b) un-ignore and commit
(bloats repo); (c) use Git LFS.

**Recommendation.** (a) — models are cheap to regenerate with fixed seeds; document clearly.

**Status.** DECIDED (2026-10, user confirmation — overrode recommendation): models ARE persisted
and committed. `05_train_models.py` now dumps each config's final locked model
(`ml.cv.fit_full`: same selection+scaling+inner-CV tuning on ALL samples) to
`results/models/<ACC>_<model>_K<k>.joblib`; the `results/models/*.joblib` gitignore rule was
dropped.

---

## D10. Enrichment universe for ORA — `OPEN`
**Context.** Hypergeometric ORA needs an explicit background.

**Options.** (a) union of genes measured in both cohorts; (b) all genes with annotation; (c) cohort
own measured genes.

**Recommendation.** (a) for the validated set; (c) for per-cohort runs. Record the exact universe in
the output metadata and methods.

**Status.** DECIDED (2026-10, user confirmation — overrode recommendation): the ORA background is
the **all-annotated-genes universe per source** (all genes present in that source's gene-set
collection) for every tag (per-cohort and validated). Implemented in `03b_enrichment.py`
(`bg_univ`); run logs print the per-source background sizes. GSEA is whole-transcriptome and
unaffected. Enrichment tables from 2026-10 onward reflect this universe.

---

## D11. DESeq2 LFC shrinkage (`apeglm` / `ashr`) — `OPEN`
**Context.** Unshrunk DESeq2 LFCs are noisy for low-count genes; shrinkage stabilises ranking.

**Options.** (a) keep unshrunk LFC + BH FDR (current); (b) apply `lfcShrink` before thresholding and
cross-dataset ranking.

**Recommendation.** (a) for the primary analysis (simpler, threshold-standard); mention shrinkage as
an optional robustness check. If adopted, re-run Stage 4/5 and revisit D5.

**Status.** DECIDED (2026-10, user confirmation): keep unshrunk LFC + BH FDR for the primary
analysis (option (a)). Shrinkage (`apeglm`/`ashr`) stays an optional robustness check only.

---

## D12. Author TPM vs NCBI counts as a sensitivity check — `DEFERRED`
**Context.** NCBI harmonised counts were chosen for a shared universe; author TPM/Kallisto exists but
is not the primary input.

**Recommendation.** Optionally check whether top validated DEGs are directionally consistent in
author TPM. Not required.

**Status.** DEFERRED.

---

## D13. Report engine — `DECIDED`
**Context.** `report.qmd` (Quarto) exists but Quarto/Pandoc are not installed.

**Decision.** Use Quarto (`report.qmd` → `report.html`). Installing Quarto is a prerequisite task
(see tasks_left A4). RMarkdown remains a fallback only if Quarto cannot be installed.

**Status.** DECIDED — implemented 2026-10: Quarto 1.10.19 rendered `report.html` on the Linux host
(user-space install + micromamba R; see tasks_left A4).

---

## D14. ML feature prior: validated DEGs vs discovery DEGs — `DECIDED`
**Context.** Leakage rules require the feature prior to come from discovery, never from validation.

**Decision.** Feature selection is nested inside training folds; where a prior is used it comes from
**discovery** DEGs only. The cross-dataset validated set is used for interpretation, not as a
pre-selected feature list on the validation cohort.

**Status.** DECIDED.

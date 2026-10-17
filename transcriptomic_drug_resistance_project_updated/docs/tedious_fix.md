# Tedious Fixes

Problems that are solvable but require substantial rework of the existing pipeline (new toolchain
bridges, new data, or architectural changes). Not fixable as a small patch.

---

## T1. Exact GSEA via R `fgsea` inside the Python pipeline
**Why it is tedious.** `fgsea` is exact and well-tested, but it lives in R. Using it means either
(a) a persistent R↔Python bridge (`rpy2`) with serialisation of the ranking and gene sets, or
(b) moving Stage 5 orchestration to R, or (c) reimplementing `fgsea`'s multi-level permutation
algorithm in Python. All three change Stage 5's architecture.
**Current state.** Python GSEA uses a size-bucketed permutation null (an approximation).
**Related.** D3, X6.

---

## T2. In-pipeline GO/KEGG/Reactome via `clusterProfiler` / `GO.db`
**Why it is tedious.** Same R↔Python bridge problem as T1. The current design deliberately keeps
enrichment in Python (Enrichr GMT for GO-BP, KEGG REST, Reactome download) to avoid Bioconductor.
Switching the primary path back to R would re-do all of Stage 5.
**Current state.** R enrichment exists but is gated off (`deg.enrichment.run_in_r: false`).
**Related.** D4.

---

## T3. Install Rtools and rebuild the Bioconductor stack from source
**Why it is tedious.** Bioconductor 3.23 annotation binaries are not published, so some packages
(`GO.db`, `org.Hs.eg.db`, `reactome.db`) had to be built from source. A fully source-based setup
would need a matching Rtools toolchain and a long rebuild of the whole dependency tree.
**Current state.** DESeq2/limma/edgeR/fgsea/sva installed from binary; annotation DBs from source;
MinGW `gcc` present but Rtools is not.
**Related.** Environment only; not required for current results.

---

## T4. Add a patient-tumour validation cohort
**Why it is tedious.** Requires new data acquisition (GEO/controlled access), label harmonisation
(responder/progressor definitions differ from cell-line labels), a new metadata builder, and a
re-run of the DEG + enrichment + external-validation stages under a new label policy.
**Current state.** Out of scope; listed as future work.
**Related.** D8.

---

## T5. Increase the number of cell lines / samples
**Why it is tedious.** More lines changes the CV structure (more than 3 grouped folds), the balanced
design, and possibly the label policy; requires additional datasets matched on cancer type and drug.
**Current state.** 3 lines → leave-one-cell-line-out (3 folds). This is the root driver of wide CIs
and unstable feature selection.
**Related.** N3 (non-fixable tradeoff), goal §non-goals.

---

## T6. Use author-specific quantification (Kallisto/TPM) as the primary input
**Why it is tedious.** The pipeline is built on NCBI harmonised raw counts for a shared gene
universe and DESeq2. Switching to author TPM/Kallisto breaks the shared universe, changes
normalisation, and re-does Stages 2–5 for both cohorts.
**Current state.** NCBI counts are primary; author TPM is only an optional sensitivity check (D12).

---

## T7. More rigorous CV (repeated grouped CV / leave-one-sample-out variants)
**Why it is tedious.** The evaluation harness, metric aggregation, and figure generation assume
leave-one-cell-line-out with 3 folds. Adding repeats or alternative schemes changes the partition
logic and all downstream aggregation.
**Current state.** 3-fold grouped nested CV.

---

## T8. Cross-cohort batch correction (ComBat / RUV)
**Why it is tedious.** The design intentionally keeps cohorts separate and treats the second cohort
as an independent validation set. Applying batch correction would entangle the two cohorts, change
the validation semantics, and require reworking the leakage rules.
**Current state.** Cohorts are never pooled; NCBI harmonisation is the only shared processing.
**Related.** N8, N15.

---

## T9. Commit models and large data with Git LFS + CI
**Why it is tedious.** Requires Git LFS setup, un-ignoring `*.joblib` / processed matrices, CI wiring,
and storage policy. Not needed for reproducibility given fixed seeds.
**Current state.** Models regenerate; `results/models/` empty.
**Related.** D9, X12.

---

## T10. Make report rendering part of the pipeline
**Why it is tedious.** `run_pipeline.py` currently stops at `08_report.py`; auto-rendering would add
a Quarto step, template parameterisation, and failure handling inside the pipeline.
**Current state.** Rendering is a manual `quarto render report.qmd` step (blocked on install).
**Related.** A4, D13.

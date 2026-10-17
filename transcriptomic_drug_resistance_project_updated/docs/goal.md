# Achievable Goal — NSCLC / osimertinib transcriptomic resistance analysis

## One-sentence goal

Build an end-to-end, leakage-safe, reproducible bulk-RNA-seq analysis that (a) derives a
cross-dataset **validated transcriptional signature** of acquired osimertinib resistance in
EGFR-mutant NSCLC cell lines, (b) characterises it biologically (GO-BP / KEGG / Reactome ORA +
GSEA), and (c) evaluates ML classifiers over it — reported strictly as **exploratory biomarker
discovery**, not clinical or causal proof.

## Why this goal is achievable

- Two independent GEO cohorts already downloaded and label-resolved (36 samples total).
- R + Bioconductor (DESeq2) now installed, so the whole R track (QC → DEG) runs without the OLS
  fallback.
- Stage 5 enrichment is implemented in Python and has already executed once on real data.
- ML track (phases 4–8) already executed once on real data.
- Only re-runs + report integration remain; no new data acquisition is required.

## Definition of done

- [ ] R track end-to-end via **DESeq2** (`02_preprocess_qc.R`, `03_deg_enrichment.R`) with no OLS fallback.
- [ ] R functional enrichment stays delegated to Stage 5 (`config: deg.enrichment.run_in_r: false`).
- [ ] Stage 5 (`03b_enrichment.py`) re-run on the **DESeq2** DEGs / validated set (current outputs are stale).
- [ ] Python ML phases 4–8 re-run on the new **VST** matrix and DEGs (`scripts/run_pipeline.py`).
- [ ] Stage 5 tables/figures integrated into `results/reports/summary.md` and `report.qmd`.
- [ ] `report.qmd` rendered to `report.html` (requires Quarto + Pandoc).
- [ ] `docs/plan.md` §8 deliverable table fully satisfied by artefacts in `results/`.
- [ ] `config/leakage_checklist.md` all items green after the re-run.
- [ ] Claims conservative throughout (candidate biomarkers; no causality; no clinical claim).

## In scope

- **Data:** GSE202859 (discovery), GSE193258 (independent validation); cell lines PC9, H1975,
  HCC827; 18 + 18 samples; Sensitive vs Resistant per `docs/class_labels_resolved.md`.
- **DEG:** DESeq2 `~ cell_line + condition`, FDR < 0.05, |log2FC| > 1.
- **Cross-dataset validation:** genes significant in both with consistent direction → validated set.
- **Enrichment:** GO-BP (Enrichr GMT), KEGG, Reactome over-representation + pre-ranked GSEA (Python).
- **ML:** LogReg, Random Forest, SVM (+ XGBoost extension); leave-one-cell-line-out nested CV;
  one locked external validation; SHAP / coefficients / permutation importance; candidate panel.
- **Deliverable:** reproducible HTML report + figures + tables.

## Out of scope (non-goals)

- No causal or mechanistic claims about individual genes.
- No clinical / diagnostic claims — n is too small and cell lines are not patients.
- No patient-tumour validation cohort.
- No isoform / fusion / CNV / immune-deconvolution analysis.

## Claim discipline (binding)

- Predictive genes are **candidate biomarkers**, not proven drivers.
- ML on 18 discovery samples is **exploratory**; cross-dataset agreement is evidence of
  **reproducibility**, not mechanism.
- Report the **full result surface** (including null/asymmetric outcomes), not just the best cell.
- State the drug-exposure confound and the `-OR` vs `osi_DTP` endpoint difference as limitations.

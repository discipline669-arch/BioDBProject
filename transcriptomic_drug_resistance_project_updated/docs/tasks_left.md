# Tasks Left

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

Last updated after: Bioconductor install + DESeq2 re-run of R phases 1b/2/3.

## Current results snapshot (DESeq2 re-run)

| Quantity | Value |
|---|---|
| Discovery DEGs (GSE202859) | 2785 (1435 up / 1350 down) |
| Validation DEGs (GSE193258) | 4852 (3651 up / 1201 down) |
| Shared DEGs | 1273 |
| Consistent direction | 1112 |
| **Validated DEG set** | **1112** |
| Discovery genes after VST | 23585 |
| Validation genes after VST | 25823 |
| R enrichment in-pipeline | disabled (`run_in_r: false`), delegated to Stage 5 |

Stage 5 and ML outputs on disk are from the **previous (OLS log2CPM) run** and are therefore **stale**.

---

## A. Must-do (blocks "definition of done" in `goal.md`)

### A1. Re-run Stage 5 enrichment on DESeq2 DEGs — `[ ]`
Outputs `enrichment_*` / `gsea_*` were produced from OLS-era DEGs. Rebuild them.

```powershell
& "C:\Program Files\Python311\python.exe" scripts/03b_enrichment.py
```

Typical output tags: `enrichment_{GSE202859,GSE193258,validated}_{GO_BP,KEGG,Reactome}.csv`,
`gsea_{GSE202859,GSE193258}_{GO_BP,KEGG,Reactome}.csv`, plus dotplot/barplot figures.

### A2. Re-run ML phases 4–8 on VST matrix + new DEGs — `[ ]`
`expression_processed.csv` changed (VST), and the DEG prior changed (1112 validated). All ML
artefacts (`nested_cv_*`, `external_*`, `biomarker_panel`, SHAP, feature stability, ROC/PR, etc.)
must be regenerated.

```powershell
$env:BIODB_SYNTHETIC = $null
& "C:\Program Files\Python311\python.exe" scripts/run_pipeline.py
# or step by step: 04 -> 05 -> 06 -> 07 -> 08
```

### A3. Integrate Stage 5 into the report — `[ ]`
`scripts/08_report.py` (`summary.md`) and `report.qmd` currently do not summarise the enrichment
tables/figures. Add sections: top enriched terms per source for the validated set, plus GSEA hits.

### A4. Install Quarto + Pandoc and render the report — `[!]`
Not installed; `report.qmd` cannot render. Blocked on installing Quarto (which bundles/uses Pandoc),
then:

```powershell
quarto render report.qmd    # -> report.html
```

### A5. Audit `plan.md` §8 deliverables against `results/` — `[ ]`
Confirm every row is satisfied by an actual file; add anything missing. Known suspects:
- true **UpSet plot** — `cross_DEG_upset.png` is a bar chart, not a set-intersection UpSet;
- explicit **Venn** figure — only counts in the console log;
- **calibration/Brier** is present for external but check nested CV;
- GO/KEGG/Reactome **figures** exist for Python only (R GO is intentionally off).

### A6. Refresh the leakage checklist after the re-run — `[ ]`
`config/leakage_checklist.md` must be re-validated against the new run (fold count, nested
selection, single external look, thresholds fixed on training).

### A7. Update docs that describe resolved gaps — `[ ]`
- `docs/plan.md` §"Known gaps": the "base-R OLS fallback (no Bioconductor)" gap is **resolved**;
  update to DESeq2. Keep the enrichment-in-Python and target_z caveat lines.
- `docs/roadmap.md` verify block: add the Bioconductor prerequisite note; the `03_deg_enrichment.R`
  line already says enrichment moved to Stage 5 — confirm wording.
- `README.md`: confirm no stale reference to OLS/no-Bioconductor.

---

## B. Should-do (quality / completeness)

### B1. Add nested-CV confidence intervals — `[ ]`
External validation reports bootstrap 95% CIs; nested CV metrics (`nested_cv_metrics.csv`) should
also carry bootstrap CIs for AUC/PR-AUC.

### B2. Verify Entrez→symbol deduplication — `[ ]`
`load_ncbi_counts` maps Entrez→symbol from `Homo_sapiens.gene_info.gz`; check for duplicate symbols
creating duplicated rows before DEG/enrichment.

### B3. Document the enrichment universe — `[ ]`
Decide and record the universe used for ORA (union of measured genes vs all annotated) in
`docs/decisions.md` and in the enrichment script output metadata.

### B4. Regenerate or explicitly document `results/models/` — `[ ]`
`results/models/` is empty because joblib is gitignored. Either persist models with a documented
location/command or state in the report that models are reproducible artefacts, not committed.

### B5. Cross-check GO results Python (Enrichr) vs R (clusterProfiler) — `[ ]`
Optional validation: temporarily set `deg.enrichment.run_in_r: true` on the validated gene list to
compare GO-BP terms; record agreement as a QC note (do not merge the two outputs).

---

## C. Blockers / external dependencies

| ID | Blocker | Unblocks |
|---|---|---|
| BL-1 | Quarto + Pandoc not installed | A4 (report render) |
| BL-2 | No patient-tumour cohort available | strengthens any clinical claim (out of scope) |
| BL-3 | `imblearn` not installed | in-fold SMOTE experiments (currently unused by design) |
| BL-4 | `upsetplot` (Python) not installed | true UpSet figure in A5 |

---

## D. Fast sanity commands

```powershell
# R toolchain present?
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" -e "cat(rownames(installed.packages())[rownames(installed.packages()) %in% c('DESeq2','limma','fgsea','clusterProfiler','org.Hs.eg.db')], sep='\n')"

# outputs count
(Get-ChildItem results/tables -File).Count
(Get-ChildItem results/figures -File).Count
```

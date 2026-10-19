# Tasks Left

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked

Last updated after: 2026-10 code-fix pass (ML robustness + doc refresh; synthetic-run verified).

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

Stage 5 and ML outputs were regenerated on the DESeq2 DEGs by the **2026-10 re-runs (A1+A2, done —
Linux host, repo `.venv`)**: `enrichment_validated_*` carries `query_size=1112` (was 348 in the OLS
era); `nested_cv_metrics.csv` is 48 rows with bootstrap-CI columns (0 bound violations);
`biomarker_panel/external_*` all fresh in `results/`.

---

## A. Must-do (blocks "definition of done" in `goal.md`)

### A1. Re-run Stage 5 enrichment on DESeq2 DEGs — `[x]` (2026-10)
Regenerated `enrichment_*` / `gsea_*` on the 1112-gene validated set (`query_size=1112` in all
three sources). Outputs reviewed in `results/tables|figures`.

```powershell
& "C:\Program Files\Python311\python.exe" scripts/03b_enrichment.py
```

Typical output tags: `enrichment_{GSE202859,GSE193258,validated}_{GO_BP,KEGG,Reactome}.csv`,
`gsea_{GSE202859,GSE193258}_{GO_BP,KEGG,Reactome}.csv`, plus dotplot/barplot figures.

### A2. Re-run ML phases 4–8 on VST matrix + new DEGs — `[x]` (2026-10)
Full real-mode chain run via the Linux-host `.venv` (`python -u scripts/run_pipeline.py`,
~14 min). Verified: group key `cell_line` (3 groups) both cohorts; `nested_cv_metrics.csv`
48 rows with bootstrap CIs (0 bound violations); panel/external/OOF fresh; report notes present.
Windows block below kept for reference.

```powershell
$env:BIODB_SYNTHETIC = $null
& "C:\Program Files\Python311\python.exe" scripts/run_pipeline.py
# or step by step: 04 -> 05 -> 06 -> 07 -> 08
```

### A3. Integrate Stage 5 into the report — `[x]` (2026-10)
- `scripts/08_report.py`: summary.md gains "Functional enrichment (Stage 5)" — top-6 validated
  terms per source (BH), leading-edge gene previews, GSEA top-5 per cohort, graceful skip in
  synthetic mode. Verified live on real data.
- `report.qmd`: new section "3b. Functional enrichment (Stage 5)" — ORA top tables, dotplots,
  GSEA tables + figures, reusing the `rd()`/`inc()` helpers.

### A6. Refresh the leakage checklist after the re-run — `[x]` (2026-10)
`config/leakage_checklist.md` re-validated against the 2026-10 run: all items checked with
per-item evidence notes (group-aware split log lines, in-fold selection code sites, nested
brier/CIs, exploratory claim notes). Determinism evidence anchored to the synthetic double-run.

### A4. Install Quarto + Pandoc and render the report — `[x]` (2026-10)
Rendered on the Linux host without sudo: Quarto 1.10.19 (user tarball in `/tmp/opencode`) +
R 4.5.3/knitr/rmarkdown via micromamba env. Quarto detected the R engine and produced
`report.html` (77 KB) including the A3 enrichment sections and the BL-4 UpSet figure.

```bash
export PATH=/tmp/opencode/quarto-1.10.19/bin:/tmp/opencode/mmenv/bin:$PATH
quarto render report.qmd    # -> report.html
```

(Windows route below kept for reference.)

Original note: Not installed then; `report.qmd` cannot render. Blocked on installing Quarto
(which bundles/uses Pandoc), then:

```powershell
quarto render report.qmd    # -> report.html
```

### A5. Audit `plan.md` §8 deliverables against `results/` — `[x]` (2026-10)

| Plan §8 item | Delivered by | Verdict |
|---|---|---|
| Two GEO datasets | `data/GSE{202859,193258}/` (downloads on disk, untracked per AC10) | OK |
| Clean count matrices | `data/GSE*/expression_processed.{csv,rds}` (on disk, untracked) | OK |
| QC results | `<ACC>_qc_metrics.csv` + PCA/correlation/heatmap/volcano figures | OK |
| DEG tables | `<ACC>_DEG_{full,up,down,significant}.csv` (DESeq2-era, fresh) | OK |
| Validated DEG list | `validated_DEGs.csv` (1112) + `cross_DEG_overlap.csv` | OK |
| GO/KEGG results | 9 enrichment + 6 GSEA tables + dotplots/GSEA figures (`query_size=1112`) | OK |
| ML models | 4 families in code; `results/models/` empty — **documented as reproducible artefacts (B4/D9)** | ✍ documented gap |
| Performance metrics | `nested_cv_metrics.csv` (48 rows, brier + bootstrap CIs), `external_validation.csv` (+CIs, calibration figure), confusion/ROC/PR covers nested CV too (`brier` column) | OK |
| Biomarker panel | `biomarker_panel.csv` (100-gene composite; stability + nested-freq + SHAP z-scores); pathway cross-ref via report/summary Stage 5 sections (A3) | OK |
| UpSet/Venn figures | **true UpSet exists:** `results/figures/cross_DEG_overlap_upset.png` (scripts/09_upset.py: 3,579 validation-only / 1,512 discovery-only / 1,112 consistent across all three / 161 inconsistent overlap) + R bar summary (renamed `cross_DEG_overlap_bar.png`, emitted on next R re-run); Venn stays console-level counts (now inside UpSet) | OK |
| Reproducible report | `results/reports/{summary.md,session_info.txt}` ✓; `report.html` pending Quarto (A4/BL-1) | ✍ blocked |
| Code repository | scripts 00–08 + helpers, seeded, documented | OK |

### A6. Refresh the leakage checklist after the re-run — `[x]` (2026-10)
See `config/leakage_checklist.md` (all items checked with evidence, 2026-10 run).

### A7. Update docs that describe resolved gaps — `[x]` (2026-10)
- `docs/plan.md` §"Known gaps": rewritten — DESeq2 resolution + pending re-run caveats recorded.
- `docs/roadmap.md`: prerequisites updated (Windows R host + Bioconductor, Linux Python host via
  repo `.venv`, `run_in_r: false` note).
- `README.md`: status refreshed (DESeq2 re-run, validated set 1112, venv host, untracked data
  artefacts + re-fetch instructions); Linux quick-start block added.

---

## A8. Pending-from-fix-pass leftovers — `[x]` (2026-10 re-run)
- X3 `[x]`: real 2026-10 run logs `n_dup` per `load_ncbi_counts` — Entrez→symbol dedup exercised on
  both cohorts with no error; R tracks completed DESeq2-first (no OLS fallback).
- SVM calibration `[x]`: kept the documented caveat (X11) — `train_stats` headline unaffected;
  revisit only if calibration becomes decision-relevant.
- CI-on-real `[x]`: 2026-10 re-run `nested_cv_metrics.csv` (48 rows) — 0 CI-bound violations.

---

## A9. Decision-gate implementation (D1–D12) — `[x]` (2026-10)
All user-confirmed decisions implemented and re-run end-to-end (see `docs/decisions.md`):
- D1/D2: `train_stats` headline + pre-registered primary config (LogReg K=50); stated by
  `08_report.py` and `report.qmd`.
- D3: `scripts/03c_fgsea_crosscheck.R` (R `fgsea`, micromamba env) → `gsea_*_fgsea.csv`;
  NES concordance (rho 0.67–0.86) and top-5 overlap reported in summary/report. Python stays primary.
- D7: `scripts/02b_vst_extend.R` (blind VST refit on all 60 GSE193258 samples) +
  `scripts/10_washout_sensitivity.py` (locked discovery models on osi_acute/short/long-washout;
  anchors DMSO 0.05 → DTP 0.80 in the transductive scheme; line-specific duration effects).
- D9: models persisted via `ml.cv.fit_full` into `results/models/` (48 joblib bundles incl.
  `accession/model/k/cfg_seed`); gitignore rule dropped.
- D10: ORA per-source universe = all genes in that source's collection (`bg_univ`); B3 superseded.
- D11: primary DEG stats stay unshrunk LFC + BH FDR; shrinkage remains an optional check.
- D8/D12: stay deferred (user confirmation).

---

## B. Should-do (quality / completeness)

### B1. Add nested-CV confidence intervals — `[x]` (2026-10)
`nested_cv_metrics.csv` now carries `roc_auc_lo/hi`, `pr_auc_lo/hi`, `f1_lo/hi`
(`scripts/05_train_models.py`, reusing `ml.metrics.bootstrap_ci`). Verified on synthetic runs
(bounds hold for every model x K row).

### B2. Verify Entrez→symbol deduplication — `[x]` (fix applied 2026-10, blind)
`load_ncbi_counts` now discards non-resolvable mappings and logs `n_dup` collapsed duplicates.
Flagged blind (no Rscript on the fix host) — the real-data count lands with A1/A2; see A8.

### B3. Document the enrichment universe — `[x]` (2026-10, via D10)
Per-source ORA background (all genes in that source's collection) implemented in `03b_enrichment.py`
and recorded in `docs/decisions.md` D10.

### B4. Regenerate or explicitly document `results/models/` — `[x]` (2026-10, via D9)
`03/05` persist 48 locked-model bundles (`results/models/<ACC>_<model>_K<k>.joblib`, keys
`pipeline/accession/model/k/cfg_seed`); D9 confirmed committed, gitignore rule dropped.

### B5. Cross-check GO results Python (Enrichr) vs R (clusterProfiler) — `[ ]`
Optional validation: temporarily set `deg.enrichment.run_in_r: true` on the validated gene list to
compare GO-BP terms; record agreement as a QC note (do not merge the two outputs).

---

## C. Blockers / external dependencies

| ID | Blocker | Unblocks |
|---|---|---|
| BL-1 | ~~Quarto + Pandoc not installed~~ RESOLVED (A4: user-space Quarto + micromamba R) | A4 done |
| BL-2 | No patient-tumour cohort available | strengthens any clinical claim (out of scope) |
| BL-3 | `imblearn` not installed | in-fold SMOTE experiments (currently unused by design) |
| BL-4 | ~~`upsetplot` incompatible with pandas 3~~ RESOLVED | A5 done — hand-rolled UpSet renderer in `scripts/09_upset.py` |

---

## D. Fast sanity commands

```powershell
# R toolchain present?
& "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" -e "cat(rownames(installed.packages())[rownames(installed.packages()) %in% c('DESeq2','limma','fgsea','clusterProfiler','org.Hs.eg.db')], sep='\n')"

# outputs count
(Get-ChildItem results/tables -File).Count
(Get-ChildItem results/figures -File).Count
```

# Relevant Content — final_report.docx

Content that is relevant and load-bearing for the study *Cross-Cohort Transcriptomic Signatures of Osimertinib Resistance in EGFR-Mutant NSCLC Cell Lines*.

## Study identity
- Title, subtitle ("leakage-controlled, cross-dataset bulk RNA-seq and machine-learning study"), abstract, TOC.
- Research objectives (5 stated aims: DEG derivation, cross-dataset signature, biological characterisation, leakage-safe ML validation, biomarker/reversibility).

## Literature directly motivating the design
- de Miguel et al. (2023) — mSWI/SNF (SMARCA4/2) chromatin remodelling drives osimertinib resistance; source of discovery cohort GSE202859.
- Criscione et al. (2022) — osimertinib DTP transcriptional-epigenomic states, partial reversibility after washout; source of validation cohort GSE193258.
- Blaquier et al. (2023) — clinical context of acquired osimertinib resistance.
- GEO/NCBI uniform reprocessing (Barrett et al., 2013) — justification for cross-cohort gene-universe comparability.
- DESeq2 (Love et al., 2014), GSEA (Subramanian et al., 2005), fgsea (Korotkevich et al.), Enrichr (Kuleshov et al., 2016), Reactome (Gillespie et al., 2022), KEGG (Kanehisa et al.), nested-CV bias control (Varma & Simon, 2006), scikit-learn, XGBoost, R.

## Methods
- Cohorts: GSE202859 (discovery; parental vs -OR) and GSE193258 (validation; DMSO vs 3-week 500 nM osi_DTP); shared lines PC9, H1975, HCC827; 9 sensitive / 9 resistant each; excluded arms tracked in coldata_all.csv.
- Preprocessing: NCBI counts (GRCh38.p13, Entrez → symbols), min_count = 10, DESeq2 normalisation + VST, design `~ cell_line + condition`, BH FDR < 0.05 and |log2FC| > 1.
- Cross-cohort validation: 1,273 shared significant genes → 1,112 directionally consistent (161 flipped); per-cohort-only sets (1,512 / 3,579).
- Enrichment: ORA (hypergeometric + BH, per-source annotated universe, decision D10) on GO-BP/KEGG/Reactome; pre-ranked GSEA (primary Python engine) with R fgsea exact cross-check (decision D3).
- ML: group-aware nested CV (StratifiedGroupKFold by cell_line), feature selection/tuning inside folds, 4 model families × K ∈ {10…500}; pre-registered primary configuration LR, K = 50 (decision D2); train_stats headline vs target_z transductive bound (decision D1); external validation run once post-lock.
- Washout probe: VST refit blind on all 60 GSE193258 samples (scripts/02b_vst_extend.R, 10_washout_sensitivity.py); locked models applied to excluded timecourse; label-free, no accuracy claim (decision D7); models persisted (decision D9).
- Reproducibility: seed 42 in config/config.yaml, run_pipeline.py, decisions D1–D14 in docs/decisions.md, leakage_checklist.md.

## Results
- Cross-cohort reproducibility: 2,785 discovery DEGs (1,435 up / 1,350 down), 4,852 validation DEGs (3,651 up / 1,201 down); 1,112 directionally consistent signature genes.
- Biological themes: up — cell migration, ECM organisation, cytoskeleton, developmental-lineage programs; down (GSEA) — Ribosome (NES −5.3/−6.9), Spliceosome (−4.0/−6.9), ribosome biogenesis, nucleocytoplasmic transport.
- Engine robustness: NES Spearman rho 0.70–0.86, sign agreement 61–81%.
- External validation (LR K=50, train_stats): ROC-AUC 1.000 (CI 1.000–1.000), PR-AUC 1.000, sensitivity 1.000, specificity 0.444 (CI 0.111–0.778), accuracy 0.722, Brier 0.132; transductive upper bound fully separated (Brier 0.012).
- Candidate biomarker panel: composite score (stability + nested selection frequency + |SHAP|); top-20 genes HECA, KLHL24, SACK1A, HEG1, IL33R, MAP3K3, TBC1D9, EFNB2, MIR198, MTURN, SULT2B1, PDCD4, CITED2, OSTM1, ITGA6, SDC1, ASAP3, SERPINB1, INSR, YPEL5; full 100-gene panel in biomarker_panel.csv.
- Washout reversibility: transductive gradient DMSO 0.05 → acute 0.68 → DTP 0.80 → washout decay (72 h 0.85, 96 h 0.65, 7 d 0.43, 10 d 0.30); strict-scheme anchors document DTP-vs--OR distribution shift.

## Figures/tables cited in the body
- Figures 1–39 (PCA, correlation, volcanoes, heatmaps, concordance, UpSet, ORA/GSEA plots, CV panels, external validation, biomarker panel, SHAP, washout strip plot) and Table 1 (cohort selection); all backing paths in results/tables/ and results/figures/.

## Discussion/conclusion elements that belong
- Central claim: shared resistance state = motility/EMT/ECM/lineage up, translation/housekeeping down; convergence with DTP and mSWI/SNF literature.
- Honest-performance framing (bootstrap CIs, full 24-cell surface, strict vs transductive, pre-registration).
- Endpoint-mismatch (DTP vs -OR) interpretation of specificity drop.
- Limitations (n=18, three backgrounds, no clinical context, ORA universe, symbol aliasing, single external run) and future work (patient/organoid cohorts, single-cell, calibration, multi-cohort panel ensembling).
- Pipeline provenance line (script chain, config, decisions, session info).

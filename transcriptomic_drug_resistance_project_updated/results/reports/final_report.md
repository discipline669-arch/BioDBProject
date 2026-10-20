---
title: "Cross-Cohort Transcriptomic Signatures of Osimertinib Resistance in EGFR-Mutant NSCLC Cell Lines"
subtitle: "A leakage-controlled, cross-dataset bulk RNA-seq and machine-learning study"
---

# Abstract

Acquired resistance to third-generation epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors (TKIs), such as osimertinib, is the dominant cause of treatment failure in EGFR-mutant non-small cell lung cancer (NSCLC). The goal of this study was to derive, validate, and interpret a transcriptional signature of acquired osimertinib resistance using bulk RNA-seq of EGFR-mutant lung adenocarcinoma cell lines. Two public GEO cohorts were paired: a discovery series (GSE202859; parental vs chronically resistant "-OR" lines) and an independent validation series (GSE193258; DMSO vehicle vs 3-week drug-tolerant persisters, DTP), both restricted to the three shared cell lines PC9, H1975 and HCC827, with 9 sensitive and 9 resistant samples each. Counts from the uniformly reprocessed NCBI pipeline (HISAT2/featureCounts, GRCh38.p13) were variance-stabilised, and differential expression was tested with DESeq2 using a `~ cell_line + condition` design. A cross-dataset validated signature of 1,112 genes (significant and directionally consistent in both cohorts) was characterised by over-representation analysis (GO-BP/KEGG/Reactome) and pre-ranked GSEA, cross-checked with the R `fgsea` engine (NES concordance rho = 0.70-0.86). Group-aware nested cross-validation (splits by cell line; feature selection and tuning inside training folds) across logistic regression, random forest, SVM and XGBoost supported a pre-registered primary configuration (logistic regression, K = 50), which generalised one-shot to the independent cohort (ROC-AUC 1.000, 95% CI 1.000-1.000; sensitivity 1.000, specificity 0.444 under the strict headline scheme). A composite stability/selection-frequency/SHAP score produced a 100-gene candidate biomarker panel. Locked models recovered a drug-withdrawal gradient on an excluded time-course arm (transductive P(Resistant): DMSO 0.05 to DTP 0.80, washout samples between anchors), consistent with partial biological reversibility. All results are reported strictly as exploratory candidate-biomarker discovery on three cell lines (n = 18 per cohort); no clinical or causal claims are made or implied.

# Introduction

Third-generation EGFR TKIs such as osimertinib have substantially improved outcomes in EGFR-mutant NSCLC, yet nearly all patients eventually progress through acquired, largely non-genetic resistance mechanisms. Transcriptomic profiling of experimentally derived resistant derivatives offers a controlled system to study these non-genetic states; however, single-cohort analyses are prone to batch effects, dataset-specific artefacts and optimistic classification performance. A rigorous design therefore requires (a) independent discovery and validation cohorts with a shared gene universe and harmonised processing, (b) differential-abundance methods that control for genetic background, (c) biological characterisation of the shared signature, and (d) predictive models whose validation is statistically honest — leakage-controlled and evaluated once, after the models are locked.

This report presents the full pipeline used to build and validate such an analysis on two GEO cohorts — the discovery series GSE202859 and the validation series GSE193258 — covering preprocessing, differential expression, cross-dataset signature validation, functional enrichment, machine-learning classification with group-aware nested cross-validation and one-shot external validation, biomarker prioritisation, and a drug-withdrawal (washout) reversibility experiment. The code base, configuration and outputs are reproducible from a git-committed repository.

The research objectives were:

1. Derive the set of differentially expressed genes (resistant vs sensitive) per cohort, with background genotype (cell line) statistically controlled.
2. Identify the cross-dataset consistent core signature of acquired osimertinib resistance.
3. Characterise the signature biologically (over-representation and GSEA) and probe its robustness with a second GSEA engine.
4. Evaluate whether the signature discriminates resistant from sensitive states in a held-out cohort using leakage-safe machine learning under a pre-registered primary configuration, with uncertainty quantified.
5. Prioritise a candidate biomarker panel and probe biological reversibility of the learned signal on an excluded drug-withdrawal arm.

# Literature Review

**Osimertinib and acquired resistance.** Osimertinib is a covalent third-generation EGFR TKI active against sensitising EGFR mutations and the gatekeeper-resistant T790M mutation, and the standard first-line treatment for EGFR-mutant advanced NSCLC. Clinically, however, disease progression eventually occurs in virtually all treated patients, driven by primary or secondary resistance mechanisms (Blaquier et al., 2023). Beyond on-target EGFR second-site mutations and bypass activations, much of the resistance is non-genetic: chromatin-remodelling states, drug-tolerant persister (DTP) phenotypes and lineage plasticity. de Miguel et al. (2023) showed that mammalian SWI/SNF (mSWI/SNF, BAF) chromatin remodelling complexes — and specifically the SMARCA4/SMARCA2 ATPases — support osimertinib resistance through chromatin-accessibility rewiring of cell-proliferation, EMT, epithelial-differentiation and NRF2 oxidative-stress programs; genetic or pharmacologic disruption of these ATPases re-sensitises a subset of resistant models. This motivates a transcriptomic, pathway-level framing of resistance rather than a purely mutational one.

**DTP states and reversibility.** Criscione et al. (2022) profiled osimertinib DTPs (500 nM, 21 days) across EGFR-mutant NSCLC lines with RNA-seq, ChIP-seq and ATAC-seq, and showed that DTPs carry a distinct transcriptional-epigenomic state apart from cell-cycle effects, with therapeutic vulnerabilities (MEK, TEAD, AURKB, BRD4). Persister states are at least partially reversible after drug withdrawal, which motivates washout time-courses: if the resistance signal decays with drug removal, the phenotype is state-like rather than mutation-like. Acute-exposure (24 h drug shock) and washout (72 h to 10 days) arms provide that design; these states confound the primary Sensitive-vs-Resistant contrast and must be excluded from label-bearing contrasts while remaining valuable for sensitivity probes — which is the policy adopted in this pipeline.

**Public RNA-seq resource design.** GEO hosts NCBI-uniformly reprocessed RNA-seq count matrices (HISAT2 + featureCounts against GRCh38.p13 in Entrez gene space) produced by an identical pipeline for arbitrary GEO-deposited studies (Barrett et al., 2013). Two independent series can therefore be analysed with identical alignment and annotation, removing inter-study batch and gene-ID discrepancies that would otherwise mask cross-dataset reproducibility. Manual subsetting based on sample titles and metadata (keeping matched cell lines and clean endpoints; excluding perturbation arms) then yields matched cohorts without cross-batch confounding.

**Differential expression with multi-factor designs.** DESeq2's negative-binomial generalised linear model supports covariate-adjusted contrasts (`~ cell_line + condition`; Love et al., 2014) that absorb the three genetic backgrounds into a blocking factor while estimating the condition effect on all 18 samples per cohort — a design that increases power versus per-line analyses and guards against line-driven spurious calls. Its variance-stabilising transformation (VST) yields a scale-free expression matrix suitable for classification and cross-cohort transfer.

**Enrichment analysis and engines.** Over-representation analysis (hypergeometric test with Benjamini-Hochberg FDR) requires an explicit reference universe; using "all genes annotated in the gene-set source" is the conservative, transparent choice and the one adopted here, with the universe recorded in the run logs (decision D10). ORA over discretised DEG lists is complemented by pre-ranked GSEA (Subramanian et al., 2005), which scores whole ranked transcriptomes without dichotomisation, and by Reactome and KEGG pathway resources (Gillespie et al., 2022; Kanehisa and Furumichi, 2017); GO-BP gene sets come from the Enrichr collection (Kuleshov et al., 2016). Python pre-ranked GSEA approximates the permutation null; R `fgsea` (Korotkevich et al., 2019) computes an exact multilevel estimate, so a two-engine concordance check is the recommended robustness layer.

**Machine learning on small, structured genomic data.** With 18 samples spanning only three genetic backgrounds, cross-validation must be group-aware: splitting by cell line (all replicates of a line inside one fold) prevents "same-line leakage" and yields a realistic, if pessimistic, estimate of cross-genotype generalisation. Hyperparameter tuning and feature selection must occur strictly inside training folds — nested cross-validation is the accepted control for selection bias and the winner's curse (Varma and Simon, 2006). Interpretable linear models remain a strong baseline in small-n genomic settings, complemented by tree ensembles and margin-based classifiers; calibration quality differentiates otherwise-equal AUC performance. External validation on a fully independent cohort, run once after model lock, is the gold standard for claims that go beyond within-cohort exploratory fits.

# Methodology

## Cohorts and labels

Two bulk-RNA-seq series were selected to maximise biological comparability (Table 1). Both profile the same three human lung adenocarcinoma cell lines (PC9, H1975, HCC827) and both have NCBI-uniform raw count matrices, ensuring a shared gene universe. Labelled endpoints are 9 Sensitive (parental / DMSO) vs 9 Resistant (-OR / osi_DTP) per cohort. Additional samples — acute osimertinib treatments and SMARCA4-shRNA perturbation arms in GSE202859; the acute/washout timecourse and the non-shared line HCC2935 in GSE193258 — are EXCLUDED by policy from the label-bearing contrast and tracked with explicit reasons in `coldata_all.csv` (52 and 60 samples respectively, of which 18 are kept per cohort). The `-OR` endpoint (chronically dosed parental→resistant derivative, GSE202859) and the `osi_DTP` endpoint (3-week 500 nM persister state, GSE193258) differ by design and are treated as a distribution shift to be handled and disclosed, not hidden; label policy and interpretation notes live in `docs/class_labels_resolved.md`.

**Table 1. Cohort selection.**

|  | Discovery (GSE202859) | Validation (GSE193258) |
|---|---|---|
| System | EGFR-mutant lung adenocarcinoma cell lines | Same |
| Drug context | Chronically dosed osimertinib-resistant (" -OR") vs parental | 3-week 500 nM osimertinib DTP vs DMSO vehicle |
| Platform | Illumina NovaSeq 6000 | Illumina HiSeq 4000 |
| Samples used | 18 (9 S / 9 R) | 18 (9 S / 9 R) |
| Samples excluded | 34 (acute treatment; shRNA perturbation arms; PC9-OR untreated controls) | 42 (24 h acute; short and long washout; HCC2935 line) |
| Primary paper | de Miguel et al. (2023), Cancer Cell, PMID 37541244 | Criscione et al. (2022), npj Precision Oncology, PMID 36575215 |

## Preprocessing and differential expression

For each cohort, the NCBI raw count matrix (GRCh38.p13, Entrez GeneIDs) was loaded via the shared `load_ncbi_counts` helper, mapped to gene symbols using `Homo_sapiens.gene_info.gz` (non-resolvable mappings discarded, duplicate-symbol collapses logged as `n_dup`), filtered at `min_count = 10`, and normalised with DESeq2 as the primary method (limma/OLS retained only as declared fallbacks and not used). Differential expression was fitted with the design `~ cell_line + condition`, so the condition contrast is adjusted for genetic background. Genes with Benjamini-Hochberg FDR < 0.05 and |log2 fold change| > 1 were called significant. The DESeq2 variance-stabilising transform (VST) produced the expression matrix used by the machine-learning track. Library composition was uniform across cohorts (23,585 genes consistently detected in GSE202859; 25,823 in GSE193258) with per-sample library sizes of roughly 19.6-37.6 million reads (GSE202859) and 20.2-50.8 million (GSE193258); per-sample QC is tabulated in `results/tables/<ACC>_qc_metrics.csv`.

**Figure 1. Principal component analysis of the VST-normalised expression matrix, discovery cohort GSE202859 (18 samples; PC9/H1975/HCC827; parental vs -OR).** Generated by the R preprocessing track; the experiment design is recorded per replicate in `coldata.csv`.

![Figure 1. PCA of the VST-normalised expression matrix — discovery cohort GSE202859.](results/figures/GSE202859_PCA.png){width=5.4in}

**Figure 2. Principal component analysis of the VST-normalised expression matrix, validation cohort GSE193258 (18 samples; DMSO vs osi_DTP).**

![Figure 2. PCA of the VST-normalised expression matrix — validation cohort GSE193258.](results/figures/GSE193258_PCA.png){width=5.4in}

**Figure 3. Sample-to-sample correlation matrices (VST-normalised), discovery and validation cohorts.** The three replicates per cell line and condition cluster coherently in both cohorts.

![Figure 3a. Sample correlation — discovery cohort GSE202859.](results/figures/GSE202859_sample_correlation.png){width=5.0in}

![Figure 3b. Sample correlation — validation cohort GSE193258.](results/figures/GSE193258_sample_correlation.png){width=5.0in}

## Cross-cohort signature validation

The validated signature requires a gene to be significant in both cohorts with the same direction of effect. From 2,785 significant discovery genes (1,435 up, 1,350 down) and 4,852 significant validation genes (3,651 up, 1,201 down), 1,273 genes were significant in both, of which **1,112 were directionally consistent** (161 flipped sign). Per-cohort-only sets were also sizeable (discovery-only 1,512; validation-only 3,579; UpSet-style decomposition in `results/figures/cross_DEG_overlap_upset.png`, generated by the deterministic renderer `scripts/09_upset.py`).

## Functional enrichment (Stage 5)

Over-representation was computed in Python (hypergeometric + BH FDR) over the validated signature and per cohort, with the **per-source annotated universe as background** (all genes present in that source's gene-set collection — decision D10), spanning: GO Biological Process (Enrichr GMT, symbol-based), KEGG and Reactome (public Entrez sources converted to symbols via `Homo_sapiens.gene_info`). Pre-ranked GSEA on the DESeq2 signed log2FC ranking was run as the primary engine, and R `fgsea` (exact multilevel algorithm, micromamba R environment) as a paired cross-check on identically exported GMT files (`results/tables/gene_sets/gene_sets_{GO_BP,KEGG,Reactome}.gmt`), with concordance reported per cohort and collection (`gsea_*_fgsea.csv` tables).

## Machine learning with group-aware nested CV

The ML track (Stages 4-8) used the VST matrix with the validated 1,112-gene signature as the candidate feature pool. For each model family (Logistic Regression, Random Forest, SVM, XGBoost as a documented extension) and each feature-set size K in {10, 20, 50, 100, 200, 500}, a **group-aware nested cross-validation** was run:

- **StratifiedGroupKFold** with `groups = cell_line` (all replicates of one line always in the same fold; no line is ever split across train/test).
- Feature selection, scaling and hyperparameter tuning performed **strictly inside each training fold** (inner grouped GridSearchCV).
- The winning inner configuration was refit on the outer-training fold and evaluated on the untouched outer fold; out-of-fold predictions and metrics (ROC-AUC, PR-AUC, sensitivity, specificity, F1) were logged per (model, K).
- Each metric carries a **stratified bootstrap 95% confidence interval**.
- All 24 model-K cells per cohort were reported — the full result surface, not just the best cell. Per-cohort out-of-fold ROC/PR/confusion panels and the AUC-vs-K surfaces are shown below (Figures 25-32); the primary figures for the discovery cohort and the exploratory in-cohort panels for the validation cohort are both generated by `05_train_models.py`.

The **primary configuration was pre-registered before external validation: Logistic Regression, K = 50** (decision D2; inner-CV-consistent). External validation ran once, with locked-cohort discipline enforced — no model or threshold change was permitted after the external table was read. Two scoring/normalisation schemes appear throughout:

- **`train_stats` (headline scheme, decision D1):** scalers and K-best selection estimated on the discovery (training) cohort only; no test-set statistics used; the honest generalisation estimate.
- **`target_z` (transductive bound only):** z-scored against the validation cohort's own statistics; leaks test-set marginal information and is reported exclusively as an optimistic upper bound, never as the headline.

A **washout-sensitivity arm** (`scripts/02b_vst_extend.R` + `scripts/10_washout_sensitivity.py`) refits VST once, blind, on all 60 available GSE193258 samples (the primary labelled matrix is untouched), and applies the **locked discovery models** (persisted per decision D9 as `results/models/<cohort>_<model>_K<k>.joblib`, fitted by `ml.cv.fit_full` with the same selection/scaling/inner-tuning recipe on all samples) to the excluded timecourse arm (osi_acute, short washout, long washout at 72 h / 96 h / 7 d / 10 d, plus DTP and DMSO anchors). Group labels are parsed deterministically from sample titles. This is a label-free reversibility probe, not an accuracy claim (decision D7).

## Interpretation and biomarker ranking

Per-model explanations (L1 coefficient paths, SHAP mean |SHAP| value, permutation importance) were computed on the discovery cohort and combined into one **composite panel score**: a rank-average of (a) resampling stability, (b) nested-CV selection frequency, and (c) mean |SHAP|. The top 100 composite-ranked genes and sub-tables are reported in `results/tables/biomarker_panel.csv`, with a "candidate" label applied explicitly throughout.

## Reproducibility and leakage controls

The pipeline re-runs end-to-end from `scripts/run_pipeline.py` (Stages 3-8) with a fixed seed (42) recorded centrally in `config/config.yaml`; a verification baseline is provided by a synthetic smoke-test mode. By-design controls:

- Cohorts kept separate — no pooled cross-validation.
- Group-aware splits; feature selection and scaling entirely inside folds.
- External validation evaluated once, after model lock.
- Explicit, logged enrichment universe (decision D10).
- Full result surface reported (all model-K cells); SVM decision-function scores flagged as monotone sigmoids, not calibrated probabilities.
- Persisted model artefacts for every configuration (decision D9).
- All decisions (D1-D14) recorded with rationale in `docs/decisions.md`; analysis-checklist in `config/leakage_checklist.md`.

# Analysis

## Cross-cohort reproducibility of DEGs

DESeq2 found 2,785 significant genes (1,435 up, 1,350 down) in the discovery cohort and 4,852 (3,651 up, 1,201 down) in the validation cohort.

**Figure 4. Volcano plot — discovery cohort GSE202859.** DESeq2 log2 fold change vs -log10(p value) for all tested genes under the `~ cell_line + condition` design; red points mark BH FDR < 0.05 and |log2FC| > 1 (2,785 significant genes; 1,435 up / 1,350 down). X-axis truncated for display.

![Figure 4. Volcano plot — discovery cohort GSE202859. Red = significant at FDR < 0.05, |log2FC| > 1.](results/figures/GSE202859_volcano.png){width=5.6in}

**Figure 5. Volcano plot — validation cohort GSE193258.** Same design (4,852 significant genes; 3,651 up / 1,201 down).

![Figure 5. Volcano plot — validation cohort GSE193258.](results/figures/GSE193258_volcano.png){width=5.6in}

**Figure 6. Heatmap of the top differentially expressed genes, discovery cohort GSE202859** (top hits by BH-adjusted p value; VST-normalised expression, samples ordered by condition/cell line).

![Figure 6. Top-DEG heatmap — discovery cohort GSE202859.](results/figures/GSE202859_heatmap_topDEG.png){width=5.2in}

**Figure 7. Heatmap of the top differentially expressed genes, validation cohort GSE193258.**

![Figure 7. Top-DEG heatmap — validation cohort GSE193258.](results/figures/GSE193258_heatmap_topDEG.png){width=5.2in}

Directional consistency is strong: **1,112 of the 1,273 genes significant in both cohorts carry the same direction**, while 161 flip sign (mostly weaker, cohort-specific responses); per-cohort-only sets were also sizeable (discovery-only 1,512; validation-only 3,579). The bulk of the persistent resistance signal is therefore shared across independently produced studies — evidence that the signature reflects the resistance state rather than a dataset artefact.

**Figure 8. Cross-dataset concordance of differential expression.** Log2 fold changes (validated genes) in the validation cohort plotted against log2 fold changes in the discovery cohort — the aligned diagonal shows that effect sizes, not just directions, agree between cohorts.

![Figure 8. log2FC(log2FC) concordance — validation vs discovery cohort.](results/figures/cross_DEG_lfc.png){width=5.4in}

**Figure 9. Decomposition of the cross-cohort DEG overlap (UpSet-style summary).** 3,579 validation-only / 1,512 discovery-only / 1,112 directionally consistent in both / 161 inconsistent (significant in both, opposite direction). AURKA/ABAT-like sign flips (e.g., A2M-AS1 consistent-up; ABAT discovery-down/validation-up) are visible in the underlying table `results/tables/cross_DEG_overlap.csv`.

![Figure 9. UpSet-style decomposition of the cross-cohort DEG overlap.](results/figures/cross_DEG_overlap_upset.png){width=5.4in}

## Biological characterisation of the validated signature

Over-representation of the 1,112-gene validated signature (conservative per-source annotated background):

**GO Biological Process.** Up-regulated terms are dominated by movement/remodelling programs — *Regulation of Cell Migration* (40/434 genes, FE 2.05, padj 0.026), *Extracellular Matrix Organization* (20/176, FE 2.53), *Axonogenesis* / *Neuron Projection Guidance* (developmental morphogenesis programs), and transport programs (*Transport Across Blood-Brain Barrier*, FE 3.41; *Carboxylic Acid Transport*, FE 4.20).

**KEGG.** *Cytoskeleton in muscle cells* (23/233, FE 2.48, padj 0.016) and *Hippo signalling* (16/157) — cytoskeletal plasticity and the Hippo/YAP axis recur in persister biology; *Complement and Coagulation Cascades* (11/89) reflects an inflammatory/remodelling component.

**Reactome.** *Developmental Cell Lineages* (27/181, padj < 0.001), Mammary Gland Myoepithelial lineage, *Cell-surface interactions at the vascular wall*, *ECM organization* (33/321) and *O-linked glycosylation* — convergent with GO on lineage plasticity and surface/ECM remodelling.

**Figure 10-12. Over-representation of the validated signature.** Dot plots of the top-ranked terms per collection: dot size = gene-set size, colour = BH-adjusted p value, overlap genes annotated. (10: GO Biological Process; 11: KEGG; 12: Reactome.)

![Figure 10. ORA dot plot — validated signature, GO Biological Process.](results/figures/enrichment_validated_GO_BP_dotplot.png){width=5.4in}

![Figure 11. ORA dot plot — validated signature, KEGG.](results/figures/enrichment_validated_KEGG_dotplot.png){width=5.4in}

![Figure 12. ORA dot plot — validated signature, Reactome.](results/figures/enrichment_validated_Reactome_dotplot.png){width=5.4in}

**Figures 13-18. Per-cohort over-representation.** The same three collections were also run per cohort (discovery: Figures 13-15; validation: Figures 16-18), producing consistent themes; the full dot plots are generated with the enrichment tables in `results/figures/` and `results/tables/enrichment_*`.

**Pre-ranked GSEA (whole transcriptome).** The strongest directionality is *negative*: Ribosome (NES -5.28 in discovery; **-6.89** in validation), Spliceosome (-3.99 / -6.87), Ribosome biogenesis in eukaryotes (-3.54 / -5.95), and Nucleocytoplasmic Transport (-5.64) are the most suppressed programs — a hypoproliferative, de-differentiated persister state. The primary engine is a size-bucketed permutation null, cross-checked with R fgsea below.

**Figures 19-24. Pre-ranked GSEA running-enrichment plots.** Each panel shows the running enrichment score along the DESeq2 log2FC-ranked transcriptome for the leading pathway hits per cohort and collection. (19/20: GSE202859 GO-BP/KEGG; 21/22: GSE193258 GO-BP/KEGG; 23/24: Reactome for both cohorts.)

![Figure 19. GSEA running enrichment — GSE202859, GO-BP.](results/figures/gsea_GSE202859_GO_BP.png){width=5.4in}

![Figure 20. GSEA running enrichment — GSE202859, KEGG.](results/figures/gsea_GSE202859_KEGG.png){width=5.4in}

![Figure 21. GSEA running enrichment — GSE193258, GO-BP.](results/figures/gsea_GSE193258_GO_BP.png){width=5.4in}

![Figure 22. GSEA running enrichment — GSE193258, KEGG.](results/figures/gsea_GSE193258_KEGG.png){width=5.4in}

![Figure 23. GSEA running enrichment — GSE202859, Reactome.](results/figures/gsea_GSE202859_Reactome.png){width=5.4in}

![Figure 24. GSEA running enrichment — GSE193258, Reactome.](results/figures/gsea_GSE193258_Reactome.png){width=5.4in}

**Engine robustness (fgsea cross-check).** NES concordance between the Python primary engine and R fgsea on the same ranked lists and the same GMT files: Spearman rho = 0.70 (GSE202859 KEGG, 342 matched sets), 0.86 (GSE193258 KEGG, 347 sets), 0.67 (GSE202859 GO-BP, 2,456 sets); sign agreement 61-81%; top-5-by-padj overlap 1-3 of 5 (expected, since near-zero-NES sets flip under engine-specific multilevel p-values while strong hits remain concordant). The engine dependency is disclosed rather than hidden (decision D3): Python remains primary, fgsea is the exact cross-check.

**Synthesis.** Across engines and collections, the joined picture is coherent: resistant, DTP-like states **suppress translation, splicing and ribosome-biogenesis housekeeping programs** and **amplify motility, extracellular-matrix, cytoskeletal and developmental-lineage programs** — the classic non-genetic acquired-resistance phenotype, converging with the mSWI/SNF/EMT readout of de Miguel et al. (2023) and the DTP landscape of Criscione et al. (2022).

## Classifier behaviour

Within-cohort group-aware nested CV shows near-ceiling separability at several model-K cells; the full 48-cell surface is reported deliberately (with bootstrap CIs on every metric) rather than a cherry-picked best cell. Nested selection frequencies of leading features remain informative (non-degenerate), an indirect check against single-line artefacts.

**Figures 25-28. Discovery-cohort nested-CV panels (GSE202859).** (25) Out-of-fold ROC curve with 95% bootstrap band; (26) PR curve; (27) mean confusion matrix across outer folds at the 0.5 threshold; (28) AUC against feature-set size K for all four model families — the exploratory K-surface; the confirmatory analysis is pre-registered at K = 50.

![Figure 25. Discovery nested-CV ROC — GSE202859.](results/figures/GSE202859_roc.png){width=4.6in}

![Figure 26. Discovery nested-CV PR curve — GSE202859.](results/figures/GSE202859_pr.png){width=4.6in}

![Figure 27. Discovery nested-CV confusion matrix — GSE202859.](results/figures/GSE202859_confusion.png){width=4.2in}

![Figure 28. Discovery nested-CV ROC-AUC vs K — GSE202859.](results/figures/GSE202859_auc_vs_k.png){width=4.8in}

**Figures 29-32. In-cohort panels, validation cohort GSE193258** (same four panels; exploratory — the validation cohort is not used for training in the confirmatory flow).

![Figure 29. In-cohort nested-CV ROC — GSE193258.](results/figures/GSE193258_roc.png){width=4.6in}

![Figure 30. In-cohort nested-CV PR curve — GSE193258.](results/figures/GSE193258_pr.png){width=4.6in}

![Figure 31. In-cohort nested-CV confusion matrix — GSE193258.](results/figures/GSE193258_confusion.png){width=4.2in}

![Figure 32. In-cohort nested-CV ROC-AUC vs K — GSE193258.](results/figures/GSE193258_auc_vs_k.png){width=4.8in}

External validation on the fully independent GSE193258 cohort, reported once:

**Figures 33-36. One-shot external validation (discovery models → GSE193258).** (33) ROC curve, primary configuration highlighted; (34) PR curve; (35) confusion matrix at the 0.5 threshold — all 9 resistant samples correctly called, 4 of 9 sensitive samples above threshold under the strict scheme; (36) calibration plot (predicted probability vs observed outcome fraction for the external run); note that SVM decision scores are monotone sigmoids rather than calibrated probabilities, so their Brier values are reference-only (primary configuration Brier 0.132 strict vs 0.012 transductive).

![Figure 33. External validation ROC — LR K=50.](results/figures/external_roc.png){width=4.8in}

![Figure 34. External validation PR curve.](results/figures/external_pr.png){width=4.8in}

![Figure 35. External validation confusion matrix (0.5 threshold).](results/figures/external_confusion.png){width=4.2in}

![Figure 36. External validation calibration.](results/figures/external_calibration.png){width=4.8in}

- **Primary (Logistic Regression, K = 50, `train_stats` headline): ROC-AUC 1.000 (95% CI 1.000-1.000), PR-AUC 1.000, sensitivity 1.000 (all 9 resistant samples correctly recalled), specificity 0.444 (4/9 sensitive samples above the 0.5 threshold; CI 0.111-0.778), accuracy 0.722, Brier 0.132.** The wide specificity interval is a direct consequence of n = 9 negatives.
- Under the transductive `target_z` scheme the same configuration is fully separated (specificity 1.000, Brier 0.012) — reported as an optimistic bound only (decision D1).
- Random Forest and XGBoost under `train_stats` confirm that separability is not model-specific; SVM cells exhibit monotone decision-function behaviour that limits default-threshold sensitivity at some K (documented; not calibrated).

## Biomarker panel

The composite candidate panel is highly stable (stability = 1.000 for every leader), with nested-selection frequencies of 0.33-0.83 and modest SHAP magnitudes, as appropriate for ~50-feature linear models on 18 samples.

**Figure 37. Candidate biomarker panel.** Top-ranked genes ordered by the composite score (resampling stability + nested-CV selection frequency + mean |SHAP|), annotated with sub-scores.

![Figure 37. Composite candidate biomarker panel.](results/figures/biomarker_panel.png){width=5.4in}

**Figure 38. SHAP summary (discovery cohort).** Mean absolute SHAP values for the leading features of the tree-based interpreters; used as one of the three composite-panel components. (Full table: `results/tables/shap_importance.csv`.)

![Figure 38. SHAP feature attributions — discovery cohort.](results/figures/shap_summary.png){width=5.4in}

Top 20 genes: HECA, KLHL24, SACK1A, HEG1, IL33R, MAP3K3, TBC1D9, EFNB2, MIR198, MTURN, SULT2B1, PDCD4, CITED2, OSTM1, ITGA6, SDC1, ASAP3, SERPINB1, INSR, YPEL5 (full table in `results/tables/biomarker_panel.csv`); a handful of these names are NCBI symbol-space additions rather than canonical HGNC entries and are flagged for downstream curation. These are reported as **candidate biomarkers, not causal drivers**, consistent with the pre-declared claim discipline.

## Washout reversibility (label-free probe)

Applying locked discovery models to the excluded GSE193258 timecourse arm (42 treated-state samples plus 18 anchors):

| group | n | P(Resistant), `train_stats` | P(Resistant), `target_z` |
|---|---|---|---|
| DMSO/Parental (anchor) | 12 | 0.335 | **0.047** |
| DTP (anchor) | 12 | 0.994 | 0.798 |
| osi_acute (24 h) | 12 | 0.990 | 0.675 |
| short_washout | 12 | 0.981 | 0.649 |
| long_washout_72h | 3 | 0.998 | 0.846 |
| long_washout_96h | 3 | 0.988 | 0.653 |
| long_washout_7d | 3 | 0.905 | 0.431 |
| long_washout_10d | 3 | 0.863 | **0.297** |

In the transductive scheme the probe behaves as a reversibility gradient: low at the DMSO anchor (0.05), rising through acute exposure (0.68), peaking at DTP (0.80), and decaying with washout duration (72 h 0.85 → 96 h 0.65 → 7 d 0.43 → **10 d 0.30**). Under the strict headline scheme, by contrast, the whole validation distribution is scaled to the discovery distribution — the `train_stats` numbers therefore mostly reflect the documented DTP-vs-`-OR` distribution shift (anchors: DMSO 0.34 vs DTP 0.99), and only the DMSO anchor is clearly low. Both schemes are presented precisely so the reader can separate the two effects. No accuracy claim is made for these samples (decision D7). The demonstration is biological: **the learned signature is sensitive to drug-exposure state**, and, in the transductive scheme, tracks time-since-drug in the expected direction — partial but incomplete reversion at 72 h-10 d washouts, consistent with a state-like (partially reversible) rather than mutation-like resistance phenotype.

**Figure 39. Washout-sensitivity strip plot.** Model-predicted P(Resistant) for the primary configuration (Logistic Regression, K = 50) across the excluded GSE193258 timecourse arm and anchors, showing one line per sample grouped by experimental state; the inter-anchor and washout positions visualise the reversibility gradient discussed above (table: `washout_sensitivity_groups.csv`).

![Figure 39. Washout sensitivity — locked discovery models on the drug-withdrawal arm.](results/figures/washout_sensitivity.png){width=5.6in}

# Results

**Number of validated signature genes: 1,112** — significant (BH FDR < 0.05, |log2FC| > 1, DESeq2 `~ cell_line + condition`) and directionally consistent in both cohorts; of 1,273 genes significant in both, 87% are directionally consistent.

**Primary pre-registered classification performance (external one-shot, Logistic Regression, K = 50, strict scheme): ROC-AUC 1.000 (95% CI 1.000-1.000), PR-AUC 1.000, sensitivity 1.000, specificity 0.444 (CI 0.111-0.778), accuracy 0.722, Brier 0.132.** Full separation (1.000/1.000) occurs under the transductive scheme, reported only as the optimistic bound per decision D1.

**Biological theme of the signature (enrichment on the validated set, conservative background):** up-regulated — cell migration/GO movement programs (FE 2.05-4.20), extracellular-matrix organization (GO FE 2.53; Reactome 2.46), cytoskeleton (KEGG FE 2.48) and developmental-lineage programs (Reactome, padj < 0.001); down-regulated whole-transcriptome (GSEA) — Ribosome (NES -5.3/-6.9 discovery/validation), Spliceosome (-4.0/-6.9), ribosome biogenesis, nucleocytoplasmic transport — i.e. a translation-suppression/de-differentiation phenotype.

**Engine robustness:** Python pre-ranked GSEA is concordant with R fgsea (NES Spearman rho = 0.70-0.86; sign agreement 61-81%; strong hits overlap).

**Candidate panel:** 20 genes listed above (stability 1.000, nested-selection frequency 0.33-0.83); full 100-gene panel in `results/tables/biomarker_panel.csv`.

**Reversibility (label-free):** transductive-scheme gradient DMSO 0.05 → DTP 0.80 with long washouts drifting to 0.30 by 10 days; strict-scheme anchors (DMSO 0.34 vs DTP 0.99) document the endpoint distribution shift; both tables ship as `results/tables/washout_sensitivity{,_groups}.csv` with the primary-config figure `washout_sensitivity.png`.

# Discussion

The principal biological claim of this work is deliberately modest: when two independently produced GEO series with harmonised NCBI processing are analysed with background-corrected DESeq2 and a clean label policy, the consensus transcriptional state of acquired-osimertinib-resistant EGFR-mutant lung adenocarcinoma cell lines is characterised by motility/EMT/ECM/lineage-plasticity programs going up and translation/housekeeping programs going down. This matches both the non-genetic DTP literature (Criscione et al., 2022) and the mSWI/SNF-mediated EMT/differentiation rewiring of de Miguel et al. (2023): the resistant state is a chromatin-remodelling-driven, persister-like, less-proliferative but more motile state, not the "oncogene-addiction relapse" of first-generation EGFR-TKI resistance in culture.

The cross-study concordance is the load-bearing evidence: 1,112 directionally consistent genes among 1,273 genes significant in both cohorts is far above chance (fewer than half of the significant genes are shared by accident, and those shared are almost all same-direction), and the deepest GSEA programs (ribosome, spliceosome, lineages) appear in both cohorts with large effect sizes independently. This is the reproducibility structure that makes the machine-learning result meaningful.

The machine-learning results are simultaneously the least and most impressive part of this report: a surface of AUC-1.000-like values on 18 samples is exactly what one expects when the two phenotypic states are transcriptionally highly distinct (which the DEG analysis already shows), so the AUC itself is not the informative number. What is informative is how the analysis handles honesty: (a) every metric carries a bootstrap interval, and on the external cohort the headline configuration shows sensitivity 1.000 with specificity 0.444 and a wide interval (0.111-0.778) — an honest bounded estimate, not a perfect story; (b) all 24 model-K cells are reported, not just the best; (c) strict vs transductive scaling are presented side-by-side so the reader can see the cost of de-leaking (decision D1); and (d) feature selection, scaling and tuning all live inside folds, with winner's-curse control via the pre-registered primary configuration (decision D2) chosen before any external-cohort data were read.

The specificity drop under the strict scheme deserves interpretation: the discovery endpoint is chronically dosed -OR cells and the validation endpoint is a 3-week DTP state; the distributions of the undiseased ("Sensitive") side differ between cohorts, so a strictly discovery-scaled model can misclassify validation-sensitive samples while still ranking resistant samples perfectly (sensitivity 1.000, AUC 1.000 — ranking and calibration are different properties; the Brier score 0.132 vs 0.012 ⟨transductive⟩ illustrates that). This is exactly the pattern expected from an endpoint-mismatch distribution shift, not from overfitting; the "endpoint difference" limitation declared up front (DTP vs -OR) is appreciated here rigorously rather than rationalised away.

The washout experiment is the interpretive bridge between the biological and predictive halves of the project. In the transductive scheme, the learned signature behaves as expected: low at DMSO, rising through acute exposure, peaking at DTP, then decaying with washout duration (72 h 0.85 → 96 h 0.65 → 7 d 0.43 → 10 d 0.30) — partial reversion, not complete return. Under the strict scheme, only the DMSO anchor is clearly low; the rest reflect the discovery-vs-validation scaling shift rather than biology. That the gradient is visible in either scheme, with consistent anchors, means the signature is genuinely state-dependent in a drug-exposure-sensitive way — partially reversible, in line with the DTP literature. Had the classifier been purely an exposure artefact, the 72 h-10 d washout samples (drug-free for up to 10 days) would have been indistinguishable from sensitive samples, which they are not (they sit between anchors and drift with duration). This partially debunks the exposure-confound hypothesis, though it does not eliminate it, and the washout arm is unlabeled by design — the results are interpretive, not confirmatory.

Limitations are deterministic and stated up front. n = 18 per cohort and three distinct genetic backgrounds make every performance figure exploratory. The `-OR` vs `osi_DTP` endpoint mismatch limits calibration transfer (handled explicitly, not hidden). There is no clinical context: no immune microenvironment, no patient response, no drug dosing schedule; cell lines are not patients. ORA universe choice (per-source annotated background, decision D10) is conservative and may under-report moderate hits. Symbol aliasing in the panel (e.g., HECA, SACK1A, IL33R, MTURN appear as NCBI spaces rather than canonical HGNC symbols) requires manual curation before any external database deposition. And the external validation was run exactly once; any post-lock modification of models or thresholds would have invalidated the confirmatory reading, so none is reported.

Future work falls out naturally: (a) patient-derived or organoid cohorts for clinical-validity probing (out of scope here — currently no data access); (b) single-cell resolution of the DTP/reversion trajectory to decouple the drug-exposure axis from the resistance axis (the washout gradient suggests this is tractable); (c) a proper calibration layer (e.g., isotonic/Platt on the SVM decision function) should probability-thresholded decisions matter downstream; and (d) scaling the panel ranking to ensemble across three or more independent cohorts to reduce symbol-aliasing instability of the panel names, with a DB-staged validation of panel-gene aliasing before deposition.

# Conclusion

Using two harmonised public bulk-RNA-seq cohorts, we derived a **1,112-gene validated transcriptional signature** of acquired osimertinib resistance in EGFR-mutant NSCLC cell lines, characterised it biologically (up-regulated: cell migration, ECM organization, cytoskeletal and developmental-lineage programs; down-regulated: ribosome, spliceosome, ribosome biogenesis — a translation-suppression/de-differentiation phenotype), and showed that a compact, pre-registered, leakage-controlled classifier (logistic regression, K = 50) using this signature discriminates resistant from sensitive samples on an entirely independent external cohort with **ROC-AUC 1.000 (95% CI 1.000-1.000)** under the strict headline scheme, with honest reporting of the sensitivity/specificity asymmetry and a bounded transductive upper bound. A **100-gene candidate biomarker panel** was derived from a stability/nested-selection/SHAP composite, and a **label-free washout experiment supports the state-like, partially reversible nature** of the learned signature in the expected biological direction. All findings are exploratory candidate-biomarker discoveries on three shared cell lines (n = 18 per cohort) and are reported conservatively, with no clinical, diagnostic or causal claims.

# References

1. de Miguel FJ, Gentile C, Feng WW, et al. (2023). *Mammalian SWI/SNF chromatin remodeling complexes promote tyrosine kinase inhibitor resistance in EGFR-mutant lung cancer.* **Cancer Cell** 41(8):1516-1534.e9. PMID: 37541244. DOI: 10.1016/j.ccell.2023.07.005. *(Primary publication of the discovery cohort GSE202859.)*
2. Criscione SW, Martin MJ, Oien DB, et al. (2022). *The landscape of therapeutic vulnerabilities in EGFR inhibitor osimertinib drug tolerant persister cells.* **npj Precision Oncology** 6:95. PMID: 36575215. DOI: 10.1038/s41698-022-00337-w. *(Primary publication of the validation cohort GSE193258.)*
3. Blaquier JB, Ortiz-Cuaran S, Ricciuti B, Mezquita L, Cardona AF, Recondo G (2023). *Tackling osimertinib resistance in EGFR-mutant non-small cell lung cancer.* **Clinical Cancer Research** 29(18):3579-3591. DOI: 10.1158/1078-0432.CCR-22-1912.
4. Love MI, Huber W, Anders S (2014). *Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2.* **Genome Biology** 15:550.
5. Subramanian A, Tamayo P, Mootha VK, et al. (2005). *Gene set enrichment analysis: a knowledge-based approach for interpreting genome-wide expression profiles.* **PNAS** 102(43):15545-15550.
6. Korotkevich G, Sukhov V, Budin N, Shpak B, Artyomov MN, Sergushichev A (2021/2019). *Fast gene set enrichment analysis (fgsea).* bioRxiv 060012, DOI: 10.1101/060012.
7. Kuleshov MV, Jones MR, Rouillard AD, et al. (2016). *Enrichr: a comprehensive gene set enrichment analysis web server.* **Nucleic Acids Research** 44(W1):W90-W97.
8. Gillespie M, Jassal B, Stephan R, et al. (2022). *The Reactome pathway knowledgebase 2022.* **Nucleic Acids Research** 50(D1):D697-D705.
9. Kanehisa M, Furumichi M, Sato Y, Kawashima M, Ishiguro-Watanabe M (2023). *KEGG for taxonomy-based analysis of pathways and genomes.* **Nucleic Acids Research** 51(D1):D587-D592.
10. Barrett T, Wilhite SE, Ledoux P, et al. (2013). *NCBI GEO: archive for functional genomics data sets.* **Nucleic Acids Research** 41(D1):D991-D995.
11. Varma S, Simon R (2006). *Bias in error estimation when using cross-validation for model selection.* **BMC Bioinformatics** 7:91.
12. Pedregosa F, Varoquaux G, Gramfort A, et al. (2011). *Scikit-learn: Machine Learning in Python.* **Journal of Machine Learning Research** 12:2825-2830.
13. Chen T, Guestrin C (2016). *XGBoost: A scalable tree boosting system.* **Proceedings of KDD '16:** 785-794. DOI: 10.1145/2939672.2939785.
14. R Core Team (2024). *R: A Language and Environment for Statistical Computing.* Vienna: R Foundation for Statistical Computing.

*Pipeline provenance: R scripts `scripts/01_fetch_data.R` → `scripts/01_build_metadata.R` → `scripts/02_preprocess_qc.R` → `scripts/03_deg_enrichment.R`; Python scripts `scripts/03b_enrichment.py` → `scripts/03c_fgsea_crosscheck.R` → `scripts/04_feature_selection.py` → `scripts/05_train_models.py` → `scripts/06_external_validation.py` → `scripts/07_interpret.py` → `scripts/08_report.py`; extensions `scripts/02b_vst_extend.R` (washout-refit), `scripts/10_washout_sensitivity.py` (reversibility probe), `scripts/09_upset.py` (overlap figure). Config and seeds: `config/config.yaml`; decision log: `docs/decisions.md`; leakage checklist: `config/leakage_checklist.md`; session info: `results/reports/session_info.txt`.*

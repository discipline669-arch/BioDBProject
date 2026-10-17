# Project Proposal

## 1. Project Title

**Transcriptomic Profiling of Drug-Resistant Cancer Cells**

## 2. Team

**Team Size:** 3 Members

### Team Responsibilities

| Member | Workstream | Primary Responsibility |
|---|---|---|
| **Member 1** | Data Acquisition, Preprocessing & QC | Identify suitable GEO datasets, prepare count matrices and metadata, perform preprocessing and quality control |
| **Member 2** | Differential Expression, Cross-Dataset Validation & Pathways | Perform DESeq2 analysis, identify validated DEGs, and conduct GO/KEGG pathway analysis |
| **Member 3** | Machine Learning & Biomarker Discovery | Build classification models, evaluate performance, and identify predictive biomarker candidates |

---

## 3. Project Goal

The project aims to identify **differentially expressed genes (DEGs)** and affected biological pathways associated with cancer drug resistance by comparing drug-resistant and drug-sensitive cancer cells using publicly available bulk RNA-seq data. The study will further validate candidate genes across independent datasets and use machine learning to identify robust transcriptomic biomarkers capable of distinguishing resistant from sensitive samples.

---

## 4. Data Collection Strategy

Two independent **human bulk RNA-seq datasets** will be selected from the NCBI Gene Expression Omnibus (GEO).

### Dataset Selection Criteria

The preferred datasets should have:

- Bulk RNA-seq data
- Human cancer samples/cell lines
- A clear **drug-resistant vs drug-sensitive** comparison
- At least **3 biological replicates per condition**
- Preferably **5–10 biological replicates per condition**
- Gene-level raw count matrices or suitable count data
- Clear sample metadata
- Minimal confounding or batch effects
- Preferably the **same cancer type and drug** across the two datasets

### Recommended Data Volume

The target is:

- **2 independent GEO datasets**
- Ideally **5–10 sensitive + 5–10 resistant samples per dataset**
- Minimum acceptable: **3 sensitive + 3 resistant samples per dataset**
- Preferred overall target: approximately **12–40 total biological samples**

The number of biological samples is more important for statistical and machine-learning reliability than simply increasing the number of genes.

---

## 5. Methodology

Two independent bulk RNA-seq datasets comparing drug-resistant and drug-sensitive cancer samples will be retrieved from the NCBI GEO database. Raw gene count matrices and sample metadata will be preprocessed and analyzed independently using the **DESeq2** package in R, including low-count filtering, normalization, variance-stabilizing transformation, and quality-control analysis such as PCA. Differentially expressed genes will be identified using predefined statistical criteria such as **adjusted p-value (FDR) < 0.05** and **|log2 fold change| > 1**. The DEGs obtained from both datasets will then be compared to identify genes showing consistent differential regulation across independent datasets. Functional enrichment analyses, including **Gene Ontology (GO)** and **KEGG pathway analysis**, will be performed to investigate biological processes and signaling pathways associated with drug resistance. Finally, validated DEGs will be used as candidate features for supervised machine-learning models, including **Logistic Regression, Random Forest, and Support Vector Machine (SVM)**, with appropriate cross-validation and leakage prevention. Model performance will be assessed using **Accuracy, Precision, Recall, F1-score, ROC-AUC, and confusion matrices**, and feature importance will be used to identify a smaller panel of candidate transcriptomic biomarkers.

---

## 6. Cross-Dataset Validation Strategy

The project will use two independent datasets to reduce dataset-specific bias.

The workflow will be:

```text
Dataset 1 → DESeq2 → Significant DEGs ─┐
                                       ├→ Common & Consistently Regulated DEGs
Dataset 2 → DESeq2 → Significant DEGs ─┘
                                                    ↓
                                           Candidate Biomarkers
```

Genes will be considered higher-confidence candidates when they:

- Are significantly differentially expressed in both datasets
- Show a consistent direction of regulation
- Remain biologically relevant to drug resistance

Where possible, the second dataset will also serve as an **independent external validation set** for the final biomarker panel.

---

## 7. Machine Learning-Based Biomarker Discovery

The cross-dataset validated genes will be used as candidate ML features.

### Models

- Logistic Regression
- Random Forest
- Support Vector Machine (SVM)

### Evaluation Metrics

- Accuracy
- Precision
- Recall
- F1-score
- ROC-AUC
- Confusion Matrix

### Biomarker Selection

Feature importance and model coefficients will be used to rank candidate genes. A smaller set of highly predictive genes will then be investigated as a potential **drug-resistance biomarker panel**.

Because GEO datasets can have relatively small sample sizes, the ML component will be treated as **exploratory biomarker discovery and validation**, rather than clinical diagnostic validation.

---

## 8. Functional and Pathway Analysis

The validated DEGs will be analyzed using:

### Gene Ontology (GO)

Focus primarily on **Biological Process (BP)** terms related to mechanisms such as:

- Apoptosis
- DNA damage and repair
- Cell-cycle regulation
- Drug response
- Oxidative stress
- Cell proliferation

### KEGG

Identify enriched signaling and metabolic pathways potentially associated with resistance, such as:

- PI3K-Akt signaling
- MAPK signaling
- p53 signaling
- Cell cycle
- ABC transporter-related pathways

The final interpretation will be based on the actual enrichment results rather than assuming that specific pathways must appear.

---

## 9. Visualization

The project will generate publication-quality visualizations including:

- PCA plots
- Sample clustering plots
- Volcano plots
- DEG heatmaps
- Venn diagram or UpSet plot for cross-dataset overlap
- GO enrichment plots
- KEGG pathway plots
- ROC curves
- Confusion matrices
- Machine-learning feature-importance plots

---

## 10. Expected Tangible Outputs

| Output | Description |
|---|---|
| **Two GEO datasets** | Independent resistant vs sensitive bulk RNA-seq datasets |
| **Clean count matrices** | Preprocessed gene × sample expression matrices |
| **QC results** | PCA and sample-quality assessment |
| **DEG tables** | Significant upregulated/downregulated genes for each dataset |
| **Validated DEG list** | Genes consistently regulated across datasets |
| **GO results** | Enriched biological processes |
| **KEGG results** | Enriched pathways |
| **ML models** | Logistic Regression, Random Forest and SVM |
| **Performance metrics** | Accuracy, Precision, Recall, F1, ROC-AUC |
| **Biomarker panel** | Top predictive and biologically relevant candidate genes |
| **Publication-quality figures** | PCA, volcano, heatmap, enrichment, ROC and feature-importance plots |
| **Reproducible report** | RMarkdown/Quarto report containing methods, results and interpretation |
| **Code repository** | Organized and reproducible project repository |

---

## 11. Novelty

- **Integrates multiple independent transcriptomic datasets** to identify reproducible biomarkers associated with cancer drug resistance.
- Performs **cross-dataset validation**, reducing dataset-specific bias and increasing confidence in candidate DEGs.
- Combines **statistical differential expression analysis with supervised machine learning** to identify biomarkers that are both biologically significant and predictive.
- Evaluates multiple classification algorithms to determine which approach best distinguishes drug-resistant from drug-sensitive samples.
- Uses feature importance to prioritize a **smaller candidate biomarker panel** from the larger set of validated DEGs.
- Incorporates independent dataset validation to assess whether discovered biomarkers generalize beyond the dataset used for discovery.
- Provides a **fully reproducible end-to-end bioinformatics and machine-learning pipeline** that can be adapted to other cancer types, drugs, and transcriptomic datasets.

---

## 12. One-Month Execution Plan

**Project Period: August 16 – September 15**

| Dates | Member 1 — Data & QC | Member 2 — DEGs & Biology | Member 3 — ML & Biomarkers |
|---|---|---|---|
| **Aug 16–18** | Search GEO and shortlist 2 suitable datasets | Study datasets and biological background; define comparison | Research ML approaches and evaluation strategy |
| **Aug 19–22** | Download data; construct metadata/count matrices; filtering; normalization; initial PCA | Set up DESeq2; preliminary Dataset 1 analysis; define statistical criteria | Build ML pipeline; define preprocessing and evaluation |
| **Aug 23–25** | Complete QC for both datasets | DESeq2 analysis of Dataset 1; DEG table and volcano plot | Build and test ML models |
| **Aug 26–29** | Investigate outliers/batch effects; harmonize gene IDs | DESeq2 analysis of Dataset 2; DEG table and volcano plot | Test Logistic Regression, Random Forest and SVM |
| **Aug 30–Sep 1** | Support dataset integration and verify overlapping genes | Identify overlapping DEGs | Prepare ML feature matrix |
| **Sep 2–5** | Verify technical consistency; prepare final expression matrices | Validate consistent DEG direction; GO and KEGG analysis | Feature selection and initial ML training |
| **Sep 6–8** | Re-run and validate preprocessing pipeline | Analyze biological significance and resistance-associated genes | Cross-validation and performance evaluation |
| **Sep 9–10** | Final data documentation | Literature comparison and biological interpretation | ROC curves, confusion matrices and model comparison |
| **Sep 11–12** | Final reproducibility check | Finalize biological interpretation | Feature importance and final biomarker panel |
| **Sep 13** | Write Data & Methods section | Write DEG, pathway and biological results | Write ML and biomarker results |
| **Sep 14** | colspan="3" | **Team Integration:** combine report, verify results, figures and reproducibility |
| **Sep 15** | colspan="3" | **Final Submission & Presentation** |

---

## 13. Success Metrics

The project will aim to demonstrate:

- At least **2 independent GEO datasets**
- At least **3 biological replicates per condition**, preferably 5–10
- Clear separation/quality assessment through PCA and clustering
- Statistically significant DEGs using predefined FDR and fold-change thresholds
- A set of **consistently regulated genes across datasets**
- Statistically enriched GO/KEGG biological pathways
- ML models capable of distinguishing resistant and sensitive samples under appropriate cross-validation
- Quantitative evaluation using **ROC-AUC, F1-score, Precision, Recall and Accuracy**
- Identification of a small, biologically interpretable candidate biomarker panel
- Complete reproducibility through documented R/ML code and a final report

---

## 14. Final Project Workflow

```text
NCBI GEO
   ↓
Select 2 Independent Bulk RNA-seq Datasets
   ↓
Download Count Matrices + Metadata
   ↓
Preprocessing & Quality Control
   ↓
DESeq2 Differential Expression
   ↓
DEGs from Dataset 1 ─────┐
                         ├──→ Cross-Dataset Validation
DEGs from Dataset 2 ─────┘
                         ↓
                 Validated DEGs
                    ↙       ↘
              GO / KEGG      Machine Learning
                    ↓             ↓
             Biological       Biomarker
             Interpretation    Discovery
                    ↘             ↙
                     Final Biomarker Panel
                             ↓
                    Reproducible Report
```

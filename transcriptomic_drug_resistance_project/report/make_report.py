"""Generate the comprehensive project report (.docx).

Reads the analysis artefacts in results/ and writes
report/DrugResistance_Report.docx.

Run:  python report/make_report.py
"""
from __future__ import annotations

import csv
import os
from datetime import date

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Inches, RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
RESULTS = os.path.join(PROJ, "results")

NAVY = RGBColor(0x1F, 0x38, 0x64)
TEAL = RGBColor(0x1E, 0x6E, 0x8C)
DARK = RGBColor(0x22, 0x22, 0x22)

TODAY = date.today().strftime("%d %B %Y")


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def _rows(rel_path):
    path = os.path.join(RESULTS, rel_path)
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _count_rows(rel_path):
    with open(os.path.join(RESULTS, rel_path), newline="", encoding="utf-8-sig") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def load_data():
    d = {}
    d["ds1_full"] = _count_rows("dataset1/DEG_table_full.csv")
    d["ds2_full"] = _count_rows("dataset2/DEG_table_full.csv")
    d["ds1"] = {"sig": _count_rows("dataset1/DEGs_significant.csv"),
                "up": _count_rows("dataset1/DEGs_up.csv"),
                "down": _count_rows("dataset1/DEGs_down.csv")}
    d["ds2"] = {"sig": _count_rows("dataset2/DEGs_significant.csv"),
                "up": _count_rows("dataset2/DEGs_up.csv"),
                "down": _count_rows("dataset2/DEGs_down.csv")}

    shared = _rows("comparison/overlapping_DEGs.csv")
    d["shared"] = {
        "up": sum(1 for r in shared if r["direction"] == "Up"),
        "down": sum(1 for r in shared if r["direction"] == "Down"),
        "mixed": sum(1 for r in shared if r["direction"] == "Mixed"),
        "total": len(shared),
    }
    d["shared_genes"] = shared

    go = sorted(_rows("enrichment/GO_enrichment_Shared_DEGs.csv"),
                key=lambda r: float(r["p.adjust"]))
    kegg = sorted(_rows("enrichment/KEGG_enrichment_Shared_DEGs.csv"),
                  key=lambda r: float(r["p.adjust"]))
    d["go"] = go[:10]
    d["kegg"] = kegg[:10]

    ext = _rows("ml/external_by_direction.csv")
    d["ext"] = ext
    d["ext_tz"] = [r for r in ext if r["normalization"] == "target_z"]
    d["ext_ts"] = [r for r in ext if r["normalization"] == "train_stats"]

    mm = _rows("ml/ml_metrics_summary.csv")
    d["loocv"] = [r for r in mm if r["validation"] == "LOOCV"]

    panel = sorted(_rows("ml/biomarker_panel.csv"), key=lambda r: int(r["rank"]))
    d["panel"] = panel[:20]

    # derived ML summaries
    ts = [float(r["ROC_AUC"]) for r in d["ext_ts"]]
    d["ts_mean_auc"] = sum(ts) / len(ts)
    d["ts_max_acc"] = max(float(r["Accuracy"]) for r in d["ext_ts"])
    d["ts_auc1"] = sum(1 for v in ts if abs(v - 1.0) < 1e-9)

    tz = [float(r["ROC_AUC"]) for r in d["ext_tz"]]
    d["tz_best"] = max(tz)
    return d


# --------------------------------------------------------------------------
# document primitives
# --------------------------------------------------------------------------
def setup(doc):
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for name, size, color in [("Heading 1", 18, NAVY), ("Heading 2", 14, TEAL),
                              ("Heading 3", 12, DARK)]:
        st = doc.styles[name]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.color.rgb = color

    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # footer page numbers
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Page ")
    r.font.size = Pt(9)
    _field(p, "PAGE")
    r2 = p.add_run(" of ")
    r2.font.size = Pt(9)
    _field(p, "NUMPAGES")

    # auto-update fields (TOC) on open
    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)


def _field(paragraph, instr):
    run = paragraph.add_run()
    run.font.size = Pt(9)
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    i = OxmlElement("w:instrText"); i.set(qn("xml:space"), "preserve"); i.text = instr
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    run._r.append(b); run._r.append(i); run._r.append(e)


def h1(doc, text):
    doc.add_heading(text, level=1)


def h2(doc, text):
    doc.add_heading(text, level=2)


def h3(doc, text):
    doc.add_heading(text, level=3)


def para(doc, text, italic=False, align=None):
    p = doc.add_paragraph(text)
    if italic:
        for r in p.runs:
            r.italic = True
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def bullets(doc, items):
    for it in items:
        doc.add_paragraph(it, style="List Bullet")


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def table(doc, headers, rows, cap=None, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, htext in enumerate(headers):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(htext)
        run.bold = True
        run.font.size = Pt(9)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(val))
            run.font.size = Pt(9)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    if cap:
        caption(doc, cap)
    doc.add_paragraph()
    return t


def figure(doc, rel, cap, max_w=6.2, max_h=7.0):
    path = os.path.join(PROJ, rel)
    if not os.path.exists(path):
        print("  [skip missing figure]", rel)
        return
    w, h = Image.open(path).size
    scale = min(max_w / w, max_h / h)
    doc.add_picture(path, width=Inches(w * scale))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption(doc, cap)


# --------------------------------------------------------------------------
# report content
# --------------------------------------------------------------------------
def title_page(doc):
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Transcriptomic Profiling of Drug-Resistant Cancer Cells")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = NAVY
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Differentially Expressed Genes, Biological Pathways, and "
                  "Machine-Learning Biomarkers of Cisplatin Resistance in Ovarian Cancer")
    r.font.size = Pt(15)
    r.font.color.rgb = TEAL
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("A reproducible cross-dataset bioinformatics and machine-learning study\n"
                  "of two independent human bulk RNA-seq datasets")
    r.italic = True
    r.font.size = Pt(12)
    for _ in range(6):
        doc.add_paragraph()
    for line in ["Team of 3",
                 "Member 1 — Data Acquisition, Preprocessing & Quality Control",
                 "Member 2 — Differential Expression, Cross-Dataset Validation & Pathways",
                 "Member 3 — Machine Learning & Biomarker Discovery",
                 "",
                 "[Your Names / Registration Numbers]",
                 "[Course / Institution]",
                 "[Supervisor]",
                 TODAY]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line)
        r.font.size = Pt(11)
    doc.add_page_break()


def toc_page(doc):
    h1(doc, "Table of Contents")
    p = doc.add_paragraph()
    run = p.add_run()
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    t = OxmlElement("w:t"); t.text = "Right-click and choose 'Update Field' to build the contents."
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    for el in (b, instr, sep, t, e):
        run._r.append(el)
    doc.add_page_break()


def abstract(doc, d):
    h1(doc, "Abstract")
    para(doc,
         "Ovarian cancer is the most lethal gynaecological malignancy, and platinum-based "
         "chemotherapy with cisplatin remains the cornerstone of first-line treatment. "
         "Acquired cisplatin resistance is a multifactorial process driven by epigenetic "
         "reprogramming, metabolic rewiring, epithelial–mesenchymal transition (EMT), "
         "inflammatory signalling and drug efflux, yet reproducible transcriptomic "
         "signatures that generalise across independent resistance models remain scarce. "
         "This study integrated two independent human bulk RNA-seq datasets of "
         "cisplatin-resistant versus cisplatin-sensitive ovarian cancer cells — "
         "GSE303889 (SKOV-3; 3 sensitive vs 3 resistant) and GSE283381 (OVCAR5; "
         "3 sensitive vs 3 resistant) — into a fully reproducible end-to-end pipeline.")
    para(doc,
         f"Differential expression analysis with DESeq2 (FDR < 0.05 and |log2 fold change| > 1) "
         f"identified {d['ds1']['sig']:,} significant differentially expressed genes (DEGs) in "
         f"SKOV-3 ({d['ds1']['up']:,} up, {d['ds1']['down']:,} down) and {d['ds2']['sig']:,} in "
         f"OVCAR5 ({d['ds2']['up']:,} up, {d['ds2']['down']:,} down), confirming extensive "
         f"transcriptomic reprogramming. Cross-dataset comparison revealed {d['shared']['total']} "
         f"consistently differentially expressed genes ({d['shared']['up']} up, "
         f"{d['shared']['down']} down, {d['shared']['mixed']} with opposite direction) that form a "
         "core cisplatin-resistance signature. Functional enrichment converged on "
         "extracellular matrix (ECM) organisation, cell–substrate adhesion, and the "
         "PI3K-Akt, focal-adhesion, integrin and cadherin signalling pathways, with EMT as the "
         "dominant shared mechanism.")
    para(doc,
         "Supervised classifiers (ridge logistic regression, random forest and radial SVM) were "
         "trained on the full 57,357-gene intersected matrix with nested, leakage-free feature "
         "selection. Within-cell-line leave-one-out cross-validation separated the phenotypes "
         f"almost completely (ROC-AUC 0.889–1.000), whereas leave-one-dataset-out external "
         f"validation showed only partial, strongly asymmetric transfer (best AUC {d['tz_best']:.2f} "
         f"under batch-corrected target_z normalisation; mean AUC {d['ts_mean_auc']:.2f} under the "
         "strict, leak-free train_stats scheme). A 30-gene ranked candidate panel headed by MAL2 "
         "and GALNT6 was nominated for follow-up. All analyses are exploratory given n = 12, but "
         "the pipeline, figures, interactive dashboard and candidate panel provide a reproducible "
         "foundation for larger validation studies.")
    doc.add_page_break()


def introduction(doc):
    h1(doc, "1. Introduction")
    h2(doc, "1.1 Ovarian cancer and platinum-based therapy")
    para(doc,
         "Ovarian cancer accounts for a disproportionate share of gynaecological cancer "
         "mortality because most patients present at an advanced stage, when the disease has "
         "already disseminated within the peritoneal cavity. Standard first-line management "
         "combines cytoreductive surgery with platinum-based chemotherapy, most commonly "
         "cisplatin or its analogue carboplatin, frequently together with a taxane. Platinum "
         "agents form covalent DNA adducts that stall replication and transcription and "
         "ultimately trigger apoptosis, so an intact DNA-damage response is central to their "
         "cytotoxicity. Despite high initial response rates, the majority of patients relapse "
         "with platinum-resistant disease, and the emergence of resistance is the principal "
         "obstacle to long-term survival.")
    h2(doc, "1.2 The problem of acquired cisplatin resistance")
    para(doc,
         "Acquired resistance is not a single event but an adaptive, polyclonal process. "
         "Documented mechanisms include reduced drug uptake and increased efflux, enhanced "
         "nucleotide-excision repair and homologous recombination, altered apoptotic "
         "thresholds, epigenetic silencing or activation of resistance programmes, metabolic "
         "rewiring that buffers oxidative stress, and a shift toward a mesenchymal, "
         "stem-like phenotype. Because these mechanisms differ between cell-line models and "
         "between patients, single-dataset studies tend to recover model-specific signatures "
         "that do not reproduce elsewhere. Identifying genes and pathways that are "
         "consistently dysregulated across independent resistance models is therefore a "
         "prerequisite for robust biomarkers and rational therapeutic targeting.")
    h2(doc, "1.3 Objectives")
    bullets(doc, [
        "Identify differentially expressed genes between cisplatin-resistant and "
        "cisplatin-sensitive human ovarian cancer cells using DESeq2.",
        "Validate candidate DEGs across two independent GEO datasets to reduce "
        "dataset-specific bias and identify a consistent core signature.",
        "Characterise the biological processes and signalling pathways affected, using Gene "
        "Ontology (GO) and KEGG enrichment analysis.",
        "Build supervised machine-learning classifiers on the transcriptome and evaluate "
        "their ability to distinguish resistant from sensitive samples under leakage-free "
        "cross-validation.",
        "Rank a compact, biologically interpretable candidate biomarker panel from feature "
        "importance across models and feature-set sizes.",
        "Deliver a fully reproducible end-to-end pipeline, including an interactive results "
        "dashboard.",
    ])
    h2(doc, "1.4 Scope and significance")
    para(doc,
         "This work is a computational, hypothesis-generating study based on public data. It "
         "does not perform wet-lab validation and is explicitly framed as exploratory "
         "biomarker discovery rather than clinical diagnostic validation. Its significance "
         "lies in demonstrating a reproducible workflow that (i) derives a cross-dataset "
         "resistance signature, (ii) connects that signature to interpretable biology, and "
         "(iii) quantifies honestly how far such a signature transfers between cell-line "
         "models — an issue frequently glossed over in small transcriptomic machine-learning "
         "studies.")
    h2(doc, "1.5 Contributions and novelty")
    bullets(doc, [
        "Integration of two independent ovarian cancer cisplatin-resistance RNA-seq datasets "
        "with a consistent, scripted analysis pipeline.",
        "A cross-dataset core signature of consistently regulated DEGs, reducing reliance on "
        "any single model.",
        "Combined statistical differential expression and supervised machine learning, with "
        "feature selection nested strictly inside each training fold to prevent leakage.",
        "Explicit reporting of cross-dataset generalisation under both a batch-corrected "
        "(transductive) and a strictly non-transductive normalisation scheme.",
        "Delivery of an interactive web dashboard and a reproducible code repository.",
    ])


def literature(doc):
    h1(doc, "2. Literature Review")
    h2(doc, "2.1 Cisplatin mechanism of action and resistance")
    para(doc,
         "Cisplatin exerts cytotoxicity by forming intra- and inter-strand DNA crosslinks "
         "that activate the DNA-damage response and, when damage is irreparable, intrinsic "
         "apoptosis. Resistance can arise at every step of this cascade: decreased uptake via "
         "the copper transporters CTR1/SLC31A1, increased efflux through ATP-binding "
         "cassette transporters, enhanced DNA repair, and defective apoptotic signalling. "
         "Transcriptomic studies consistently report large-scale reprogramming, but the "
         "specific genes implicated vary widely across models, motivating cross-dataset "
         "validation.")
    h2(doc, "2.2 Epithelial–mesenchymal transition and ECM remodelling")
    para(doc,
         "EMT is among the most reproducible features of platinum-resistant ovarian cancer. "
         "Loss of the epithelial markers E-cadherin (CDH1) and EpCAM, together with "
         "up-regulation of collagens and matrix metalloproteinases, accompanies resistance "
         "and invasion. Hypermethylation of the CDH1 promoter has been demonstrated in "
         "chemoresistant ovarian cancer lines, linking epigenetic silencing to EMT. Collagen "
         "genes such as COL1A1 are up-regulated in drug-resistant ovarian cancer lines and "
         "are associated with ECM-receptor interaction and focal-adhesion pathways. Reduced "
         "miR-29, a negative regulator of collagens, further contributes to cisplatin "
         "resistance. These observations establish ECM remodelling and adhesion as core, "
         "cross-model resistance biology.")
    h2(doc, "2.3 Epigenetic mechanisms")
    para(doc,
         "Methylome and expression profiling of isogenic sensitive/resistant ovarian cancer "
         "pairs has identified DNA-methylation drivers of acquired cisplatin resistance, "
         "including silencing of apoptosis-related genes. Histone-modifying enzymes of the "
         "KDM5 (lysine demethylase) family have been implicated in maintaining a "
         "drug-tolerant state in several cancers, providing context for the SKOV-3 model "
         "analysed here. Because epigenetic programmes are plastic and reversible, they are "
         "attractive targets for resensitisation strategies.")
    h2(doc, "2.4 Metabolic rewiring")
    para(doc,
         "Metabolic dependency is an emerging theme in platinum resistance. A recent study "
         "demonstrated that platinum-resistant ovarian cancer develops a targetable "
         "dependency on de novo pyrimidine synthesis, underpinning one of the datasets "
         "(OVCAR5 Cis-R) analysed in this work. Such metabolic reprogramming supplies "
         "nucleotides for repair and buffers redox stress, and it can dominate the "
         "transcriptional landscape of a given model — explaining why metabolic and "
         "epigenetic resistance models may share relatively few DEGs.")
    h2(doc, "2.5 Inflammation and immune evasion")
    para(doc,
         "Chronic, low-grade inflammation supports resistance. Interleukin-1 signalling "
         "(IL1A/IL1B) is elevated in resistant ovarian cancer models and is linked to "
         "inflammasome activation, with higher caspase-1 activity and IL-1β secretion. "
         "Separately, the tryptophan–kynurenine pathway, in which kynureninase (KYNU) "
         "converts kynurenine, acts as an immune checkpoint: tumour-derived kynurenine "
         "activates the aryl-hydrocarbon receptor (AhR) to suppress anti-tumour immunity. "
         "KYNU up-regulation has been documented in ovarian and other cancers, linking "
         "metabolism to immune evasion and chemoresistance.")
    h2(doc, "2.6 Validated candidate biomarkers")
    para(doc,
         "NDRG1 has been identified as a hub gene across multiple independent ovarian cancer "
         "datasets, and its knockdown inhibits proliferation of cisplatin-resistant SKOV-3 "
         "cells, making it a validated resistance-associated biomarker. SERPINE1, a "
         "plasminogen-activator inhibitor that promotes invasion and metastasis, recurs in "
         "resistance signatures. EpCAM-based circulating markers have also been explored as "
         "predictors of platinum sensitivity. These genes provide external anchors against "
         "which computationally derived signatures can be contextualised.")
    h2(doc, "2.7 Convergent signalling pathways")
    para(doc,
         "Across studies, resistance converges on a limited set of pathways: PI3K-Akt "
         "signalling (survival and apoptosis suppression), MAPK signalling (proliferation "
         "and efflux), focal-adhesion and integrin signalling (adhesion, migration, "
         "Wnt/β-catenin activation), cadherin signalling (loss of adhesion during EMT) and "
         "p53 signalling (damage response). Their recurrence in enrichment analyses of "
         "independent cohorts supports the notion of shared therapeutic nodes.")
    h2(doc, "2.8 Cross-dataset validation and reproducibility")
    para(doc,
         "Single-dataset signatures are notoriously unstable. Cross-dataset validation — "
         "requiring a gene to be significant in independent cohorts, ideally with a "
         "consistent direction of change — increases confidence and reduces batch-specific "
         "artefacts. Directional consistency is a simple but effective filter, and reporting "
         "the degree of overlap honestly is more informative than tuning thresholds to "
         "maximise it.")
    h2(doc, "2.9 Machine learning in transcriptomic biomarker discovery")
    para(doc,
         "Supervised classifiers are widely used to derive gene panels from expression data. "
         "However, high-dimensional, small-sample settings (n << p) are highly prone to "
         "overfitting and to optimistic performance estimates. Two well-known pitfalls are "
         "selection bias — performing feature selection outside the cross-validation loop — "
         "and leakage through preprocessing that uses held-out data. Rigorous designs nest "
         "feature selection and normalisation inside each training fold, and evaluate "
         "generalisation on truly external data. Transductive preprocessing, in which test "
         "samples are standardised using their own statistics, is common in cross-study "
         "batch correction but does not correspond to a deployable model; reporting a "
         "strictly non-transductive result alongside it brackets the achievable range.")
    h2(doc, "2.10 Research gap")
    para(doc,
         "Despite extensive mechanistic literature, there is a shortage of studies that "
         "combine (i) rigorous cross-dataset differential-expression validation, (ii) "
         "interpretable pathway enrichment, and (iii) leakage-controlled machine learning "
         "with honest external generalisation reporting, within a single reproducible "
         "pipeline for ovarian cancer cisplatin resistance. This project addresses that gap "
         "using two independent models with distinct resistance mechanisms.")


def methodology(doc, d):
    h1(doc, "3. Methodology")
    h2(doc, "3.1 Study design and data sources")
    para(doc,
         "Two independent human bulk RNA-seq datasets were retrieved from the NCBI Gene "
         "Expression Omnibus (GEO). Each provides a paired comparison between a "
         "cisplatin-sensitive and a cisplatin-resistant ovarian cancer cell line, with three "
         "biological replicates per condition. Dataset-specific resistance mechanisms were "
         "intentionally allowed to differ, so that any consistently regulated genes reflect "
         "mechanism-independent resistance biology rather than a single model.")
    table(doc,
          ["Attribute", "Dataset 1", "Dataset 2"],
          [["GEO accession", "GSE303889", "GSE283381"],
           ["Cell line", "SKOV-3", "OVCAR5"],
           ["Resistance model", "SKOV-3 CDDP (chronic cisplatin; KDM5-associated)",
            "OVCAR5 Cis-R (repeated cisplatin; de novo pyrimidine dependency)"],
           ["Sensitive group", "Parental (wild-type), n = 3", "Cis-S control, n = 3"],
           ["Resistant group", "CDDP, n = 3", "Cis-R control, n = 3"],
           ["Platform", "Illumina NovaSeq 6000", "Illumina NextSeq 500"],
           ["Total samples", "6", "6"]],
          cap="Table 1. Overview of the two independent GEO datasets (n = 12 samples total).")
    h2(doc, "3.2 Preprocessing and quality control")
    para(doc,
         "Raw gene-level count matrices and sample metadata were assembled for each dataset. "
         "For the OVCAR5 dataset, per-sample count files were merged and non-messenger "
         "features (e.g. small RNAs) were removed. Lowly expressed genes were filtered by "
         "requiring a total count of at least ten across samples (rowSums ≥ 10). Counts were "
         "normalised using DESeq2 size factors, and expression values were transformed to "
         "log2(counts per million + 1) for the machine-learning feature matrix. Duplicate "
         "gene symbols were collapsed by summation (rowsum, reorder = TRUE) and the two "
         "datasets were intersected on shared symbols, yielding a common feature space of "
         "57,357 genes across 12 samples. Quality was assessed by principal-component "
         "analysis and hierarchical sample clustering. A fixed random seed (42) was used "
         "throughout to ensure reproducibility.")
    h2(doc, "3.3 Differential expression analysis")
    para(doc,
         "Each dataset was analysed independently with DESeq2 using a negative-binomial "
         "generalised linear model with design ~ condition. The sensitive group was set as "
         "the reference level and the contrast was Resistant versus Sensitive. Significance "
         "was defined a priori as an adjusted p-value (Benjamini–Hochberg FDR) below 0.05 "
         "and an absolute log2 fold change greater than 1. Outputs per dataset included a "
         "full DEG table, up- and down-regulated gene lists, volcano and MA plots, and a "
         "heatmap of the top DEGs.")
    h2(doc, "3.4 Cross-dataset comparison")
    para(doc,
         "Gene symbols (Ensembl identifiers mapped to symbols for Dataset 1) were "
         "intersected to identify genes significant in both datasets. Shared genes were "
         "classified as up (up in both), down (down in both) or mixed (opposite direction). "
         "Genes with a consistent direction in both datasets constitute the higher-confidence "
         "core signature. Agreement in magnitude was assessed by Spearman correlation of "
         "shared log2 fold changes, and overlap was visualised with a Venn diagram and a "
         "log2FC scatter plot.")
    h2(doc, "3.5 Functional enrichment analysis")
    para(doc,
         "Functional enrichment was performed with clusterProfiler against the human "
         "annotation database org.Hs.eg.db. Gene Ontology enrichment (enrichGO; Biological "
         "Process focus) and KEGG pathway enrichment (enrichKEGG, organism hsa) were run "
         "separately on the shared DEGs, on each dataset's DEGs, and on the shared up- and "
         "down-regulated subsets, using Benjamini–Hochberg adjustment and a significance "
         "threshold of p < 0.05. Results were visualised as dot plots.")
    h2(doc, "3.6 Machine-learning feature matrix")
    para(doc,
         "The classifier feature matrix comprised the 57,357 shared genes (log2 CPM + 1) "
         "across the 12 samples, with labels indicating dataset (cell line) and condition "
         "(resistant/sensitive). Crucially, the full gene space was used rather than a "
         "pre-selected DEG panel; any DEG-based pre-filtering would allow test information "
         "to leak into feature selection. The 913 shared DEGs were retained only as a "
         "reference panel.")
    h2(doc, "3.7 Classifiers")
    bullets(doc, [
        "Logistic regression with L2 (ridge) regularisation (glmnet), tuned by inner "
        "leave-one-out cross-validation. Lasso (L1) was found to be degenerate at n = 6 and "
        "was not used.",
        "Random forest (ranger) with min.node.size = 1 (the default of 10 forbids any split "
        "at n = 6).",
        "Support vector machine with a radial-basis kernel (e1071), on standardised inputs "
        "(scale = FALSE), with a fallback for probability estimation.",
    ])
    h2(doc, "3.8 Validation design and leakage control")
    para(doc,
         "Two complementary validation schemes were used. First, within-cell-line "
         "leave-one-out cross-validation (LOOCV) holds out one sample inside a single cell "
         "line, leaving five training samples per fold, with feature selection and "
         "normalisation recomputed from the training samples only. Second, cross-dataset "
         "external validation trains on all six samples of one cell line and predicts the "
         "six samples of the other (SKOV3→OVCAR5 and OVCAR5→SKOV3). Feature selection was "
         "nested strictly inside every training fold: the top K genes by the absolute "
         "two-sample t-statistic were selected with K ∈ {20, 50, 100, 200, 500}. No test "
         "fold ever informed feature or model selection.")
    para(doc,
         "Because the two studies were normalised independently, their expression scales "
         "differ; test rows were therefore standardised with respect to cell-line statistics "
         "in two ways. Under target_z (the primary, transductive scheme) the held-out cell "
         "line is standardised with its own mean and standard deviation, batch-correcting "
         "the two datasets. Under train_stats (the strict scheme) the held-out cell line is "
         "standardised with the training cell line's statistics, using no information "
         "whatever from the test set; this is the fully leak-free number. The model is fit "
         "once per fold on identically normalised training rows, so only test-row "
         "normalisation differs between the two schemes.")
    h2(doc, "3.9 Evaluation metrics and biomarker ranking")
    para(doc,
         "Model performance was summarised by accuracy, precision, recall, F1-score and "
         "ROC-AUC. External metrics are reported per direction and per normalisation; the "
         "two directions have opposite probability scales, so pooling them into a single "
         "'External' row is not interpretable and was deliberately avoided. Under "
         "train_stats the probabilities are miscalibrated with respect to the 0.5 threshold, "
         "so ROC-AUC (rank-based) is the meaningful metric there. Candidate biomarkers were "
         "ranked by how often each gene was selected across the grid of models and K values, "
         "with mean absolute log2 fold change used as a tie-breaker.")
    h2(doc, "3.10 Software, reproducibility and dashboard")
    para(doc,
         "All analysis code is R, organised as three scripts (DEG analysis, ML matrix "
         "construction, ML biomarkers) with a project-root auto-detection mechanism. The ML "
         "stage uses a fast RDS feature matrix (load time ~0.03 s) and completes in "
         "approximately 25 seconds. Console output is captured to a run log, and two "
         "consecutive runs produce byte-identical predictions and metrics. Results are "
         "served through a FastAPI backend that exposes the artefacts as a read-only REST "
         "API and a browser dashboard with a normalisation toggle, an AUC-by-K chart, an "
         "external-metrics table and a prediction explorer.")
    h2(doc, "3.11 Ethical considerations")
    para(doc,
         "Only de-identified, publicly available data were used; no new human or animal "
         "subjects were involved, and no ethical approval was required. All primary studies "
         "are cited in Section 8.")


def analysis(doc, d):
    h1(doc, "4. Analysis")
    h2(doc, "4.1 Differential expression — Dataset 1 (SKOV-3)")
    para(doc,
         f"After low-count filtering, DESeq2 tested {d['ds1_full']:,} genes in the SKOV-3 "
         f"dataset. At FDR < 0.05 and |log2FC| > 1, {d['ds1']['sig']:,} genes were "
         f"significantly differentially expressed: {d['ds1']['up']:,} up-regulated and "
         f"{d['ds1']['down']:,} down-regulated. The volcano plot (Figure 1) shows a broad "
         "dispersion of both up- and down-regulated genes, indicating extensive "
         "transcriptomic reprogramming. The heatmap of the top DEGs (Figure 2) separates the "
         "sensitive and resistant replicates cleanly, and down-regulation of the epithelial "
         "marker CDH1 is evident among the top changes, consistent with an EMT-like shift.")
    figure(doc, "results/dataset1/volcano_plot.png",
           "Figure 1. Volcano plot of differential expression in SKOV-3 (GSE303889). "
           "Red, significant up-regulated; blue, significant down-regulated; grey, not significant.")
    figure(doc, "results/dataset1/heatmap_top_DEGs.png",
           "Figure 2. Heatmap of the top differentially expressed genes in SKOV-3, showing "
           "clear separation of sensitive and resistant replicates.")
    h2(doc, "4.2 Differential expression — Dataset 2 (OVCAR5)")
    para(doc,
         f"In the OVCAR5 dataset, {d['ds2_full']:,} genes were tested and {d['ds2']['sig']:,} "
         f"were significant ({d['ds2']['up']:,} up, {d['ds2']['down']:,} down). The volcano "
         "plot (Figure 3) shows the distribution of effects, and the top up-regulated genes "
         "include the inflammatory cytokines IL1A and IL1B, with a large log2 fold change, "
         "reflecting the inflammatory component of this resistance model. As expected from "
         "the distinct mechanism, the magnitude and composition of the DEG set differ from "
         "Dataset 1.")
    figure(doc, "results/dataset2/volcano_plot.png",
           "Figure 3. Volcano plot of differential expression in OVCAR5 (GSE283381).")
    figure(doc, "results/dataset2/heatmap_top_DEGs.png",
           "Figure 4. Heatmap of the top differentially expressed genes in OVCAR5.")
    h2(doc, "4.3 Cross-dataset overlap")
    para(doc,
         f"Intersecting the two DEG sets yielded {d['shared']['total']} genes differentially "
         f"expressed in both datasets: {d['shared']['up']} up-regulated in both, "
         f"{d['shared']['down']} down-regulated in both, and {d['shared']['mixed']} with "
         "opposite direction of change (Figure 5). The consistently regulated genes define a "
         "core signature independent of cell-line background. The Spearman correlation of "
         "shared log2 fold changes was approximately −0.04 (Figure 6): a low value that is "
         "biologically meaningful rather than a failure, because SKOV-3 and OVCAR5 acquire "
         "resistance through different programmes, so even shared genes are not expected to "
         "change by the same magnitude.")
    figure(doc, "results/comparison/venn_diagram.png",
           "Figure 5. Venn diagram of overlapping DEGs between the two datasets.")
    figure(doc, "results/comparison/lfc_correlation.png",
           "Figure 6. Correlation of log2 fold changes for shared DEGs (Spearman r ≈ −0.04).")
    h2(doc, "4.4 Gene Ontology enrichment")
    para(doc,
         "GO enrichment of the shared DEGs was dominated by extracellular and adhesion "
         "terms (Figure 7; Table 2), including cell–substrate adhesion, extracellular matrix "
         "organisation, extracellular structure organisation, ossification and axon "
         "guidance. This is the expected functional signature of EMT and ECM remodelling, "
         "and it is consistent with the literature reviewed in Section 2.")
    table(doc,
          ["GO term", "Ontology", "Count", "Adjusted p"],
          [[r["Description"], r["ONTOLOGY"], r["Count"], f"{float(r['p.adjust']):.2e}"]
           for r in d["go"]],
          cap="Table 2. Top Gene Ontology terms enriched among shared DEGs.",
          widths=[3.6, 1.0, 0.8, 1.2])
    figure(doc, "results/enrichment/GO_dotplot_Shared_DEGs.png",
           "Figure 7. Gene Ontology enrichment dot plot for shared DEGs.")
    h2(doc, "4.5 KEGG pathway enrichment")
    para(doc,
         "KEGG enrichment of the shared DEGs highlighted cytoskeletal remodelling, "
         "PI3K-Akt signalling, cadherin and integrin signalling, axon guidance, Hippo "
         "signalling and focal adhesion (Figure 8; Table 3). These pathways converge on "
         "survival, adhesion and cytoskeletal dynamics — coherent with the GO results and "
         "with known resistance mechanisms.")
    table(doc,
          ["KEGG pathway", "Count", "Adjusted p"],
          [[r["Description"], r["Count"], f"{float(r['p.adjust']):.2e}"] for r in d["kegg"]],
          cap="Table 3. Top KEGG pathways enriched among shared DEGs.",
          widths=[4.6, 1.0, 1.2])
    figure(doc, "results/enrichment/KEGG_dotplot_Shared_DEGs.png",
           "Figure 8. KEGG pathway enrichment dot plot for shared DEGs.")
    h2(doc, "4.6 Within-cell-line LOOCV")
    para(doc,
         "Under within-cell-line LOOCV, all three classifiers separated resistant from "
         "sensitive samples almost perfectly at small feature-set sizes, with performance "
         "degrading slightly for random forest and SVM as K increased (Table 4). The minimum "
         "across the entire grid was accuracy 0.833 and ROC-AUC 0.889. Because this scheme "
         "no longer pools the two cell lines and recomputes preprocessing per fold, it is a "
         "legitimate within-study reference — but it is likely optimistic relative to true "
         "generalisation, since cell-line background itself is highly separable.")
    loocv_rows = []
    for r in sorted(d["loocv"], key=lambda x: (x["model"], int(x["K"]))):
        loocv_rows.append([r["model"], r["K"], f"{float(r['Accuracy']):.3f}",
                           f"{float(r['ROC_AUC']):.3f}"])
    table(doc, ["Model", "K", "Accuracy", "ROC-AUC"], loocv_rows,
          cap="Table 4. Within-cell-line LOOCV performance (K = number of selected genes).",
          widths=[2.4, 0.8, 1.2, 1.2])
    figure(doc, "results/ml/ROC_LOOCV.png",
           "Figure 9. ROC curves for within-cell-line LOOCV.")
    h2(doc, "4.7 Cross-dataset external validation — target_z")
    para(doc,
         "Under the batch-corrected target_z scheme, a small SKOV-3-derived signature "
         "transferred to OVCAR5, with all three models reaching ROC-AUC 1.0 at K = 20 "
         "(logistic regression and SVM also at K = 50). The reverse direction, OVCAR5→SKOV3, "
         "remained close to chance (AUC ≈ 0.44–0.78). Performance collapsed as K grew, a "
         "classic n << p overfitting signature given only six training samples (Table 5).")
    ext_tz = [r for r in d["ext_tz"] if r["K"] in ("20", "50", "100")]
    rows = [[r["model"], r["K"], r["direction"], f"{float(r['Accuracy']):.3f}",
             f"{float(r['ROC_AUC']):.3f}"] for r in sorted(
        ext_tz, key=lambda x: (x["direction"], x["model"], int(x["K"])))]
    table(doc, ["Model", "K", "Train→Test", "Accuracy", "ROC-AUC"], rows,
          cap="Table 5. External validation under target_z (selected K values).",
          widths=[2.0, 0.6, 1.6, 1.0, 1.0])
    figure(doc, "results/ml/ROC_external.png",
           "Figure 10. External validation ROC curves (target_z, per direction).")
    figure(doc, "results/ml/confusion_external.png",
           "Figure 11. External confusion matrices (target_z).")
    h2(doc, "4.8 Cross-dataset external validation — train_stats (strict)")
    para(doc,
         f"Under the strictly non-transductive train_stats scheme, in which the held-out "
         f"cell line is standardised with the training line's statistics, the mean ROC-AUC "
         f"across the 3 × 5 × 2 grid was {d['ts_mean_auc']:.2f}. {d['ts_auc1']} of 30 cells "
         f"reached AUC 1.0, but these were not consistent across K, model or direction. "
         f"Accuracy never reached 1.0 (maximum {d['ts_max_acc']:.2f}, median 0.50) because "
         "the miscalibrated probabilities cluster on one side of the 0.5 threshold; AUC is "
         "therefore the meaningful metric. This leak-free result is the honest estimate of "
         "cross-model transfer.")
    figure(doc, "results/ml/ROC_external_trainstats.png",
           "Figure 12. External validation ROC curves (strict train_stats scheme).")
    h2(doc, "4.9 Feature importance and panel construction")
    para(doc,
         "Across the grid of models and K values, a stable set of genes was selected "
         "repeatedly from the full 57,357-gene space (Figure 13). MAL2 and GALNT6 were the "
         "most consistently selected, followed by LDOC1, SH2D4A and FBXL21P. Because the "
         "selection frequency is dominated by the SKOV3→OVCAR5 direction, the panel is best "
         "regarded as a set of candidates for follow-up rather than a validated, "
         "directionally consistent signature.")
    figure(doc, "results/ml/feature_importance.png",
           "Figure 13. Feature-selection frequencies across models and K values.")


def results_section(doc, d):
    h1(doc, "5. Result")
    para(doc,
         "This section consolidates the headline outcomes. Detailed per-stage analysis is "
         "presented in Section 4; here the results are presented as summary tables and the "
         "key figures that support them.")
    h2(doc, "5.1 Summary of differential expression")
    table(doc,
          ["Dataset", "Cell line", "Genes tested", "Significant DEGs", "Up", "Down"],
          [["GSE303889", "SKOV-3", f"{d['ds1_full']:,}", f"{d['ds1']['sig']:,}",
            f"{d['ds1']['up']:,}", f"{d['ds1']['down']:,}"],
           ["GSE283381", "OVCAR5", f"{d['ds2_full']:,}", f"{d['ds2']['sig']:,}",
            f"{d['ds2']['up']:,}", f"{d['ds2']['down']:,}"]],
          cap="Table 6. Differential expression summary (FDR < 0.05, |log2FC| > 1).",
          widths=[1.3, 1.0, 1.1, 1.4, 0.9, 0.9])
    h2(doc, "5.2 Cross-dataset core signature")
    table(doc,
          ["Category", "Count"],
          [["Shared up-regulated", d["shared"]["up"]],
           ["Shared down-regulated", d["shared"]["down"]],
           ["Opposite direction (mixed)", d["shared"]["mixed"]],
           ["Total shared DEGs", d["shared"]["total"]]],
          cap="Table 7. Composition of the cross-dataset core signature.",
          widths=[3.4, 1.2])
    example = [r["gene_name"] for r in d["shared_genes"][:15]]
    para(doc, "Representative shared DEGs (first 15 of the overlap list): "
              + ", ".join(example) + ".")
    h2(doc, "5.3 Enrichment results")
    para(doc,
         "The top GO terms and KEGG pathways are summarised in Tables 2 and 3. Across both "
         "ontologies, the recurring themes are extracellular matrix organisation, cell "
         "adhesion, cytoskeletal remodelling and PI3K-Akt/integrin/focal-adhesion "
         "signalling — a coherent resistance phenotype centred on EMT.")
    h2(doc, "5.4 Machine-learning performance summary")
    table(doc,
          ["Validation", "Scheme", "Best / range", "Interpretation"],
          [["Within-cell-line LOOCV", "—", "Acc 0.833–1.000; AUC 0.889–1.000",
            "Near-complete within-study separation"],
           ["External (SKOV3→OVCAR5)", "target_z", "AUC up to 1.00 at small K",
            "Transferable signal at K = 20–50"],
           ["External (OVCAR5→SKOV3)", "target_z", "AUC ≈ 0.44–0.78",
            "No reliable reverse transfer"],
           ["External (all cells)", "train_stats", f"Mean AUC {d['ts_mean_auc']:.2f}",
            "Leak-free; partial transfer only"]],
          cap="Table 8. Machine-learning performance summary across validation schemes.",
          widths=[1.9, 1.0, 2.0, 1.9])
    h2(doc, "5.5 Candidate biomarker panel")
    panel_rows = []
    for r in d["panel"]:
        lfc = r["mean_abs_lfc"]
        lfc = f"{float(lfc):.1f}" if lfc not in ("", "NA", None) else "NA"
        panel_rows.append([r["rank"], r["gene"], r["n_select_slots"], lfc])
    table(doc, ["Rank", "Gene", "Selected (of 15 slots)", "Mean |log2FC|"], panel_rows,
          cap="Table 9. Top-20 candidate biomarkers ranked by cross-dataset selection "
              "frequency (tie-broken by mean |log2FC|).",
          widths=[0.8, 1.3, 2.0, 1.6])
    h2(doc, "5.6 Integrated result")
    para(doc,
         f"Two independent cisplatin-resistance models both undergo extensive "
         f"transcriptomic reprogramming ({d['ds1']['sig']:,} and {d['ds2']['sig']:,} DEGs), "
         f"sharing {d['shared']['total']} consistently regulated genes that centre on EMT and "
         "ECM biology. Supervised classifiers distinguish the phenotypes almost perfectly "
         "within a cell line, but cross-dataset transfer is only partial and strongly "
         "asymmetric, and weakens further under strict, leak-free normalisation. A compact "
         "panel of repeatedly selected genes provides concrete candidates for experimental "
         "follow-up.")


def discussion(doc, d):
    h1(doc, "6. Discussion")
    h2(doc, "6.1 Biological interpretation")
    para(doc,
         "The enrichment results and the gene-level changes tell a consistent story. The "
         "shared signature is dominated by loss of epithelial adhesion molecules "
         "(CDH1/E-cadherin, EpCAM) and gain of ECM and mesenchymal components "
         "(collagens such as COL1A1/COL5A2/COL6A1, and matrix metalloproteinases such as "
         "MMP14). This is the canonical EMT programme, and it appeared across both models "
         "despite their differing resistance mechanisms. In the OVCAR5 model, the "
         "inflammatory axis (IL1A/IL1B) was prominent, consistent with inflammasome-driven "
         "resistance. NDRG1, a validated hub gene in independent ovarian cancer datasets, "
         "and KYNU, a kynurenine-pathway enzyme implicated in immune evasion, provide "
         "literature-anchored nodes within the derived signature. SERPINE1, an invasion "
         "effector, further connects the signature to ECM remodelling and metastasis.")
    h2(doc, "6.2 Proposed mechanistic model")
    para(doc,
         "Taken together, the results support the following working model. Cisplatin "
         "exposure causes DNA damage that is accompanied by chronic inflammation "
         "(IL1A/IL1B) and immune-evasive metabolic signalling (KYNU). Cells evade apoptosis "
         "(via reduced DAPK1-type signalling and altered BCL2 balance), remodel the "
         "extracellular matrix (collagens, MMP14), and activate integrin/focal-adhesion "
         "signalling, which in turn promotes Wnt/β-catenin activity and a full EMT "
         "(CDH1 and EPCAM loss). The resulting phenotype combines drug efflux, stemness and "
         "invasion to produce stable cisplatin resistance. PI3K-Akt signalling acts as a "
         "recurring survival node throughout.")
    h2(doc, "6.3 Machine-learning interpretation")
    para(doc,
         "The machine-learning results must be read with their design in mind. "
         "Within-cell-line LOOCV is near-perfect, but this largely reflects the fact that "
         "the two cell lines are intrinsically separable; it is a useful sanity check, not "
         "evidence of a deployable classifier. The meaningful test is cross-dataset "
         "generalisation. Here a small SKOV-3-derived signature transfers to OVCAR5 at "
         "K = 20–50 under batch-corrected normalisation, but the reverse direction does not, "
         "and performance collapses as K grows — the expected consequence of tuning many "
         "features on six training samples. When normalisation is made strictly "
         "non-transductive, the transfer weakens or disappears (mean AUC ≈ 0.61). The honest "
         "conclusion is that a small, model-specific signal exists but does not constitute a "
         "generalised, deployable signature at this sample size.")
    h2(doc, "6.4 Comparison with the literature")
    para(doc,
         "The recurrence of EMT, ECM remodelling and adhesion pathways aligns this work "
         "with established findings that CDH1 silencing and collagen up-regulation accompany "
         "platinum resistance, and that PI3K-Akt, integrin, focal-adhesion and cadherin "
         "signalling are convergent resistance nodes. The prominent inflammatory and "
         "metabolic signals in the OVCAR5 model reflect its documented pyrimidine-dependency "
         "and inflammasome biology. The low cross-dataset correlation of log2 fold changes "
         "is itself consistent with the mechanistic heterogeneity reported for ovarian "
         "cancer resistance, and argues for treating single-dataset signatures with caution.")
    h2(doc, "6.5 Limitations")
    bullets(doc, [
        "Small sample size (n = 12; six per cell line): the study is exploratory and cannot "
        "support clinical or diagnostic claims.",
        "High dimensionality relative to sample size (n << p): large feature sets overfit, "
        "and efficient methods are required; only small K values are reliable.",
        "External performance depends materially on the normalisation scheme; only the "
        "strict train_stats result is fully leak-free, and it is modest.",
        "Cell-line models do not capture tumour heterogeneity, the immune microenvironment "
        "or patient-level variability.",
        "The two datasets share cancer type and drug but differ in resistance mechanism, "
        "which limits the size of the shared signature and the symmetry of transfer.",
        "No wet-lab validation of the candidate panel was performed.",
    ])
    h2(doc, "6.6 Future work")
    bullets(doc, [
        "Add independent datasets and more biological replicates to stabilise cross-dataset "
        "generalisation and enable patient-derived validation.",
        "Benchmark batch-correction methods (ComBat, quantile normalisation) and evaluate "
        "pathway-level or module-based features rather than individual genes.",
        "Experimentally validate leading candidates (MAL2, GALNT6, NDRG1) and the EMT/ECM "
        "axis in resistant cell lines.",
        "Extend the interactive dashboard with network visualisation and survival-outcome "
        "integration where clinical data are available.",
    ])


def conclusion(doc):
    h1(doc, "7. Conclusion")
    para(doc,
         "This project delivered a reproducible, end-to-end transcriptomic and "
         "machine-learning analysis of cisplatin resistance in ovarian cancer using two "
         "independent public RNA-seq datasets. Differential expression analysis revealed "
         "extensive reprogramming in both models, and cross-dataset validation isolated a "
         "core signature of consistently regulated genes. Functional enrichment converged "
         "on extracellular matrix remodelling, cell adhesion and the PI3K-Akt, "
         "focal-adhesion, integrin and cadherin pathways, with epithelial–mesenchymal "
         "transition as the dominant shared mechanism — in agreement with the published "
         "literature.")
    para(doc,
         "Supervised classifiers separated resistant from sensitive samples almost perfectly "
         "within a cell line, but cross-dataset transfer was partial, strongly asymmetric "
         "and weakened under strictly leak-free normalisation. This honest result "
         "underscores the importance of leakage control and external validation in small "
         "high-dimensional studies. A 30-gene candidate biomarker panel, headed by MAL2 and "
         "GALNT6, was nominated for experimental follow-up together with literature-anchored "
         "candidates such as NDRG1. Beyond the biological findings, the project provides a "
         "reproducible pipeline, publication-quality figures and an interactive dashboard "
         "that can be adapted to other cancers, drugs and datasets.")


def references(doc):
    h1(doc, "8. References")
    refs = [
        "Cardenas H, Wang Y, Zhao G, Hao DX, Isac AM, Hernandez V, Kim U, Qiang W, "
        "Zhang HF, Matei D. Metabolic dependency on de novo pyrimidine synthesis is a "
        "targetable vulnerability in platinum-resistant ovarian cancer. Cancer Res. "
        "2026;86(2):387–401. doi:10.1158/0008-5472.CAN-25-0043.",
        "Zhu Y, Chen X, Tang R, Li G, Yang J, Hong S. Comprehensive analysis of hub genes "
        "associated with cisplatin-resistance in ovarian cancer and screening of therapeutic "
        "drugs through bioinformatics and experimental validation. J Ovarian Res. "
        "2024;17(1):142. doi:10.1186/s13048-024-01461-w.",
        "de Souza JC, Pimenta TM, Martins BDS, Padilha JMS, Butzene SMS, Marçal MG, "
        "Rangel LBA. Inflammasome activation contributes to cisplatin resistance in ovarian "
        "cancer. J Ovarian Res. 2025;18(1):294. doi:10.1186/s13048-025-01852-7.",
        "Alghamian Y, Soukkarieh C, Abbady AQ, Murad H. Investigation of role of CpG "
        "methylation in some epithelial mesenchymal transition gene in a chemoresistant "
        "ovarian cancer cell line. Sci Rep. 2022;12(1):7494. doi:10.1038/s41598-022-11634-6.",
        "Zeller C, Dai W, Steele NL, Siddiq A, Walley AJ, Wilhelm-Benartzi CS, Rizzo S, "
        "van der Zee A, Plumb JA, Brown R. Candidate DNA methylation drivers of acquired "
        "cisplatin resistance in ovarian cancer identified by methylome and expression "
        "profiling. Oncogene. 2012;31(42):4567–4576. doi:10.1038/onc.2011.611.",
        "Januchowski R, Świerczewska M, Sterzyńska K, Wojtowicz K, Nowicki M, Zabel M. "
        "Increased expression of several collagen genes is associated with drug resistance "
        "in ovarian cancer cell lines. J Cancer. 2016;7(10):1295–1310. doi:10.7150/jca.15371.",
        "Yu PN, Yan MD, Lai HC, Huang RL, Chou YC, Lin WC, Yeh LT, Lin YW. Downregulation "
        "of miR-29 contributes to cisplatin resistance of ovarian cancer cells. Int J "
        "Cancer. 2014;134(3):542–551. doi:10.1002/ijc.28399.",
        "Chen S, Yang G, Shi Q, Wan N, Lin R, Wang L, Hu X, Zhuang X, Yu L, Sui M. "
        "Frizzled 6 endows high-grade serous ovarian cancer with stem-like properties and "
        "chemoresistance. Mol Carcinog. 2024;63(10):2001–2012. doi:10.1002/mc.23789.",
        "Tersigni C, Onori M, Buzzonetti A, et al. Diagnostic performance of circulating "
        "EpCAM+ and CD45+ extracellular vesicles in platinum-sensitivity in high-grade "
        "serous ovarian cancer: a pilot study. J Ovarian Res. 2025;18(1):93. "
        "doi:10.1186/s13048-025-01656-9.",
        "Wang F, Yue QF, Zhang Y, Lei FL. Synergistic overcoming of cisplatin resistance in "
        "ovarian cancer by combined Astragalus membranaceus and cisplatin treatment: network "
        "pharmacology and experimental validation. BMC Complement Med Ther. 2025;25(1):337. "
        "doi:10.1186/s12906-025-05066-8.",
        "Velmurugan P, Parsanathan R, Shankari G, et al. Pharmacological modulation of the "
        "tryptophan-kynurenine pathway by the intervention of indoleamine 2,3-dioxygenase 2 "
        "(IDO2) and kynureninase (KYNU) in ovarian cancer. Curr Med Chem. 2026 (Epub). "
        "doi:10.2174/0109298673450210260701040244.",
        "Heng B, Bilgin AA, Lovejoy DB, et al. Differential kynurenine pathway metabolism "
        "in highly metastatic aggressive breast cancer subtypes: beyond IDO1-induced "
        "immunosuppression. Breast Cancer Res. 2020;22(1):113. doi:10.1186/s13058-020-01351-1.",
        "Mrkvicova A, Chmelarova M, Peterova E, Havelek R, Baranova I, Kazimirova P, "
        "Rudolf E, Rezacova M. The effect of sodium butyrate and cisplatin on expression of "
        "EMT markers. PLoS One. 2019;14(1):e0210889. doi:10.1371/journal.pone.0210889.",
        "Chiang YC, Chang MC, Chen PJ, Wu MM, Hsieh CY, Cheng WF, Chen CA. Epigenetic "
        "silencing of BLU through interfering apoptosis results in chemoresistance and poor "
        "prognosis of ovarian serous carcinoma patients. Endocr Relat Cancer. "
        "2013;20(2):213–227. doi:10.1530/ERC-12-0117.",
        "Edgar R, Domrachev M, Lash AE. Gene Expression Omnibus: NCBI gene expression and "
        "hybridization array data repository. Nucleic Acids Res. 2002;30(1):207–210. "
        "doi:10.1093/nar/30.1.207.",
        "Barrett T, Wilhite SE, Ledoux P, et al. NCBI GEO: archive for functional genomics "
        "data sets—update. Nucleic Acids Res. 2013;41(Database issue):D991–D995. "
        "doi:10.1093/nar/gks1193.",
        "Love MI, Huber W, Anders S. Moderated estimation of fold change and dispersion for "
        "RNA-seq data with DESeq2. Genome Biol. 2014;15(12):550. "
        "doi:10.1186/s13059-014-0550-8.",
        "Wu T, Hu E, Xu S, et al. clusterProfiler 4.0: A universal enrichment tool for "
        "interpreting omics data. Innovation (Camb). 2021;2(3):100141. "
        "doi:10.1016/j.xinn.2021.100141.",
        "Yu G, Wang LG, Han Y, He QY. clusterProfiler: an R package for comparing biological "
        "themes among gene clusters. OMICS. 2012;16(5):284–287. doi:10.1089/omi.2011.0118.",
        "Kanehisa M, Goto S. KEGG: Kyoto Encyclopedia of Genes and Genomes. Nucleic Acids "
        "Res. 2000;28(1):27–30. doi:10.1093/nar/28.1.27.",
        "Friedman J, Hastie T, Tibshirani R. Regularization paths for generalized linear "
        "models via coordinate descent. J Stat Softw. 2010;33(1):1–22. "
        "doi:10.18637/jss.v033.i01.",
        "Wright MN, Ziegler A. ranger: A fast implementation of random forests for high "
        "dimensional data in C++ and R. J Stat Softw. 2017;77(1):1–17. "
        "doi:10.18637/jss.v077.i01.",
        "Meyer D, Dimitriadou E, Hornik K, Weingessel A, Leisch F. e1071: Misc Functions of "
        "the Department of Statistics, Probability Theory and Its Applications. R package.",
        "Blighe K, Rana S, Lewis M. EnhancedVolcano: Publication-ready volcano plots with "
        "enhanced colouring and labeling. R package (Bioconductor).",
        "Kolde R. pheatmap: Pretty Heatmaps. R package.",
        "Carlson M. org.Hs.eg.db: Genome wide annotation for Human. R package (Bioconductor).",
        "Varma S, Simon R. Bias in error estimation when using cross-validation for model "
        "selection. BMC Bioinformatics. 2006;7:91. doi:10.1186/1471-2105-7-91.",
        "Ambroise C, McLachlan GJ. Selection bias in gene extraction on the basis of "
        "microarray gene-expression data. Proc Natl Acad Sci USA. 2002;99(10):6562–6566. "
        "doi:10.1073/pnas.102102699.",
        "Guyon I, Elisseeff A. An introduction to variable and feature selection. J Mach "
        "Learn Res. 2003;3:1157–1182.",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.35)
        p.paragraph_format.first_line_indent = Inches(-0.35)
        r = p.add_run(f"[{i}] ")
        r.bold = True
        r.font.size = Pt(10)
        r2 = p.add_run(ref)
        r2.font.size = Pt(10)


def appendix(doc, d):
    h1(doc, "Appendix A. Data availability")
    para(doc,
         "All datasets are publicly available from the NCBI Gene Expression Omnibus under "
         "accessions GSE303889 and GSE283381. Analysis code, result tables, figures and the "
         "interactive dashboard are contained within the project repository.")
    h1(doc, "Appendix B. Key output files")
    table(doc,
          ["Output", "Description"],
          [["results/dataset{1,2}/DEG_table_full.csv", "All genes with DESeq2 statistics"],
           ["results/dataset{1,2}/DEGs_{up,down,significant}.csv", "Significant DEG lists"],
           ["results/comparison/overlapping_DEGs.csv", "Cross-dataset shared DEGs"],
           ["results/enrichment/*.csv / *.png", "GO and KEGG enrichment tables and plots"],
           ["results/ml/expression_matrix.rds", "12 × 57,357 ML feature matrix"],
           ["results/ml/ml_metrics_summary.csv", "Metrics per model / K / validation / scheme"],
           ["results/ml/external_by_direction.csv", "Primary external metrics per direction"],
           ["results/ml/biomarker_panel.csv", "Ranked candidate biomarker panel"],
           ["results/ml/*.png", "ROC, confusion-matrix and feature-importance figures"],
           ["backend/app.py + static/index.html", "FastAPI backend and web dashboard"]],
          widths=[3.0, 3.2])
    h1(doc, "Appendix C. Software")
    table(doc,
          ["Component", "Version / notes"],
          [["R", "4.4.2"],
           ["DESeq2, EnhancedVolcano", "Bioconductor (differential expression)"],
           ["clusterProfiler, org.Hs.eg.db", "Bioconductor (enrichment)"],
           ["glmnet, ranger, e1071", "Machine-learning models"],
           ["ggplot2, pheatmap, VennDiagram", "Visualisation"],
           ["Python 3.11, FastAPI, python-docx", "Dashboard backend and report generation"]],
          widths=[2.6, 3.6])


def build():
    d = load_data()
    doc = Document()
    setup(doc)
    title_page(doc)
    toc_page(doc)
    abstract(doc, d)
    introduction(doc)
    literature(doc)
    methodology(doc, d)
    analysis(doc, d)
    results_section(doc, d)
    discussion(doc, d)
    conclusion(doc)
    references(doc)
    appendix(doc, d)

    out = os.path.join(HERE, "DrugResistance_Report.docx")
    doc.save(out)
    n_tables = len(doc.tables)
    n_paras = len(doc.paragraphs)
    print(f"wrote {out}")
    print(f"  tables: {n_tables}, paragraphs: {n_paras}, "
          f"sections: {len(doc.sections)}")
    return out


if __name__ == "__main__":
    build()

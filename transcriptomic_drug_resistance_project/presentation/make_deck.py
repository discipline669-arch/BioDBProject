"""Generate the project presentation (.pptx) from results/ artefacts.

Mirrors presentation/full_deck.bas and condensed_deck.bas.

Run:  python presentation/make_deck.py
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Pt
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)

NAVY = RGBColor(0x1F, 0x38, 0x64)
TEAL = RGBColor(0x2E, 0x9C, 0xCA)
GRAY = RGBColor(0x40, 0x40, 0x40)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF0, 0xF4, 0xF8)
FADED = RGBColor(0x82, 0x8A, 0x96)

SLIDE_W, SLIDE_H = 960, 540


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def _rect(slide, shape, x, y, w, h, fill):
    sh = slide.shapes.add_shape(shape, Pt(x), Pt(y), Pt(w), Pt(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def _text(slide, x, y, w, h, text, size, color, bold=False,
          align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Pt(x), Pt(y), Pt(w), Pt(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    for run in p.runs:
        run.font.size = Pt(size)
        run.font.name = "Calibri"
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def _header(slide, title, idx):
    _rect(slide, MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, 76, NAVY)
    _rect(slide, MSO_SHAPE.RECTANGLE, 0, 76, SLIDE_W, 5, TEAL)
    _text(slide, 30, 10, 900, 58, title, 26, WHITE, bold=True)
    _rect(slide, MSO_SHAPE.RECTANGLE, 30, 512, 900, 1, RGBColor(0xD2, 0xD7, 0xDE))
    _text(slide, 30, 513, 720, 22,
          "Transcriptomic Profiling of Drug-Resistant Cancer Cells", 10, FADED)
    _text(slide, 890, 513, 40, 22, str(idx), 10, FADED, align=PP_ALIGN.RIGHT)


def _bullets(slide, items, left, top, width, height):
    tb = slide.shapes.add_textbox(Pt(left), Pt(top), Pt(width), Pt(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (text, level) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text
        p.level = level
        p.space_after = Pt(6)
        for run in p.runs:
            run.font.size = Pt(17 if level == 0 else 15)
            run.font.name = "Calibri"
            run.font.color.rgb = GRAY if level == 0 else RGBColor(0x50, 0x50, 0x50)
    return tb


def _image(slide, rel, left, top, max_w, max_h):
    path = os.path.join(PROJ, rel)
    if not os.path.exists(path):
        print("  [skip missing image]", rel)
        return
    w, h = Image.open(path).size
    scale = min(max_w / w, max_h / h)
    slide.shapes.add_picture(path, Pt(left), Pt(top),
                             width=Pt(w * scale), height=Pt(h * scale))


def _notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def _title_slide(pres, title, subtitle, team):
    s = pres.slides.add_slide(pres.slide_layouts[6])
    _rect(s, MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H, NAVY)
    _rect(s, MSO_SHAPE.RECTANGLE, 70, 300, 820, 6, TEAL)
    _text(s, 70, 170, 820, 120, title, 38, WHITE, bold=True)
    _text(s, 70, 318, 820, 80, subtitle, 18, RGBColor(0xD2, 0xE0, 0xF0))
    _text(s, 70, 440, 820, 40, team, 14, RGBColor(0xA0, 0xBE, 0xDC))
    return s


def _thanks_slide(pres):
    s = pres.slides.add_slide(pres.slide_layouts[6])
    _rect(s, MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H, NAVY)
    _text(s, 0, 210, SLIDE_W, 70, "Thank You", 44, WHITE, bold=True,
          align=PP_ALIGN.CENTER)
    _text(s, 0, 290, SLIDE_W, 40, "Questions?", 22, TEAL, align=PP_ALIGN.CENTER)
    return s


def _content_slide(pres, title, idx):
    s = pres.slides.add_slide(pres.slide_layouts[6])
    _header(s, title, idx)
    return s


def _dataset_table(slide, left=60, top=120, width=840, height=250):
    data = [
        ["Attribute", "GSE303889", "GSE283381"],
        ["Cell line", "SKOV-3", "OVCAR5"],
        ["Resistance model", "CDDP (chronic cisplatin)", "Cis-R (repeated cisplatin)"],
        ["Design", "3 Sensitive vs 3 Resistant", "3 Sensitive vs 3 Resistant"],
        ["Platform", "Illumina NovaSeq 6000", "Illumina NextSeq 500"],
    ]
    gf = slide.shapes.add_table(len(data), 3, Pt(left), Pt(top), Pt(width), Pt(height))
    tbl = gf.table
    for r, row in enumerate(data):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            para = cell.text_frame.paragraphs[0]
            for run in para.runs:
                run.font.size = Pt(15)
                run.font.name = "Calibri"
                run.font.color.rgb = WHITE if r == 0 else GRAY
                run.font.bold = (r == 0) or (c == 0 and r > 0)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if r == 0 else (LIGHT if r % 2 == 0 else WHITE)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE


def _workflow(slide):
    y1, y2, bw, bh = 140, 340, 240, 80
    boxes = [
        ("GEO datasets\n(2 studies)", 50, y1),
        ("Preprocess\n& QC", 350, y1),
        ("DESeq2\nper dataset", 650, y1),
        ("Cross-dataset\nvalidation", 50, y2),
        ("GO / KEGG\nenrichment", 350, y2),
        ("ML biomarker\ndiscovery", 650, y2),
    ]
    for text, x, y in boxes:
        sh = _rect(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, bw, bh, TEAL)
        tf = sh.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = text
        p.alignment = PP_ALIGN.CENTER
        for run in p.runs:
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.name = "Calibri"
            run.font.color.rgb = WHITE
    _rect(slide, MSO_SHAPE.RIGHT_ARROW, 295, 162, 40, 36, NAVY)
    _rect(slide, MSO_SHAPE.RIGHT_ARROW, 595, 162, 40, 36, NAVY)
    _rect(slide, MSO_SHAPE.DOWN_ARROW, 750, 225, 36, 40, NAVY)
    _rect(slide, MSO_SHAPE.RIGHT_ARROW, 295, 362, 40, 36, NAVY)
    _rect(slide, MSO_SHAPE.RIGHT_ARROW, 595, 362, 40, 36, NAVY)


# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------
FULL = [
    ("bullets", "Outline", [
        ("•  Background & Objectives", 0),
        ("•  Data & Methods", 0),
        ("•  Differential Expression Analysis", 0),
        ("•  Cross-Dataset Validation", 0),
        ("•  Functional Enrichment (GO / KEGG)", 0),
        ("•  Machine Learning & Biomarker Discovery", 0),
        ("•  Key Findings, Limitations & Conclusions", 0),
    ], 60, 130, 840, 340, None),
    ("bullets", "Background: Ovarian Cancer & Cisplatin Resistance", [
        ("•  Ovarian cancer is the most lethal gynaecologic malignancy; platinum-based chemotherapy (cisplatin) is first-line.", 0),
        ("•  Acquired platinum resistance underlies relapse and poor survival.", 0),
        ("•  Resistance is multifactorial: epigenetic reprogramming, metabolic rewiring, EMT, drug efflux, apoptotic evasion.", 0),
        ("•  Need reproducible transcriptomic signatures that generalise across independent resistance models.", 0),
    ], 60, 125, 840, 360, None),
    ("bullets", "Objectives & Scope", [
        ("•  Identify differentially expressed genes (DEGs) between cisplatin-resistant and sensitive ovarian cancer cells.", 0),
        ("•  Validate DEGs across two independent GEO datasets to reduce dataset-specific bias.", 0),
        ("•  Characterise the affected biological processes and signalling pathways (GO / KEGG).", 0),
        ("•  Build supervised classifiers and rank a compact candidate biomarker panel.", 0),
        ("•  Deliver a fully reproducible end-to-end bioinformatics + ML pipeline.", 0),
    ], 60, 125, 840, 360,
     "Scope is exploratory biomarker discovery, not clinical validation (small n)."),
    ("table", "Data: Two Independent GEO Datasets", None, None, None, None, None,
     "GSE303889 (SKOV-3, Yonsei, KDM5-mediated) and GSE283381 (OVCAR5, Northwestern, pyrimidine metabolism). 3 vs 3 replicates each, n=12."),
    ("workflow", "Analytical Workflow", None, None, None, None, None,
     "GEO -> preprocess/QC -> DESeq2 per dataset -> cross-dataset validation -> parallel GO/KEGG and ML -> final panel."),
    ("bullets", "Preprocessing & Quality Control", [
        ("•  Raw gene count matrices + sample metadata retrieved from NCBI GEO (2 datasets).", 0),
        ("•  Low-count filtering: retained genes with rowSums >= 10.", 0),
        ("•  DESeq2 size-factor normalisation; log2(CPM + 1) transform.", 0),
        ("•  Duplicate gene symbols collapsed (rowsum); intersect -> 57,357 shared genes.", 0),
        ("•  PCA and sample-clustering QC (seed 42 for reproducibility).", 0),
    ], 60, 125, 840, 360, None),
    ("bullets", "Differential Expression (DESeq2)", [
        ("•  Design: ~ condition; negative-binomial GLM, Wald test.", 0),
        ("•  Multiple testing: Benjamini-Hochberg FDR.", 0),
        ("•  Significance thresholds: FDR < 0.05  AND  |log2 fold change| > 1.", 0),
        ("•  Outputs per dataset: full DEG table, up/down lists, volcano, MA plot, top-DEG heatmap.", 0),
        ("•  Reference level = Sensitive; contrast = Resistant vs Sensitive.", 0),
    ], 60, 125, 840, 360, None),
    ("bullets", "Dataset 1 (SKOV-3 / GSE303889) — DEG Results", [
        ("•  GSE303889: SKOV-3 parental vs KDM5-mediated CDDP-resistant cells.", 0),
        ("•  Total significant DEGs: 5,212", 0),
        ("-  Up-regulated:  2,983", 1),
        ("-  Down-regulated: 2,229", 1),
        ("•  Extensive transcriptomic reprogramming on resistance acquisition.", 0),
        ("•  Top down-regulated genes include CDH1 (E-cadherin) — EMT signal.", 0),
    ], 40, 120, 430, 370, None,
     "imgs", [("results/dataset1/volcano_plot.png", 500, 110, 430, 390)]),
    ("bullets", "Dataset 2 (OVCAR5 / GSE283381) — DEG Results", [
        ("•  GSE283381: OVCAR5 cisplatin-sensitive (Cis-S) vs resistant (Cis-R).", 0),
        ("•  Total significant DEGs: 2,572", 0),
        ("-  Up-regulated:    912", 1),
        ("-  Down-regulated: 1,660", 1),
        ("•  Up-regulated inflammatory / ECM genes (IL1A, IL1B, COL genes).", 0),
        ("•  Distinct resistance mechanism vs Dataset 1.", 0),
    ], 40, 120, 430, 370, None,
     "imgs", [("results/dataset2/volcano_plot.png", 500, 110, 430, 390)]),
    ("bullets", "Cross-Dataset Validation", [
        ("•  913 genes are differentially expressed in BOTH datasets (core signature).", 0),
        ("-  198 shared up-regulated", 1),
        ("-  220 shared down-regulated", 1),
        ("-  495 with opposite direction (cell-line-specific)", 1),
        ("•  Spearman correlation of shared log2FC ~ -0.04.", 0),
        ("•  Low correlation is expected: distinct resistance mechanisms (epigenetic vs metabolic).", 0),
    ], 40, 120, 430, 370, None,
     "imgs", [("results/comparison/venn_diagram.png", 490, 105, 450, 200),
              ("results/comparison/lfc_correlation.png", 490, 305, 450, 190)]),
    ("bullets", "Functional Enrichment — Gene Ontology", [
        ("•  clusterProfiler enrichGO (BP focus), BH-adjusted, p < 0.05.", 0),
        ("•  Top enriched terms for shared DEGs:", 0),
        ("-  Cell-substrate adhesion", 1),
        ("-  Extracellular matrix organisation", 1),
        ("-  Extracellular structure organisation", 1),
        ("-  Ossification / axon guidance", 1),
        ("•  ECM and adhesion processes dominate — hallmark of EMT.", 0),
    ], 40, 120, 430, 370, None,
     "imgs", [("results/enrichment/GO_dotplot_Shared_DEGs.png", 490, 100, 450, 400)]),
    ("bullets", "Functional Enrichment — KEGG Pathways", [
        ("•  enrichKEGG (hsa), BH-adjusted, p < 0.05.", 0),
        ("•  Convergent pathways in shared DEGs:", 0),
        ("-  PI3K-Akt signalling", 1),
        ("-  Focal adhesion / Integrin signalling", 1),
        ("-  Cadherin signalling", 1),
        ("-  Cytoskeleton / ECM-receptor interaction", 1),
        ("-  Hippo signalling pathway", 1),
        ("•  Survival, adhesion and cytoskeletal remodelling converge on resistance.", 0),
    ], 40, 120, 430, 370, None,
     "imgs", [("results/enrichment/KEGG_dotplot_Shared_DEGs.png", 490, 100, 450, 400)]),
    ("bullets", "Biological Model of Cisplatin Resistance", [
        ("•  EMT (central): CDH1 down, EPCAM down, COL1A1/COL5A2/COL6A1 up, MMP14/MMP1 up.", 0),
        ("•  Inflammation: IL1A up / IL1B up (NLRP3 inflammasome).", 0),
        ("•  NDRG1 up — validated hub gene across 3 independent OC datasets.", 0),
        ("•  KYNU up — kynurenine/AhR axis driving immune evasion.", 0),
        ("•  SERPINE1 up — metastasis & resistance effector.", 0),
        ("Cisplatin -> DNA damage -> inflammation -> apoptosis evasion + ECM remodelling -> integrin/focal adhesion -> EMT -> RESISTANCE", 0),
    ], 60, 120, 840, 380,
     "Literature-supported: Wani 2025, Ghosh 2022, Li 2021, Zhu 2024, J Ovarian Res 2025."),
    ("bullets", "Machine Learning: Design & Leakage Control", [
        ("•  Feature space: full intersected matrix (12 samples x 57,357 genes), log2(CPM+1).", 0),
        ("•  Models: Logistic Regression (ridge/L2), Random Forest (ranger), SVM (radial).", 0),
        ("•  Nested feature selection: top-K by |t-statistic|, K in {20,50,100,200,500} — inside each training fold only.", 0),
        ("•  Fold-aware normalisation; two external schemes:", 0),
        ("-  target_z (transductive, batch-corrected)", 1),
        ("-  train_stats (strictly non-transductive, leak-free)", 1),
        ("•  Validation: within-cell-line LOOCV + leave-one-dataset-out external.", 0),
    ], 60, 120, 840, 380,
     "No DEG pre-filtering: avoids test leakage. Deterministic via fixed seeds."),
    ("bullets", "Within-Cell-Line LOOCV", [
        ("•  Leave-one-out inside each cell line (5 train / 1 test per fold).", 0),
        ("•  Preprocessing + feature selection recomputed per fold.", 0),
        ("•  Accuracy 0.833 - 1.000  |  ROC-AUC 0.889 - 1.000.", 0),
        ("•  Phenotypes are almost trivially separable within a cell line.", 0),
        ("•  Likely optimistic: reflects within-study (batch) separation.", 0),
    ], 40, 125, 430, 360, None,
     "imgs", [("results/ml/ROC_LOOCV.png", 490, 105, 450, 390)]),
    ("bullets", "Cross-Dataset External Validation", [
        ("•  Train on one cell line (6), predict the other (6).", 0),
        ("•  target_z (batch-corrected):", 0),
        ("-  SKOV3 -> OVCAR5: AUC 1.0 at K = 20-50", 1),
        ("-  OVCAR5 -> SKOV3: AUC ~ 0.44 - 0.78 (near chance)", 1),
        ("•  train_stats (leak-free, strict): mean ROC-AUC ~ 0.61.", 0),
        ("•  Transfer is partial and strongly asymmetric; signal collapses as K grows (n << p).", 0),
    ], 40, 120, 430, 375, None,
     "imgs", [("results/ml/ROC_external.png", 490, 105, 450, 200),
              ("results/ml/ROC_external_trainstats.png", 490, 300, 450, 195)]),
    ("bullets", "Candidate Biomarker Panel", [
        ("•  Ranked by cross-dataset selection frequency across models x K.", 0),
        ("•  Top candidates: MAL2, GALNT6, LDOC1, SH2D4A, FBXL21P,", 0),
        ("-  EPB41L3, TMEM218, CALB1, LINC02582, CELF2 ...", 1),
        ("•  30-gene exploratory panel (biomarker_panel.csv).", 0),
        ("•  Reflects the SKOV3->OVCAR5 direction; candidates for follow-up.", 0),
        ("•  NOT a clinically validated diagnostic panel.", 0),
    ], 40, 120, 430, 375, None,
     "imgs", [("results/ml/feature_importance.png", 490, 100, 450, 400)]),
    ("bullets", "Interactive Results Dashboard", [
        ("•  FastAPI backend (backend/app.py) serving the ML artifacts as a read-only REST API.", 0),
        ("•  Endpoints: /api/summary, /api/external, /api/metrics, /api/loocv,", 0),
        ("-  /api/predictions/external, /api/biomarkers, /api/feature-importance", 1),
        ("•  Web dashboard with a normalisation toggle (target_z / train_stats),", 0),
        ("-  AUC-by-K chart, external metrics table and prediction explorer", 1),
        ("•  Run:  python backend/app.py  ->  http://127.0.0.1:8000/", 0),
    ], 60, 125, 840, 360, None),
    ("bullets", "Key Findings", [
        ("•  Extensive transcriptomic reprogramming: 5,212 DEGs (SKOV-3) and 2,572 (OVCAR5).", 0),
        ("•  913 shared DEGs form a cross-dataset core cisplatin-resistance signature.", 0),
        ("•  EMT and ECM remodelling are the dominant shared mechanism.", 0),
        ("•  PI3K-Akt, focal adhesion, integrin and cadherin pathways converge on resistance.", 0),
        ("•  ML separates phenotypes within a cell line; cross-dataset transfer is partial and asymmetric.", 0),
        ("•  A 30-gene candidate panel (MAL2, GALNT6, ...) nominated for follow-up.", 0),
    ], 60, 120, 840, 380, None),
    ("bullets", "Limitations & Caveats", [
        ("•  Small sample size (n = 12; 6 per cell line) — exploratory, not clinical validation.", 0),
        ("•  n << p: large-K feature sets overfit; small K is required.", 0),
        ("•  Cross-dataset normalisation choice materially changes external results.", 0),
        ("•  Only the train_stats scheme is fully leak-free (mean AUC ~ 0.61).", 0),
        ("•  Two datasets share cancer type/drug but differ in resistance mechanism.", 0),
    ], 60, 125, 840, 360, None),
    ("bullets", "Conclusions & Future Work", [
        ("•  A reproducible end-to-end pipeline: GEO -> DESeq2 -> cross-validation -> GO/KEGG -> ML.", 0),
        ("•  Defines a core cisplatin-resistance transcriptomic signature with clear EMT/ECM biology.", 0),
        ("•  Provides an interactive dashboard and a candidate biomarker panel.", 0),
        ("Future work:", 0),
        ("-  Add independent datasets / more replicates to stabilise cross-dataset generalisation.", 1),
        ("-  Batch-correction benchmarking (ComBat, quantile) and pathway-level ML features.", 1),
        ("-  Experimental validation of MAL2, GALNT6, NDRG1 and the EMT axis.", 1),
    ], 60, 120, 840, 380, None),
]

CONDENSED = [
    ("bullets", "Background & Objectives", [
        ("•  Ovarian cancer: platinum (cisplatin) is first-line; acquired resistance drives relapse.", 0),
        ("•  Resistance is multifactorial (epigenetic, metabolic, EMT, efflux, apoptosis evasion).", 0),
        ("Objectives", 0),
        ("•  Identify DEGs between resistant and sensitive ovarian cancer cells.", 0),
        ("•  Validate DEGs across two independent GEO datasets.", 0),
        ("•  Characterise affected GO / KEGG pathways.", 0),
        ("•  Build ML classifiers and rank a candidate biomarker panel.", 0),
    ], 60, 120, 840, 380, None),
    ("table", "Data: Two Independent GEO Datasets", None, None, None, None, None, None),
    ("workflow", "Analytical Workflow", None, None, None, None, None, None),
    ("bullets", "Differential Expression Results", [
        ("•  DESeq2, FDR < 0.05 and |log2FC| > 1 (Design ~ condition).", 0),
        ("•  SKOV-3 (GSE303889): 5,212 DEGs (2,983 up / 2,229 down).", 0),
        ("•  OVCAR5 (GSE283381): 2,572 DEGs (912 up / 1,660 down).", 0),
        ("•  913 genes shared by both datasets (198 up / 220 down / 495 opposite).", 0),
        ("•  Extensive, dataset-specific reprogramming; low shared log2FC correlation (~ -0.04).", 0),
    ], 40, 120, 430, 375, None,
     "imgs", [("results/dataset1/volcano_plot.png", 490, 105, 450, 200),
              ("results/dataset2/volcano_plot.png", 490, 305, 450, 190)]),
    ("bullets", "Cross-Dataset Validation", [
        ("•  913 shared DEGs = core cross-dataset cisplatin-resistance signature.", 0),
        ("•  Distinct resistance mechanisms (KDM5 epigenetic vs pyrimidine metabolism).", 0),
        ("•  Shared signature highlights EMT / ECM biology.", 0),
        ("•  Consistently regulated genes = higher-confidence candidates.", 0),
    ], 40, 120, 400, 370, None,
     "imgs", [("results/comparison/venn_diagram.png", 460, 105, 480, 210),
              ("results/comparison/lfc_correlation.png", 460, 310, 480, 185)]),
    ("bullets", "Functional Enrichment (GO / KEGG)", [
        ("GO (shared DEGs):", 0),
        ("-  Cell-substrate adhesion", 1),
        ("-  Extracellular matrix organisation", 1),
        ("-  Extracellular structure organisation", 1),
        ("KEGG (shared DEGs):", 0),
        ("-  PI3K-Akt signalling", 1),
        ("-  Focal adhesion / Integrin signalling", 1),
        ("-  Cadherin signalling", 1),
        ("-  Cytoskeleton / ECM-receptor interaction", 1),
    ], 40, 115, 400, 380, None,
     "imgs", [("results/enrichment/GO_dotplot_Shared_DEGs.png", 430, 95, 260, 390),
              ("results/enrichment/KEGG_dotplot_Shared_DEGs.png", 700, 95, 260, 390)]),
    ("bullets", "Biological Model of Resistance", [
        ("•  EMT (central): CDH1 down, EPCAM down, COL1A1/COL5A2/COL6A1 up, MMP14/MMP1 up.", 0),
        ("•  Inflammation: IL1A up / IL1B up (inflammasome).", 0),
        ("•  NDRG1 up — validated hub gene in 3 independent OC datasets.", 0),
        ("•  KYNU up — kynurenine/AhR immune evasion.", 0),
        ("•  SERPINE1 up — metastasis & resistance effector.", 0),
        ("Cisplatin -> DNA damage -> inflammation -> ECM remodelling -> EMT -> RESISTANCE", 0),
    ], 60, 120, 840, 370, None),
    ("bullets", "Machine Learning: Design & Results", [
        ("•  Full 57,357-gene space; LR (ridge), Random Forest, SVM radial.", 0),
        ("•  Nested top-K selection (K in {20,50,100,200,500}) — no test leakage.", 0),
        ("•  Within-cell-line LOOCV: Acc 0.833-1.000, AUC 0.889-1.000.", 0),
        ("•  External (target_z): SKOV3->OVCAR5 AUC 1.0 at K=20-50; reverse ~0.44-0.78.", 0),
        ("•  External (train_stats, leak-free): mean AUC ~0.61.", 0),
        ("•  Transfer is partial and asymmetric (n << p).", 0),
    ], 40, 120, 430, 375, None,
     "imgs", [("results/ml/ROC_LOOCV.png", 490, 105, 450, 200),
              ("results/ml/ROC_external.png", 490, 305, 450, 190)]),
    ("bullets", "Candidate Biomarker Panel", [
        ("•  Ranked by cross-dataset selection frequency (models x K).", 0),
        ("•  Top candidates: MAL2, GALNT6, LDOC1, SH2D4A, FBXL21P,", 0),
        ("-  EPB41L3, TMEM218, CALB1, LINC02582, CELF2 ...", 1),
        ("•  30-gene exploratory panel for follow-up.", 0),
        ("•  NOT a clinically validated diagnostic panel.", 0),
    ], 40, 120, 430, 375, None,
     "imgs", [("results/ml/feature_importance.png", 490, 100, 450, 400)]),
    ("bullets", "Key Findings, Limitations & Conclusions", [
        ("Key findings", 0),
        ("•  913 shared DEGs; EMT and ECM remodelling dominate.", 0),
        ("•  PI3K-Akt, focal adhesion, integrin and cadherin pathways converge.", 0),
        ("•  ML works within a cell line; cross-dataset transfer is partial / asymmetric.", 0),
        ("Limitations", 0),
        ("•  n = 12 (exploratory); n << p; normalisation choice matters.", 0),
        ("Conclusions", 0),
        ("•  Reproducible end-to-end pipeline + dashboard + candidate panel.", 0),
    ], 60, 115, 840, 385, None),
]


def _render(pres, spec, title_slide=True):
    idx = 1
    if title_slide:
        _title_slide(
            pres,
            "Transcriptomic Profiling of Drug-Resistant Cancer Cells",
            "Cisplatin resistance in ovarian cancer: differential expression, pathways & machine-learning biomarkers",
            "Team of 3  |  Data & QC  .  DEGs & Biology  .  ML & Biomarkers",
        )
        idx = 2

    for entry in spec:
        kind = entry[0]
        if kind == "table":
            _, title = entry[0], entry[1]
            s = _content_slide(pres, title, idx)
            _dataset_table(s)
            if entry[7]:
                _notes(s, entry[7])
        elif kind == "workflow":
            s = _content_slide(pres, entry[1], idx)
            _workflow(s)
            if entry[7]:
                _notes(s, entry[7])
        elif kind == "bullets":
            _, title, items, left, top, width, height = entry[:7]
            notes = entry[7] if len(entry) > 7 else None
            s = _content_slide(pres, title, idx)
            _bullets(s, items, left, top, width, height)
            if len(entry) > 8 and entry[8] == "imgs":
                for rel, l, t, mw, mh in entry[9]:
                    _image(s, rel, l, t, mw, mh)
            if notes:
                _notes(s, notes)
        idx += 1

    _thanks_slide(pres)
    return pres


def _new_pres():
    pres = Presentation()
    pres.slide_width = Pt(SLIDE_W)
    pres.slide_height = Pt(SLIDE_H)
    return pres


def main():
    full = _render(_new_pres(), FULL)
    out_full = os.path.join(HERE, "DrugResistance_Full.pptx")
    full.save(out_full)
    print("wrote", out_full, "(", len(full.slides), "slides )")

    cond = _render(_new_pres(), CONDENSED)
    out_cond = os.path.join(HERE, "DrugResistance_Condensed.pptx")
    cond.save(out_cond)
    print("wrote", out_cond, "(", len(cond.slides), "slides )")


if __name__ == "__main__":
    main()

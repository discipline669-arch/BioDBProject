Attribute VB_Name = "modFullDeck"
Option Explicit

' =====================================================================
'  Transcriptomic Profiling of Drug-Resistant Cancer Cells
'  FULL deck (23 slides, 16:9). Run BuildDeck from the PowerPoint VBE.
'  Adjust PROJ if the project root moves.
' =====================================================================

Const PROJ As String = "E:\BioDBProject\BioDBProject\transcriptomic_drug_resistance_project\"

Dim COL_NAVY As Long, COL_TEAL As Long, COL_GRAY As Long, COL_WHITE As Long, COL_LIGHT As Long

Sub BuildDeck()
    COL_NAVY = RGB(31, 56, 100)
    COL_TEAL = RGB(46, 156, 202)
    COL_GRAY = RGB(64, 64, 64)
    COL_WHITE = RGB(255, 255, 255)
    COL_LIGHT = RGB(240, 244, 248)

    Dim pres As Presentation
    Set pres = Application.Presentations.Add
    pres.PageSetup.SlideWidth = 960
    pres.PageSetup.SlideHeight = 540

    Dim n As Long
    On Error Resume Next
    For n = pres.Slides.Count To 1 Step -1
        pres.Slides(n).Delete
    Next n
    On Error GoTo 0

    Dim s As Slide

    ' ---- 1. Title ----
    Set s = pres.Slides.Add(1, ppLayoutBlank)
    MakeTitleSlide s, _
        "Transcriptomic Profiling of Drug-Resistant Cancer Cells", _
        "Cisplatin resistance in ovarian cancer: differential expression, pathways & machine-learning biomarkers", _
        "Team of 3  |  Data & QC  .  DEGs & Biology  .  ML & Biomarkers"
    AddNotes s, "Final capstone presentation. Two independent cisplatin-resistant vs sensitive ovarian cancer RNA-seq datasets (SKOV-3 and OVCAR5), cross-dataset DEG validation, GO/KEGG enrichment, and supervised ML biomarker discovery."

    ' ---- 2. Outline ----
    Set s = NewC(pres, "Outline")
    AddBullets s, "•  Background & Objectives" & vbCrLf & _
                 "•  Data & Methods" & vbCrLf & _
                 "•  Differential Expression Analysis" & vbCrLf & _
                 "•  Cross-Dataset Validation" & vbCrLf & _
                 "•  Functional Enrichment (GO / KEGG)" & vbCrLf & _
                 "•  Machine Learning & Biomarker Discovery" & vbCrLf & _
                 "•  Key Findings, Limitations & Conclusions", 60, 130, 840, 340

    ' ---- 3. Background ----
    Set s = NewC(pres, "Background: Ovarian Cancer & Cisplatin Resistance")
    AddBullets s, _
        "•  Ovarian cancer is the most lethal gynaecologic malignancy; platinum-based chemotherapy (cisplatin) is first-line." & vbCrLf & vbCrLf & _
        "•  Acquired platinum resistance underlies relapse and poor survival." & vbCrLf & vbCrLf & _
        "•  Resistance is multifactorial: epigenetic reprogramming, metabolic rewiring, EMT, drug efflux, apoptotic evasion." & vbCrLf & vbCrLf & _
        "•  Need reproducible transcriptomic signatures that generalise across independent resistance models.", _
        60, 125, 840, 360

    ' ---- 4. Objectives ----
    Set s = NewC(pres, "Objectives & Scope")
    AddBullets s, _
        "•  Identify differentially expressed genes (DEGs) between cisplatin-resistant and sensitive ovarian cancer cells." & vbCrLf & _
        "•  Validate DEGs across two independent GEO datasets to reduce dataset-specific bias." & vbCrLf & _
        "•  Characterise the affected biological processes and signalling pathways (GO / KEGG)." & vbCrLf & _
        "•  Build supervised classifiers and rank a compact candidate biomarker panel." & vbCrLf & _
        "•  Deliver a fully reproducible end-to-end bioinformatics + ML pipeline.", _
        60, 125, 840, 360
    AddNotes s, "Scope is exploratory biomarker discovery, not clinical validation (small n)."

    ' ---- 5. Datasets table ----
    Set s = NewC(pres, "Data: Two Independent GEO Datasets")
    BuildDatasetTable s
    AddNotes s, "GSE303889 (SKOV-3, Yonsei, KDM5-mediated resistance) and GSE283381 (OVCAR5, Northwestern, pyrimidine metabolism). 3 vs 3 replicates each, n=12 total."

    ' ---- 6. Workflow ----
    Set s = NewC(pres, "Analytical Workflow")
    BuildWorkflow s
    AddNotes s, "GEO -> preprocess/QC -> DESeq2 per dataset -> cross-dataset validation -> parallel GO/KEGG and ML -> final biomarker panel."

    ' ---- 7. Preprocessing ----
    Set s = NewC(pres, "Preprocessing & Quality Control")
    AddBullets s, _
        "•  Raw gene count matrices + sample metadata retrieved from NCBI GEO (2 datasets)." & vbCrLf & _
        "•  Low-count filtering: retained genes with rowSums >= 10." & vbCrLf & _
        "•  DESeq2 size-factor normalisation; log2(CPM + 1) transform." & vbCrLf & _
        "•  Duplicate gene symbols collapsed (rowsum); intersect -> 57,357 shared genes." & vbCrLf & _
        "•  PCA and sample-clustering QC (seed 42 for reproducibility).", _
        60, 125, 840, 360

    ' ---- 8. DESeq2 methods ----
    Set s = NewC(pres, "Differential Expression (DESeq2)")
    AddBullets s, _
        "•  Design: ~ condition; negative-binomial GLM, Wald test." & vbCrLf & _
        "•  Multiple testing: Benjamini-Hochberg FDR." & vbCrLf & _
        "•  Significance thresholds: FDR < 0.05  AND  |log2 fold change| > 1." & vbCrLf & _
        "•  Outputs per dataset: full DEG table, up/down lists, volcano, MA plot, top-DEG heatmap." & vbCrLf & _
        "•  Reference level = Sensitive; contrast = Resistant vs Sensitive.", _
        60, 125, 840, 360

    ' ---- 9. DS1 ----
    Set s = NewC(pres, "Dataset 1 (SKOV-3 / GSE303889) — DEG Results")
    AddBullets s, _
        "•  GSE303889: SKOV-3 parental vs KDM5-mediated CDDP-resistant cells." & vbCrLf & _
        "•  Total significant DEGs: 5,212" & vbCrLf & _
        "     -  Up-regulated:  2,983" & vbCrLf & _
        "     -  Down-regulated: 2,229" & vbCrLf & _
        "•  Extensive transcriptomic reprogramming on resistance acquisition." & vbCrLf & _
        "•  Top down-regulated genes include CDH1 (E-cadherin) — EMT signal.", _
        40, 120, 430, 370
    AddImageFit s, PROJ & "results\dataset1\volcano_plot.png", 500, 110, 430, 390

    ' ---- 10. DS2 ----
    Set s = NewC(pres, "Dataset 2 (OVCAR5 / GSE283381) — DEG Results")
    AddBullets s, _
        "•  GSE283381: OVCAR5 cisplatin-sensitive (Cis-S) vs resistant (Cis-R)." & vbCrLf & _
        "•  Total significant DEGs: 2,572" & vbCrLf & _
        "     -  Up-regulated:    912" & vbCrLf & _
        "     -  Down-regulated: 1,660" & vbCrLf & _
        "•  Up-regulated inflammatory / ECM genes (IL1A, IL1B, COL genes)." & vbCrLf & _
        "•  Distinct resistance mechanism vs Dataset 1.", _
        40, 120, 430, 370
    AddImageFit s, PROJ & "results\dataset2\volcano_plot.png", 500, 110, 430, 390

    ' ---- 11. Cross-dataset ----
    Set s = NewC(pres, "Cross-Dataset Validation")
    AddBullets s, _
        "•  913 genes are differentially expressed in BOTH datasets (core signature)." & vbCrLf & _
        "     -  198 shared up-regulated" & vbCrLf & _
        "     -  220 shared down-regulated" & vbCrLf & _
        "     -  495 with opposite direction (cell-line-specific)" & vbCrLf & _
        "•  Spearman correlation of shared log2FC ~ -0.04." & vbCrLf & _
        "•  Low correlation is expected: distinct resistance mechanisms (epigenetic vs metabolic).", _
        40, 120, 430, 370
    AddImageFit s, PROJ & "results\comparison\venn_diagram.png", 490, 105, 450, 200
    AddImageFit s, PROJ & "results\comparison\lfc_correlation.png", 490, 305, 450, 190

    ' ---- 12. GO ----
    Set s = NewC(pres, "Functional Enrichment — Gene Ontology")
    AddBullets s, _
        "•  clusterProfiler enrichGO (BP focus), BH-adjusted, p < 0.05." & vbCrLf & _
        "•  Top enriched terms for shared DEGs:" & vbCrLf & _
        "     -  Cell-substrate adhesion" & vbCrLf & _
        "     -  Extracellular matrix organisation" & vbCrLf & _
        "     -  Extracellular structure organisation" & vbCrLf & _
        "     -  Ossification / axon guidance" & vbCrLf & _
        "•  ECM and adhesion processes dominate — hallmark of EMT.", _
        40, 120, 430, 370
    AddImageFit s, PROJ & "results\enrichment\GO_dotplot_Shared_DEGs.png", 490, 100, 450, 400

    ' ---- 13. KEGG ----
    Set s = NewC(pres, "Functional Enrichment — KEGG Pathways")
    AddBullets s, _
        "•  enrichKEGG (hsa), BH-adjusted, p < 0.05." & vbCrLf & _
        "•  Convergent pathways in shared DEGs:" & vbCrLf & _
        "     -  PI3K-Akt signalling" & vbCrLf & _
        "     -  Focal adhesion / Integrin signalling" & vbCrLf & _
        "     -  Cadherin signalling" & vbCrLf & _
        "     -  Cytoskeleton / ECM-receptor interaction" & vbCrLf & _
        "     -  Hippo signalling pathway" & vbCrLf & _
        "•  Survival, adhesion and cytoskeletal remodelling converge on resistance.", _
        40, 120, 430, 370
    AddImageFit s, PROJ & "results\enrichment\KEGG_dotplot_Shared_DEGs.png", 490, 100, 450, 400

    ' ---- 14. Biological model ----
    Set s = NewC(pres, "Biological Model of Cisplatin Resistance")
    AddBullets s, _
        "•  EMT (central): CDH1 down, EPCAM down, COL1A1/COL5A2/COL6A1 up, MMP14/MMP1 up." & vbCrLf & _
        "•  Inflammation: IL1A up / IL1B up (NLRP3 inflammasome)." & vbCrLf & _
        "•  NDRG1 up — validated hub gene across 3 independent OC datasets." & vbCrLf & _
        "•  KYNU up — kynurenine/AhR axis driving immune evasion." & vbCrLf & _
        "•  SERPINE1 up — metastasis & resistance effector." & vbCrLf & vbCrLf & _
        "  Cisplatin -> DNA damage -> inflammation -> apoptosis evasion + ECM remodelling" & vbCrLf & _
        "  -> integrin/focal adhesion -> EMT -> drug efflux & stemness -> RESISTANCE", _
        60, 120, 840, 380
    AddNotes s, "Literature-supported: Wani 2025, Ghosh 2022, Li 2021, Zhu 2024, J Ovarian Res 2025."

    ' ---- 15. ML design ----
    Set s = NewC(pres, "Machine Learning: Design & Leakage Control")
    AddBullets s, _
        "•  Feature space: full intersected matrix (12 samples x 57,357 genes), log2(CPM+1)." & vbCrLf & _
        "•  Models: Logistic Regression (ridge/L2), Random Forest (ranger), SVM (radial)." & vbCrLf & _
        "•  Nested feature selection: top-K by |t-statistic|, K in {20,50,100,200,500} — inside each training fold only." & vbCrLf & _
        "•  Fold-aware normalisation; two external schemes:" & vbCrLf & _
        "     -  target_z (transductive, batch-corrected)" & vbCrLf & _
        "     -  train_stats (strictly non-transductive, leak-free)" & vbCrLf & _
        "•  Validation: within-cell-line LOOCV + leave-one-dataset-out external.", _
        60, 120, 840, 380
    AddNotes s, "No DEG pre-filtering: avoids test leakage. Deterministic via fixed seeds."

    ' ---- 16. LOOCV ----
    Set s = NewC(pres, "Within-Cell-Line LOOCV")
    AddBullets s, _
        "•  Leave-one-out inside each cell line (5 train / 1 test per fold)." & vbCrLf & _
        "•  Preprocessing + feature selection recomputed per fold." & vbCrLf & _
        "•  Accuracy 0.833 – 1.000  |  ROC-AUC 0.889 – 1.000." & vbCrLf & _
        "•  Phenotypes are almost trivially separable within a cell line." & vbCrLf & _
        "•  Likely optimistic: reflects within-study (batch) separation.", _
        40, 125, 430, 360
    AddImageFit s, PROJ & "results\ml\ROC_LOOCV.png", 490, 105, 450, 390

    ' ---- 17. External ----
    Set s = NewC(pres, "Cross-Dataset External Validation")
    AddBullets s, _
        "•  Train on one cell line (6), predict the other (6)." & vbCrLf & _
        "•  target_z (batch-corrected):" & vbCrLf & _
        "     -  SKOV3 -> OVCAR5: AUC 1.0 at K = 20-50" & vbCrLf & _
        "     -  OVCAR5 -> SKOV3: AUC ~ 0.44 - 0.78 (near chance)" & vbCrLf & _
        "•  train_stats (leak-free, strict): mean ROC-AUC ~ 0.61." & vbCrLf & _
        "•  Transfer is partial and strongly asymmetric; signal collapses as K grows (n << p).", _
        40, 120, 430, 375
    AddImageFit s, PROJ & "results\ml\ROC_external.png", 490, 105, 450, 200
    AddImageFit s, PROJ & "results\ml\ROC_external_trainstats.png", 490, 300, 450, 195

    ' ---- 18. Biomarker panel ----
    Set s = NewC(pres, "Candidate Biomarker Panel")
    AddBullets s, _
        "•  Ranked by cross-dataset selection frequency across models x K." & vbCrLf & _
        "•  Top candidates: MAL2, GALNT6, LDOC1, SH2D4A, FBXL21P," & vbCrLf & _
        "     EPB41L3, TMEM218, CALB1, LINC02582, CELF2 ..." & vbCrLf & _
        "•  30-gene exploratory panel (biomarker_panel.csv)." & vbCrLf & _
        "•  Reflects the SKOV3->OVCAR5 direction; candidates for follow-up." & vbCrLf & _
        "•  NOT a clinically validated diagnostic panel.", _
        40, 120, 430, 375
    AddImageFit s, PROJ & "results\ml\feature_importance.png", 490, 100, 450, 400

    ' ---- 19. Dashboard ----
    Set s = NewC(pres, "Interactive Results Dashboard")
    AddBullets s, _
        "•  FastAPI backend (backend/app.py) serving the ML artifacts as a read-only REST API." & vbCrLf & _
        "•  Endpoints: /api/summary, /api/external, /api/metrics, /api/loocv," & vbCrLf & _
        "     /api/predictions/external, /api/biomarkers, /api/feature-importance." & vbCrLf & _
        "•  Web dashboard with a normalisation toggle (target_z / train_stats)," & vbCrLf & _
        "     AUC-by-K chart, external metrics table and prediction explorer." & vbCrLf & _
        "•  Run:  python backend/app.py  ->  http://127.0.0.1:8000/", _
        60, 125, 840, 360

    ' ---- 20. Key findings ----
    Set s = NewC(pres, "Key Findings")
    AddBullets s, _
        "•  Extensive transcriptomic reprogramming: 5,212 DEGs (SKOV-3) and 2,572 (OVCAR5)." & vbCrLf & _
        "•  913 shared DEGs form a cross-dataset core cisplatin-resistance signature." & vbCrLf & _
        "•  EMT and ECM remodelling are the dominant shared mechanism." & vbCrLf & _
        "•  PI3K-Akt, focal adhesion, integrin and cadherin pathways converge on resistance." & vbCrLf & _
        "•  ML separates phenotypes within a cell line; cross-dataset transfer is partial and asymmetric." & vbCrLf & _
        "•  A 30-gene candidate panel (MAL2, GALNT6, ...) nominated for follow-up.", _
        60, 120, 840, 380

    ' ---- 21. Limitations ----
    Set s = NewC(pres, "Limitations & Caveats")
    AddBullets s, _
        "•  Small sample size (n = 12; 6 per cell line) — exploratory, not clinical validation." & vbCrLf & _
        "•  n << p: large-K feature sets overfit; small K is required." & vbCrLf & _
        "•  Cross-dataset normalisation choice materially changes external results." & vbCrLf & _
        "•  Only the train_stats scheme is fully leak-free (mean AUC ~ 0.61)." & vbCrLf & _
        "•  Two datasets share cancer type/drug but differ in resistance mechanism.", _
        60, 125, 840, 360

    ' ---- 22. Conclusions ----
    Set s = NewC(pres, "Conclusions & Future Work")
    AddBullets s, _
        "•  A reproducible end-to-end pipeline: GEO -> DESeq2 -> cross-validation -> GO/KEGG -> ML." & vbCrLf & _
        "•  Defines a core cisplatin-resistance transcriptomic signature with clear EMT/ECM biology." & vbCrLf & _
        "•  Provides an interactive dashboard and a candidate biomarker panel." & vbCrLf & vbCrLf & _
        "Future work:" & vbCrLf & _
        "•  Add independent datasets / more replicates to stabilise cross-dataset generalisation." & vbCrLf & _
        "•  Batch-correction benchmarking (ComBat, quantile) and pathway-level ML features." & vbCrLf & _
        "•  Experimental validation of MAL2, GALNT6, NDRG1 and the EMT axis.", _
        60, 120, 840, 380

    ' ---- 23. Thanks ----
    Set s = pres.Slides.Add(pres.Slides.Count + 1, ppLayoutBlank)
    Dim bg2 As Shape
    Set bg2 = s.Shapes.AddShape(1, 0, 0, 960, 540)
    bg2.Fill.ForeColor.RGB = COL_NAVY: bg2.Line.Visible = msoFalse
    Dim ty As Shape
    Set ty = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 0, 210, 960, 70)
    With ty.TextFrame.TextRange
        .Text = "Thank You"
        .Font.Name = "Calibri": .Font.Size = 44: .Font.Bold = msoTrue
        .Font.Color.RGB = COL_WHITE: .ParagraphFormat.Alignment = ppAlignCenter
    End With
    Dim qz As Shape
    Set qz = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 0, 290, 960, 40)
    With qz.TextFrame.TextRange
        .Text = "Questions?"
        .Font.Name = "Calibri": .Font.Size = 22: .Font.Color.RGB = COL_TEAL
        .ParagraphFormat.Alignment = ppAlignCenter
    End With

    MsgBox "Deck built: " & pres.Slides.Count & " slides.", vbInformation
End Sub

' ==================== HELPERS ====================
Private Function NewC(pres As Presentation, title As String) As Slide
    Dim s As Slide
    Set s = pres.Slides.Add(pres.Slides.Count + 1, ppLayoutBlank)
    Dim bar As Shape
    Set bar = s.Shapes.AddShape(1, 0, 0, 960, 76)
    bar.Fill.ForeColor.RGB = COL_NAVY: bar.Line.Visible = msoFalse
    Dim accent As Shape
    Set accent = s.Shapes.AddShape(1, 0, 76, 960, 5)
    accent.Fill.ForeColor.RGB = COL_TEAL: accent.Line.Visible = msoFalse
    Dim tb As Shape
    Set tb = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 30, 10, 900, 58)
    With tb.TextFrame.TextRange
        .Text = title: .Font.Name = "Calibri": .Font.Size = 26
        .Font.Bold = msoTrue: .Font.Color.RGB = COL_WHITE
        .ParagraphFormat.Alignment = ppAlignLeft
    End With
    Dim fl As Shape
    Set fl = s.Shapes.AddShape(1, 30, 512, 900, 1)
    fl.Fill.ForeColor.RGB = RGB(210, 215, 222): fl.Line.Visible = msoFalse
    Dim ft As Shape
    Set ft = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 30, 513, 720, 22)
    With ft.TextFrame.TextRange
        .Text = "Transcriptomic Profiling of Drug-Resistant Cancer Cells"
        .Font.Size = 10: .Font.Color.RGB = RGB(130, 138, 150)
    End With
    Dim num As Shape
    Set num = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 890, 513, 40, 22)
    With num.TextFrame.TextRange
        .Text = CStr(pres.Slides.Count): .Font.Size = 10
        .Font.Color.RGB = RGB(130, 138, 150)
        .ParagraphFormat.Alignment = ppAlignRight
    End With
    Set NewC = s
End Function

Private Sub MakeTitleSlide(s As Slide, title As String, subtitle As String, team As String)
    Dim bg As Shape
    Set bg = s.Shapes.AddShape(1, 0, 0, 960, 540)
    bg.Fill.ForeColor.RGB = COL_NAVY: bg.Line.Visible = msoFalse
    Dim band As Shape
    Set band = s.Shapes.AddShape(1, 70, 300, 820, 6)
    band.Fill.ForeColor.RGB = COL_TEAL: band.Line.Visible = msoFalse
    Dim t As Shape
    Set t = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 70, 170, 820, 120)
    With t.TextFrame.TextRange
        .Text = title: .Font.Name = "Calibri": .Font.Size = 38
        .Font.Bold = msoTrue: .Font.Color.RGB = COL_WHITE
    End With
    Dim st As Shape
    Set st = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 70, 318, 820, 80)
    With st.TextFrame.TextRange
        .Text = subtitle: .Font.Name = "Calibri": .Font.Size = 18
        .Font.Color.RGB = RGB(210, 224, 240)
    End With
    Dim tm As Shape
    Set tm = s.Shapes.AddTextbox(msoTextOrientationHorizontal, 70, 440, 820, 40)
    With tm.TextFrame.TextRange
        .Text = team: .Font.Name = "Calibri": .Font.Size = 14
        .Font.Color.RGB = RGB(160, 190, 220)
    End With
End Sub

Private Sub AddBullets(s As Slide, txt As String, left As Single, top As Single, width As Single, height As Single)
    Dim tb As Shape
    Set tb = s.Shapes.AddTextbox(msoTextOrientationHorizontal, left, top, width, height)
    With tb.TextFrame
        .WordWrap = msoTrue
        With .TextRange
            .Text = txt: .Font.Name = "Calibri": .Font.Size = 17
            .Font.Color.RGB = COL_GRAY
            .ParagraphFormat.SpaceAfter = 6
            .ParagraphFormat.LineRuleWithin = msoTrue
            .ParagraphFormat.SpaceWithin = 1.05
        End With
    End With
End Sub

Private Sub AddImageFit(s As Slide, path As String, left As Single, top As Single, maxW As Single, maxH As Single)
    If Dir(path) = "" Then Exit Sub
    Dim pic As Shape
    On Error Resume Next
    Set pic = s.Shapes.AddPicture(path, msoFalse, msoTrue, left, top, -1, -1)
    On Error GoTo 0
    If pic Is Nothing Then Exit Sub
    Dim w As Single, h As Single, sc As Single
    w = pic.Width: h = pic.Height
    If w <= 0 Or h <= 0 Then Exit Sub
    sc = maxW / w
    If (maxH / h) < sc Then sc = maxH / h
    pic.Width = w * sc
    pic.Height = h * sc
End Sub

Private Sub AddNotes(s As Slide, txt As String)
    On Error Resume Next
    Dim ph As Shape
    For Each ph In s.NotesPage.Shapes
        If ph.Type = msoPlaceholder Then
            If ph.PlaceholderFormat.Type = ppPlaceholderBody Then
                ph.TextFrame.TextRange.Text = txt
                Exit For
            End If
        End If
    Next ph
    On Error GoTo 0
End Sub

Private Sub BuildDatasetTable(s As Slide)
    Dim tbl As Shape
    Set tbl = s.Shapes.AddTable(5, 3, 60, 120, 840, 250)
    Dim T As Table
    Set T = tbl.Table

    Dim hdr(2) As String, r1(2) As String, r2(2) As String, r3(2) As String, r4(2) As String
    hdr(0) = "Attribute": hdr(1) = "GSE303889": hdr(2) = "GSE283381"
    r1(0) = "Cell line": r1(1) = "SKOV-3": r1(2) = "OVCAR5"
    r2(0) = "Resistance model": r2(1) = "CDDP (chronic cisplatin)": r2(2) = "Cis-R (repeated cisplatin)"
    r3(0) = "Design": r3(1) = "3 Sensitive vs 3 Resistant": r3(2) = "3 Sensitive vs 3 Resistant"
    r4(0) = "Platform": r4(1) = "Illumina NovaSeq 6000": r4(2) = "Illumina NextSeq 500"

    Dim rows(4) As Variant
    rows(0) = hdr: rows(1) = r1: rows(2) = r2: rows(3) = r3: rows(4) = r4

    Dim r As Long, c As Long
    For r = 0 To 4
        Dim arr As Variant
        arr = rows(r)
        For c = 0 To 2
            T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Text = arr(c)
            T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Font.Size = 15
            T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Font.Name = "Calibri"
            If r = 0 Then
                T.Cell(r + 1, c + 1).Shape.Fill.ForeColor.RGB = COL_NAVY
                T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Font.Color.RGB = COL_WHITE
                T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Font.Bold = msoTrue
            Else
                T.Cell(r + 1, c + 1).Shape.Fill.ForeColor.RGB = IIf(r Mod 2 = 0, COL_LIGHT, COL_WHITE)
                T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Font.Color.RGB = COL_GRAY
                If c = 0 Then T.Cell(r + 1, c + 1).Shape.TextFrame.TextRange.Font.Bold = msoTrue
            End If
        Next c
    Next r
End Sub

Private Sub BuildWorkflow(s As Slide)
    Dim y1 As Single, y2 As Single, bw As Single, bh As Single
    y1 = 140: y2 = 340: bw = 240: bh = 80
    AddBox s, "GEO datasets" & vbCrLf & "(2 studies)", 50, y1, bw, bh
    AddArrow s, 295, 162, 40, 36
    AddBox s, "Preprocess" & vbCrLf & "& QC", 350, y1, bw, bh
    AddArrow s, 595, 162, 40, 36
    AddBox s, "DESeq2" & vbCrLf & "per dataset", 650, y1, bw, bh

    AddDownArrow s, 750, 225, 36, 40

    AddBox s, "Cross-dataset" & vbCrLf & "validation", 50, y2, bw, bh
    AddArrow s, 295, 362, 40, 36
    AddBox s, "GO / KEGG" & vbCrLf & "enrichment", 350, y2, bw, bh
    AddArrow s, 595, 362, 40, 36
    AddBox s, "ML biomarker" & vbCrLf & "discovery", 650, y2, bw, bh
End Sub

Private Sub AddBox(s As Slide, txt As String, x As Single, y As Single, w As Single, h As Single)
    Dim sh As Shape
    Set sh = s.Shapes.AddShape(5, x, y, w, h)
    With sh
        .Fill.ForeColor.RGB = COL_TEAL: .Line.Visible = msoFalse
        .TextFrame.TextRange.Text = txt
        .TextFrame.TextRange.Font.Size = 14
        .TextFrame.TextRange.Font.Bold = msoTrue
        .TextFrame.TextRange.Font.Color.RGB = COL_WHITE
        .TextFrame.TextRange.ParagraphFormat.Alignment = ppAlignCenter
        .TextFrame.VerticalAnchor = msoAnchorMiddle
    End With
End Sub

Private Sub AddArrow(s As Slide, x As Single, y As Single, w As Single, h As Single)
    Dim a As Shape
    Set a = s.Shapes.AddShape(33, x, y, w, h)
    a.Fill.ForeColor.RGB = COL_NAVY: a.Line.Visible = msoFalse
End Sub

Private Sub AddDownArrow(s As Slide, x As Single, y As Single, w As Single, h As Single)
    Dim a As Shape
    Set a = s.Shapes.AddShape(36, x, y, w, h)
    a.Fill.ForeColor.RGB = COL_NAVY: a.Line.Visible = msoFalse
End Sub

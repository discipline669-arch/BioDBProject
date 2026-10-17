Attribute VB_Name = "modCondensedDeck"
Option Explicit

' =====================================================================
'  Transcriptomic Profiling of Drug-Resistant Cancer Cells
'  CONDENSED deck (12 slides, 16:9). Run BuildCondensedDeck.
'  Adjust PROJ if the project root moves.
' =====================================================================

Const PROJ As String = "E:\BioDBProject\BioDBProject\transcriptomic_drug_resistance_project\"

Dim COL_NAVY As Long, COL_TEAL As Long, COL_GRAY As Long, COL_WHITE As Long, COL_LIGHT As Long

Sub BuildCondensedDeck()
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
        "Cisplatin resistance in ovarian cancer: DEGs, pathways & ML biomarkers", _
        "Team of 3  |  Data & QC  .  DEGs & Biology  .  ML & Biomarkers"

    ' ---- 2. Background & Objectives ----
    Set s = NewC(pres, "Background & Objectives")
    AddBullets s, _
        "•  Ovarian cancer: platinum (cisplatin) is first-line; acquired resistance drives relapse." & vbCrLf & _
        "•  Resistance is multifactorial (epigenetic, metabolic, EMT, efflux, apoptosis evasion)." & vbCrLf & vbCrLf & _
        "Objectives" & vbCrLf & _
        "•  Identify DEGs between resistant and sensitive ovarian cancer cells." & vbCrLf & _
        "•  Validate DEGs across two independent GEO datasets." & vbCrLf & _
        "•  Characterise affected GO / KEGG pathways." & vbCrLf & _
        "•  Build ML classifiers and rank a candidate biomarker panel.", _
        60, 120, 840, 380

    ' ---- 3. Data ----
    Set s = NewC(pres, "Data: Two Independent GEO Datasets")
    BuildDatasetTable s

    ' ---- 4. Workflow ----
    Set s = NewC(pres, "Analytical Workflow")
    BuildWorkflow s

    ' ---- 5. DEG results ----
    Set s = NewC(pres, "Differential Expression Results")
    AddBullets s, _
        "•  DESeq2, FDR < 0.05 and |log2FC| > 1 (Design ~ condition)." & vbCrLf & vbCrLf & _
        "•  SKOV-3 (GSE303889): 5,212 DEGs (2,983 up / 2,229 down)." & vbCrLf & _
        "•  OVCAR5 (GSE283381): 2,572 DEGs (912 up / 1,660 down)." & vbCrLf & vbCrLf & _
        "•  913 genes shared by both datasets (198 up / 220 down / 495 opposite)." & vbCrLf & _
        "•  Extensive, dataset-specific reprogramming; low shared log2FC correlation (~ -0.04).", _
        40, 120, 430, 375
    AddImageFit s, PROJ & "results\dataset1\volcano_plot.png", 490, 105, 450, 200
    AddImageFit s, PROJ & "results\dataset2\volcano_plot.png", 490, 305, 450, 190

    ' ---- 6. Cross-dataset ----
    Set s = NewC(pres, "Cross-Dataset Validation")
    AddBullets s, _
        "•  913 shared DEGs = core cross-dataset cisplatin-resistance signature." & vbCrLf & _
        "•  Distinct resistance mechanisms (KDM5 epigenetic vs pyrimidine metabolism)." & vbCrLf & _
        "•  Shared signature highlights EMT / ECM biology." & vbCrLf & _
        "•  Consistently regulated genes = higher-confidence candidates.", _
        40, 120, 400, 370
    AddImageFit s, PROJ & "results\comparison\venn_diagram.png", 460, 105, 480, 210
    AddImageFit s, PROJ & "results\comparison\lfc_correlation.png", 460, 310, 480, 185

    ' ---- 7. Enrichment ----
    Set s = NewC(pres, "Functional Enrichment (GO / KEGG)")
    AddBullets s, _
        "GO (shared DEGs):" & vbCrLf & _
        "•  Cell-substrate adhesion" & vbCrLf & _
        "•  Extracellular matrix organisation" & vbCrLf & _
        "•  Extracellular structure organisation" & vbCrLf & vbCrLf & _
        "KEGG (shared DEGs):" & vbCrLf & _
        "•  PI3K-Akt signalling" & vbCrLf & _
        "•  Focal adhesion / Integrin signalling" & vbCrLf & _
        "•  Cadherin signalling" & vbCrLf & _
        "•  Cytoskeleton / ECM-receptor interaction", _
        40, 115, 400, 380
    AddImageFit s, PROJ & "results\enrichment\GO_dotplot_Shared_DEGs.png", 430, 95, 260, 390
    AddImageFit s, PROJ & "results\enrichment\KEGG_dotplot_Shared_DEGs.png", 700, 95, 260, 390

    ' ---- 8. Biological model ----
    Set s = NewC(pres, "Biological Model of Resistance")
    AddBullets s, _
        "•  EMT (central): CDH1 down, EPCAM down, COL1A1/COL5A2/COL6A1 up, MMP14/MMP1 up." & vbCrLf & _
        "•  Inflammation: IL1A up / IL1B up (inflammasome)." & vbCrLf & _
        "•  NDRG1 up — validated hub gene in 3 independent OC datasets." & vbCrLf & _
        "•  KYNU up — kynurenine/AhR immune evasion." & vbCrLf & _
        "•  SERPINE1 up — metastasis & resistance effector." & vbCrLf & vbCrLf & _
        "  Cisplatin -> DNA damage -> inflammation -> ECM remodelling -> EMT -> RESISTANCE", _
        60, 120, 840, 370

    ' ---- 9. ML design & results ----
    Set s = NewC(pres, "Machine Learning: Design & Results")
    AddBullets s, _
        "•  Full 57,357-gene space; LR (ridge), Random Forest, SVM radial." & vbCrLf & _
        "•  Nested top-K selection (K in {20,50,100,200,500}) — no test leakage." & vbCrLf & _
        "•  Within-cell-line LOOCV: Acc 0.833-1.000, AUC 0.889-1.000." & vbCrLf & _
        "•  External (target_z): SKOV3->OVCAR5 AUC 1.0 at K=20-50; reverse ~0.44-0.78." & vbCrLf & _
        "•  External (train_stats, leak-free): mean AUC ~0.61." & vbCrLf & _
        "•  Transfer is partial and asymmetric (n << p).", _
        40, 120, 430, 375
    AddImageFit s, PROJ & "results\ml\ROC_LOOCV.png", 490, 105, 450, 200
    AddImageFit s, PROJ & "results\ml\ROC_external.png", 490, 305, 450, 190

    ' ---- 10. Biomarker panel ----
    Set s = NewC(pres, "Candidate Biomarker Panel")
    AddBullets s, _
        "•  Ranked by cross-dataset selection frequency (models x K)." & vbCrLf & _
        "•  Top candidates: MAL2, GALNT6, LDOC1, SH2D4A, FBXL21P," & vbCrLf & _
        "     EPB41L3, TMEM218, CALB1, LINC02582, CELF2 ..." & vbCrLf & _
        "•  30-gene exploratory panel for follow-up." & vbCrLf & _
        "•  NOT a clinically validated diagnostic panel.", _
        40, 120, 430, 375
    AddImageFit s, PROJ & "results\ml\feature_importance.png", 490, 100, 450, 400

    ' ---- 11. Findings & conclusions ----
    Set s = NewC(pres, "Key Findings, Limitations & Conclusions")
    AddBullets s, _
        "Key findings" & vbCrLf & _
        "•  913 shared DEGs; EMT and ECM remodelling dominate." & vbCrLf & _
        "•  PI3K-Akt, focal adhesion, integrin and cadherin pathways converge." & vbCrLf & _
        "•  ML works within a cell line; cross-dataset transfer is partial / asymmetric." & vbCrLf & vbCrLf & _
        "Limitations" & vbCrLf & _
        "•  n = 12 (exploratory); n << p; normalisation choice matters." & vbCrLf & vbCrLf & _
        "Conclusions" & vbCrLf & _
        "•  Reproducible end-to-end pipeline + dashboard + candidate panel.", _
        60, 115, 840, 385

    ' ---- 12. Thanks ----
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

Private Sub BuildDatasetTable(s As Slide)
    Dim tbl As Shape
    Set tbl = s.Shapes.AddTable(5, 3, 70, 135, 820, 240)
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

# Irrelevant Content — final_report.docx

Content that is irrelevant, excluded by design, or not load-bearing for the study's claims.

## Samples/experiments excluded from the label-bearing contrast
- GSE202859 excluded arms (34 samples): acute osimertinib treatments (24 h drug shock), SMARCA4-shRNA perturbation arms, PC9-OR untreated controls.
- GSE193258 excluded arms (42 samples): 24 h acute treatment, short washout, long washout timecourse (72 h / 96 h / 7 d / 10 d), non-shared cell line HCC2935.
- These samples are only used (label-free) in the washout sensitivity probe — they never contribute to accuracy metrics or the DEG contrast.

## Reporting artefacts, not findings
- TOC field code (`TOC \o "1-1" \h \z \u`).
- Duplicate figure captions (each figure is captioned twice in the document layout — once as figure-legend text, once as in-document caption).
- Boilerplate XML/page furniture from the .docx extraction.

## Declared non-primary / fallback methods
- limma/OLS normalisation — retained only as declared fallbacks, never used.
- In-cohort nested CV on GSE193258 (Figures 29–32) — exploratory panels only; the validation cohort is not used for training in the confirmatory flow.
- target_z (transductive) scheme numbers — optimistic upper bound only, never a headline result (decision D1).
- SVM calibration/Brier values — reference-only; SVM decision scores are monotone sigmoids, not calibrated probabilities.

## Non-claims / out-of-scope items
- Any clinical, diagnostic, prognostic or causal claims — explicitly disclaimed; results are exploratory candidate biomarkers on cell lines only.
- Patient response, immune microenvironment, drug dosing schedules — no clinical context in the data.
- Causality of panel genes — the 100-gene panel is a candidate biomarker set, not a set of causal drivers.
- Accuracy claims for washout/timecourse samples — the probe is label-free and interpretive (decision D7).
- Non-canonical gene symbols flagged for curation (e.g., HECA, SACK1A, IL33R, MTURN as NCBI symbol-space additions) — pending downstream HGNC curation before database deposition.

## Background material that motivates but does not constitute results
- General methodological primer text (what DESeq2/GSEA/nested CV are) — citation-level support only, not project output.
- Redundant restatements: key numbers (1,112 genes, AUC 1.000, washout gradient) appear in Abstract, Analysis, Results, Discussion and Conclusion; only one full statement is needed per section.

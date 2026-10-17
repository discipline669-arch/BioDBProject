# Non-Fixable Tradeoffs

Tradeoffs and limitations that remain **regardless of any code fix**. They are properties of the
data, the biological question, or the statistical setting. They must be disclosed, not "solved".

---

## N1. Drug-exposure confound
In both cohorts the resistant arm is drug-treated while the sensitive arm is vehicle/untreated, so the
resistance signature is partly entangled with **acute drug exposure**. Washout samples exist but were
excluded from training. No modelling choice removes this without a drug-treated-sensitive control arm.

## N2. `-OR` vs `osi_DTP` are different resistance states
GSE202859 resistant samples are chronically dosed `-OR` lines (relatively stable acquired
resistance); GSE193258 resistant samples are 3-week `osi_DTP` persisters (potentially reversible).
They are treated as one "Resistant" class by the label policy; this endpoint mismatch is inherent.

## N3. Only three cell lines
PC9, H1975, HCC827 → leave-one-cell-line-out CV has only **3 folds**. Confidence intervals are wide
and feature selection is unstable. More folds require more lines (see T5).

## N4. p >> n
Tens of thousands of genes vs 18 samples per cohort. High-dimensional overfitting is mitigated by
regularisation and nested CV, but not eliminated.

## N5. Cell lines are not patients
No tumour microenvironment, immune compartment, pharmacokinetics, or clonal heterogeneity. Any
translational claim is unsupported by this data.

## N6. Cell-line identity is entangled with condition
Baseline genetic differences between the three lines correlate with the condition structure. The
DESeq2 design includes `cell_line`, but within-cell-line signal is limited to 3 replicates, so some
cell-line effects can leak into the "resistance" contrast.

## N7. Cross-dataset agreement is reproducibility, not mechanism
A gene significant in both cohorts with consistent direction is evidence of **reproducibility** of an
association — not of causal role in resistance.

## N8. NCBI harmonised counts tradeoff
Uniform reprocessing guarantees a shared universe and enables DESeq2, but the values may differ from
authors' own quantification (Kallisto/TPM) and discard isoform-level information. This is a
deliberate trade of fidelity for comparability.

## N9. Normalisation choice affects absolute values
VST (now) vs log2(CPM+1) (previously) changes the exact expression values and downstream DEG ranking.
Results are conditioning on the normalisation; only relative patterns are robust.

## N10. Winner's curse
Enumerating a model × K grid and reporting the best cell inflates the best estimate. Reporting the
full grid (per plan §6) **mitigates** but does not remove this.

## N11. Predictive ≠ causal
Feature importance / SHAP describe the model, not biology. Candidate biomarkers are hypotheses.

## N12. Enrichment is noisy at small n
ORA/GSEA on a few hundred to a few thousand genes from 18+18 samples is hypothesis-level. FDR control
and cross-checking GO/KEGG/Reactome/GSEA reduce but do not remove false positives.

## N13. No isoform / fusion / CNV / immune signal
Bulk gene-level counts cannot see alternative splicing, gene fusions, copy-number changes, or immune
infiltration — all relevant to drug resistance.

## N14. The resistance timepoint is fixed by the source studies
"3 weeks" (GSE193258) and the `-OR` derivation (GSE202859) are study-defined endpoints; the biology
may differ at other times.

## N15. Residual cross-study batch effects
Different labs, platforms (NovaSeq vs HiSeq), and library preps. NCBI harmonisation reduces but does
not remove study-level differences; cohorts are never pooled, so this shows up as distribution shift
at validation time.

## N16. Label-policy exclusions discard real biology
Acute-24h, washout, and shRNA/perturbation samples are excluded by design. This is correct for the
stated question but means those states are unmodelled.

## N17. Score-distribution shift harms calibration
Even with good discrimination (AUC), predicted probabilities shift across cohorts (`train_stats` vs
`target_z`), so calibration/Brier is fragile and threshold transfer is unreliable.

## N18. Observational, not interventional
No perturbation of the candidate genes; associations cannot be upgraded to mechanisms without
experimental follow-up.

## N19. Operational/network constraints
GEO webfetch is reCAPTCHA-blocked and some NCBI FTP paths are heavily throttled in this environment;
`curl --ssl-no-revoke` and resume were required. This constrains automation but does not affect
results once data are present.

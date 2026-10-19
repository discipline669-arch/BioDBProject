#!/usr/bin/env python
"""Phase 7 (delivery) - assemble a results summary and reproducibility record.

Reads the Phase 4-6 outputs and writes:
  results/reports/summary.md
  results/reports/session_info.txt

Run: python scripts/08_report.py
"""
from __future__ import annotations

import platform
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project, set_global_seed  # noqa: E402


def _read(path: Path):
    return pd.read_csv(path) if path.is_file() else None


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    """Minimal markdown table writer (avoids the optional `tabulate` dep)."""
    def cell(v):
        if isinstance(v, float):
            return "nan" if pd.isna(v) else floatfmt.format(v)
        return str(v)

    cols = list(df.columns)
    rows = [[cell(v) for v in r] for r in df.itertuples(index=False)]
    out = ["| " + " | ".join(cols) + " |",
           "| " + " | ".join("---" for _ in cols) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def main():
    project = load_project()
    set_global_seed(project.cfg["project"]["seed"])
    project.ensure_dirs()
    T = project.tables

    nested = _read(T / "nested_cv_metrics.csv")
    ext = _read(T / "external_validation.csv")
    panel = _read(T / "biomarker_panel.csv")

    lines = []
    lines.append("# Results summary\n")
    lines.append(f"Generated: {datetime.now():%Y-%m-%d %H:%M}\n")
    if project.synthetic_mode:
        lines.append("> **SYNTHETIC DATA** - pipeline smoke-test run, not real GEO data.\n")
    lines.append("\n## Nested cross-validation (within-cohort, group-aware)\n")
    if nested is not None:
        best = (nested.sort_values("roc_auc", ascending=False)
                .groupby("accession").head(3))
        lines.append(md_table(pd.DataFrame(best[[
            c for c in ("accession", "model", "k", "roc_auc", "pr_auc",
                        "sensitivity", "specificity", "n_splits")
            if c in best.columns]])))
    else:
        lines.append("_not available - run 05_train_models.py_")

    lines.append("\n## External validation (discovery GSE202859 -> validation GSE193258)\n")
    if ext is not None:
        show = [c for c in ("model", "k", "normalization", "roc_auc", "roc_auc_lo",
                            "roc_auc_hi", "pr_auc", "sensitivity", "specificity", "brier")
                if c in ext.columns]
        lines.append(md_table(pd.DataFrame(ext.sort_values(
            ["model", "k", "normalization"])[show])))
        lines.append("\n_CIs are stratified bootstrap 95% intervals._")
        lines.append("\n**Note:** SVM scores are monotone sigmoids of the decision "
                     "function, not calibrated probabilities; SVM Brier/calibration "
                     "are reference-only.")
        lines.append("\n**Note:** with n=18 validation samples these estimates are "
                     "exploratory, not a clinical validation claim.")
        lines.append("\n**D1 (decided):** the headline scheme is `train_stats`; "
                     "`target_z` rows are transductive normalisations that leak "
                     "test-set statistics - optimistic bounds only, never the "
                     "headline.")
    else:
        lines.append("_not available - run 06_validate_clinical.py_")

    lines.append("\n**D2 (decided):** pre-registered primary configuration is "
                 "**LogisticRegression, K=50** (inner-CV-consistent); every other "
                 "model x K cell in this report is exploratory.")

    lines.append("\n## Functional enrichment (Stage 5)\n")
    enr_any = False
    for source in ("GO_BP", "KEGG", "Reactome"):
        df = _read(T / f"enrichment_validated_{source}.csv")
        if df is None or df.empty:
            continue
        enr_any = True
        top = df.sort_values("padj").head(6)
        show = [c for c in ("term_name", "overlap", "set_size",
                            "fold_enrichment", "padj") if c in top.columns]
        lines.append(f"\n**Validated signature ({source}), top 6 by BH-adjusted p:**")
        lines.append(md_table(pd.DataFrame(top[show])))
        lead = sorted({g for s in df.sort_values("padj").head(10)["genes"]
                       for g in str(s).strip().split(";") if g and g != "nan"})
        if lead:
            preview = ", ".join(lead[:15]) + (f" (+{len(lead) - 15} more)"
                                              if len(lead) > 15 else "")
            lines.append(f"\nLeading-edge genes across top 10 terms ({len(lead)} total):"
                         f" {preview}")
    if not enr_any:
        lines.append("_enrichment tables not found - run scripts/03b_enrichment.py_")

    gsea_any = False
    for acc, role in (("GSE202859", "discovery"), ("GSE193258", "validation")):
        gdf = _read(project.root / "results" / "tables" / f"gsea_{acc}_KEGG.csv")
        if gdf is None or gdf.empty:
            continue
        gsea_any = True
        gtop = gdf.sort_values("padj").head(5)
        show = [c for c in ("term_name", "NES", "padj") if c in gtop.columns]
        lines.append(f"\n**Pre-ranked GSEA hits ({role} {acc}, top 5 by BH):**")
        lines.append(md_table(pd.DataFrame(gtop[show])))
    if gsea_any:
        lines.append("\n_GSEA ranks genes by signed log2FC from the DEG tables; "
                     "NES = normalised enrichment score._")

    if project.synthetic_mode:
        lines.append("\n_(Stage 5 runs on real cohorts; synthetic mode skips enrichment.)_")

    lines.append("\n## Sensitivity - biological reversibility (D7)\n")
    wgroups = _read(T / "washout_sensitivity_groups.csv")
    if wgroups is not None and not wgroups.empty:
        prim = wgroups[(wgroups["model"] == "LogisticRegression") &
                       (wgroups["k"] == 50)]
        show = prim if not prim.empty else wgroups.head(9)
        lines.append("Locked **discovery** models applied to the excluded GSE193258 "
                     "time-course samples (VST refit on all 60 samples, blind; "
                     "train_stats scheme). No AUC is claimed - the washout/acute "
                     "samples have no two-class labels; the reading is whether "
                     "P(Resistant) drifts back after drug withdrawal.")
        lines.append(md_table(pd.DataFrame(show)))
        lines.append("\n_P(Resistant) ~ 0 in DMSO/parental anchors and ~ 1 in DTP "
                     "anchors sanity-check the transfer._")
    else:
        lines.append("_not available - run scripts/02b_vst_extend.R then "
                     "scripts/10_washout_sensitivity.py_")

    lines.append("\n## GSEA engine cross-check (D3)\n")
    fgseen = 0
    for acc, src in (("GSE202859", "KEGG"), ("GSE193258", "KEGG")):
        py = _read(T / f"gsea_{acc}_{src}.csv")
        fp = _read(T / f"gsea_{acc}_{src}_fgsea.csv")
        if py is None or fp is None or fp.empty or py is None or py.empty:
            continue
        both = fp.merge(py[["term_id", "NES"]], on="term_id",
                        suffixes=("_fgsea", "_python"))
        if len(both) < 5:
            continue
        rho = both["NES_fgsea"].corr(both["NES_python"], method="spearman")
        top_py = set(py.sort_values("padj").head(5)["term_id"])
        top_fp = set(fp.sort_values("padj").head(5)["term_id"])
        ov = len(top_py & top_fp)
        lines.append(f"- **{acc} ({src})**: NES concordance Spearman rho = "
                     f"{rho:.2f} over {len(both)} sets; top-5 by padj overlap "
                     f"{ov}/5.")
        fgseen += 1
    if fgseen == 0:
        lines.append("_not available - run scripts/03c_fgsea_crosscheck.R_ (also "
                     "_requires the D10-updated Stage 5 GMT exports)_")
    else:
        lines.append("\n_Python pre-ranked GSEA (size-bucketed permutation null) "
                     "remains the primary engine; fgsea is the exact cross-check "
                     "per D3. Full fgsea tables: `gsea_*_fgsea.csv`._")

    lines.append("\n## Candidate biomarker panel (top 20)\n")
    if panel is not None:
        lines.append(md_table(panel.head(20).reset_index(drop=True)))
        lines.append("\nCandidate biomarkers only; predictive genes are not causal.")
    else:
        lines.append("_not available - run 07_interpret.py_")

    lines.append("\n## Leakage controls applied\n")
    for r in [
        "Cohorts kept separate; no pooled cross-validation.",
        "Splits are group-aware by cell line; all replicates of a line stay in one fold.",
        "Feature selection, scaling and tuning run inside each training fold.",
        "External validation cohort evaluated once, after the pipeline is locked.",
        "Full model x K grid reported; bootstrap CIs included.",
    ]:
        lines.append(f"- {r}")

    out = project.reports / "summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")

    # reproducibility record
    info = [
        f"generated: {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"python: {sys.version}",
        f"platform: {platform.platform()}",
        f"project_root: {project.root}",
        f"synthetic_mode: {project.synthetic_mode}",
        f"seed: {project.cfg['project']['seed']}",
        "",
        "package versions:",
    ]
    for mod in ("numpy", "pandas", "scipy", "sklearn", "xgboost", "shap"):
        try:
            m = __import__(mod)
            info.append(f"  {mod}: {getattr(m, '__version__', 'n/a')}")
        except Exception:
            info.append(f"  {mod}: not installed")
    (project.reports / "session_info.txt").write_text("\n".join(info), encoding="utf-8")
    print(f"Wrote {project.reports / 'session_info.txt'}")


if __name__ == "__main__":
    main()

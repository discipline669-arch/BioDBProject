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
        lines.append("\n**Note:** with n=18 validation samples these estimates are "
                     "exploratory, not a clinical validation claim.")
    else:
        lines.append("_not available - run 06_validate_clinical.py_")

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

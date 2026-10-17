#!/usr/bin/env python
"""Phase 4 - Feature selection (training-only / stability based).

Produces a gene-level candidate table per cohort using:
  * elastic-net stability selection (stratified bootstrap of the training data)
  * optional DEG log2FC annotation, if the R track has produced DEG tables

This is a screening deliverable. The *decision* feature set used for each model
is still chosen inside every training fold in Phase 5 (nested), so nothing here
leaks test information into model fitting.

Run: python scripts/04_feature_selection.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project, set_global_seed  # noqa: E402
from ml.data import align_gene_space, encode_labels, load_cohort  # noqa: E402
from ml.models import stability_selection  # noqa: E402


def deg_annotation(project, accession):
    """Read <ACC>_DEG_full.csv if present; return gene -> log2FC map."""
    f = project.tables / f"{accession}_DEG_full.csv"
    if not f.is_file():
        return None
    df = pd.read_csv(f)
    gene_col = next((c for c in ("gene", "gene_name", "gene_id") if c in df.columns), None)
    if gene_col is None or "log2FoldChange" not in df.columns:
        return None
    return df.set_index(gene_col)["log2FoldChange"]


def main():
    project = load_project()
    set_global_seed(project.cfg["project"]["seed"])
    project.ensure_dirs()

    disc = load_cohort(project, project.cfg["cohorts"]["discovery"]["accession"])
    clin = load_cohort(project, project.cfg["cohorts"]["validation"]["accession"])
    disc, clin = align_gene_space(disc, clin)
    print(f"Aligned gene space: {disc.X.shape[1]} genes")
    print(f"  discovery  {disc.accession}: {disc.X.shape[0]} samples "
          f"({dict(disc.y.value_counts())})")
    print(f"  validation {clin.accession}: {clin.X.shape[0]} samples "
          f"({dict(clin.y.value_counts())})")

    threshold = project.cfg["ml"]["feature_selection"]["stability_threshold"]
    rows = []
    for label, cohort in (("discovery", disc), ("validation", clin)):
        print(f"\nStability selection ({label}, elastic net), "
              f"{project.cfg['ml']['feature_selection']['stability_resamples']} resamples...")
        freq = stability_selection(
            cohort.X, encode_labels(cohort.y),
            seed=project.cfg["project"]["seed"], cfg=project.cfg
        )
        out = freq.to_frame().sort_values("stability_freq", ascending=False)
        out.to_csv(project.tables / f"feature_stability_{label}.csv")
        kept = int((out["stability_freq"] >= threshold).sum())
        print(f"  genes selected >= {threshold:.2f}: {kept} / {len(out)}")
        print(f"  top 5: {list(out.head(5).index)}")
        rows.append((label, out, cohort))

    # Combined candidate table for the validation cohort (external target)
    cand = rows[1][1].copy()
    cand.index.name = "gene"
    lfc = deg_annotation(project, clin.accession)
    if lfc is not None:
        cand["log2FC_validation"] = lfc.reindex(cand.index)
    panel = cand.sort_values("stability_freq", ascending=False)
    panel.to_csv(project.tables / "feature_candidates_validation.csv")
    print(f"\nWrote {project.tables / 'feature_candidates_validation.csv'}")
    print("Phase 4 complete.")


if __name__ == "__main__":
    main()

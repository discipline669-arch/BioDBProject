#!/usr/bin/env python
"""BL-4 - true UpSet-style plot for the cross-dataset DEG overlap.

Sets (gene symbols):
  Discovery DEGs  = union(up, down) from GSE202859 DEG tables
  Validation DEGs = union(up, down) from GSE193258 DEG tables
  Validated       = genes significant in BOTH with consistent direction
                    (results/tables/validated_DEGs.csv)

Hand-rolled renderer (no `upsetplot` - its 0.9.0 is incompatible with the
project's pandas 3.x stack: silent CoW no-ops + NaN style crash). Canonical
UpSet layout: intersection bars (size-sorted) below, membership matrix with
constellation lines above, counts on top, per-set sizes at the far left.

Writes results/figures/cross_DEG_overlap_upset.png and prints the intersection
sizes (console mirrors the R-side overlap log).

Run: .venv/bin/python scripts/09_upset.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project  # noqa: E402

FACE = "#4C72B0"


def _gene_set(path: Path) -> set[str]:
    df = pd.read_csv(path)
    return set(df["gene"].dropna().astype(str)) if "gene" in df.columns else set()


def main() -> None:
    project = load_project()
    project.ensure_dirs()
    T = project.tables

    disc = _gene_set(T / "GSE202859_DEG_up.csv") | _gene_set(T / "GSE202859_DEG_down.csv")
    val = _gene_set(T / "GSE193258_DEG_up.csv") | _gene_set(T / "GSE193258_DEG_down.csv")
    vdf = pd.read_csv(T / "validated_DEGs.csv")
    validated = set(vdf["gene"].dropna().astype(str))

    sets = [("Discovery", disc), ("Validation", val), ("Validated", validated)]
    gene2mask = {}
    for gene in sorted(disc | val | validated):
        gene2mask[gene] = tuple(int(gene in s) for _, s in sets)
    counts: dict[tuple[int, ...], int] = {}
    for m in gene2mask.values():
        counts[m] = counts.get(m, 0) + 1

    print("Set sizes:", dict(zip((n for n, _ in sets), (len(s) for _, s in sets))))
    print(f"|Discovery ^ Validation| = {len(disc & val)}")
    print(f"|Validated (consistent)  | = {len(validated)}")

    combos = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    n_c, n_s = len(combos), len(sets)

    fig = plt.figure(figsize=(max(6.0, 0.62 * n_c + 2.4), 5.6))
    ax_bar = fig.add_axes([0.30, 0.03, 1 - 0.30, 0.34])
    ax_mat = fig.add_axes([0.30, 0.47, 1 - 0.30, 0.33])
    ax_cnt = fig.add_axes([0.30, 0.83, 1 - 0.30, 0.09])

    xs = list(range(n_c))
    ys = [c for _, c in combos]
    ax_bar.bar(xs, ys, color=FACE, width=0.6)
    for x, y in zip(xs, ys):
        ax_bar.annotate(f"{y:,}", (x, y), textcoords="offset points",
                        xytext=(0, 2), ha="center", fontsize=8)
    ax_bar.set_xticks([])
    ax_bar.set_yticks([])
    ax_bar.set_ylabel("intersection size", fontsize=9)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)

    for i in range(n_s):
        ax_mat.axhline(i, color="#9E9E9E", lw=1.2, zorder=1)
    for x, (mask, _) in zip(xs, combos):
        idxs = [i for i, v in enumerate(mask) if v]
        if len(idxs) > 1:
            ax_mat.plot([x, x], [idxs[0], idxs[-1]], color=FACE, lw=1.8, zorder=2)
        for i in idxs:
            ax_mat.plot(x, i, "o", color=FACE, markersize=10, zorder=3)
    for i, (name, s) in enumerate(sets):
        ax_mat.annotate(f"{name}\n(n={len(s):,})", (-0.35, i), ha="right",
                        va="center", fontsize=9, annotation_clip=False)
    ax_mat.set_xticks([])
    ax_mat.set_yticks([])
    ax_mat.set_xlim(-0.6, n_c - 0.4)
    ax_mat.set_ylim(-0.7, n_s - 0.3)
    for s in ax_mat.spines.values():
        s.set_visible(False)

    ax_cnt.set_ylim(0, 1)
    ax_cnt.set_xticks([])
    ax_cnt.set_yticks([])
    for s in ax_cnt.spines.values():
        s.set_visible(False)
    ax_cnt.set_xlim(-0.6, n_c - 0.4)
    for x, (_, c) in zip(xs, combos):
        ax_cnt.annotate(f"{c:,}", (x, 0.35), ha="center", fontsize=8.5)

    fig.suptitle("Cross-dataset DEG overlap (GSE202859 vs GSE193258)", fontsize=12)
    out = project.root / "results" / "figures" / "cross_DEG_overlap_upset.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

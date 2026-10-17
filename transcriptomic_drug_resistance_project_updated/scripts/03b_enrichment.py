#!/usr/bin/env python
"""Stage 5 - Functional / pathway enrichment (GO-BP, KEGG, Reactome, GSEA).

Self-contained replacement for the clusterProfiler / ReactomePA / fgsea step:
gene-set sources are downloaded once into ``data/annotation/`` and analysed with
a hypergeometric ORA (+ BH FDR) and a pre-ranked GSEA. Works offline once the
gene-set files are cached, so no Bioconductor host is required.

Inputs (produced by the R DEG track):
  results/tables/<ACC>_DEG_full.csv        (gene, log2FoldChange, ...)
  results/tables/<ACC>_DEG_significant.csv (FDR<0.05, |log2FC|>1)
  results/tables/validated_DEGs.csv        (shared, direction-consistent DEGs)

Outputs:
  results/tables/{enrichment,gsea}_<TAG>_<SOURCE>.csv
  results/figures/{enrichment,gsea}_<TAG>_<SOURCE>.png

Run: python scripts/03b_enrichment.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enrich import analysis, gene_sets  # noqa: E402
from ml.config import load_project  # noqa: E402

SOURCE_LABEL = {"GO_BP": "GO Biological Process", "KEGG": "KEGG",
                "Reactome": "Reactome"}


def _read(path):
    return pd.read_csv(path) if path.is_file() else None


def _universe_symbols(project, accession):
    """Measured genes for a cohort (columns of expression_processed.csv)."""
    f = project.cohort_dir(accession) / "expression_processed.csv"
    if not f.is_file():
        return None
    return list(pd.read_csv(f, nrows=0).columns)[1:]


def dotplot(df, title, out_png, top_n=15):
    import numpy as _np
    d = df[df["overlap"] > 0].nsmallest(top_n, "pvalue").copy()
    if d.empty:
        return
    d["neglog10padj"] = -_np.log10(d["padj"].clip(lower=1e-300))
    d = d.sort_values("neglog10padj")
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(d) + 2))
    sizes = d["overlap"].to_numpy()
    sc = ax.scatter(d["neglog10padj"], range(len(d)),
                    s=40 + 260 * (sizes / max(sizes.max(), 1)),
                    c=d["fold_enrichment"], cmap="viridis", edgecolor="k", linewidth=0.4)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([t[:60] for t in d["term_name"]], fontsize=8)
    ax.set_xlabel("-log10(FDR)")
    ax.set_title(title, fontsize=10)
    cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("fold enrichment")
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def gsea_barplot(df, title, out_png, top_n=15):
    d = df.reindex(df["NES"].abs().sort_values(ascending=False).index).head(top_n)
    if d.empty:
        return
    d = d.sort_values("NES")
    colors = ["#c0392b" if v > 0 else "#2471a3" for v in d["NES"]]
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(d) + 2))
    ax.barh(range(len(d)), d["NES"], color=colors)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([t[:60] for t in d["term_name"]], fontsize=8)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("NES (z-score vs size-matched null)")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    plt.close(fig)


def main():
    project = load_project()
    project.ensure_dirs()
    cfge = project.cfg["deg"]["enrichment"]
    sources = [s.upper() if s != "BP" else "GO_BP" for s in cfge["ontologies"]]
    sources = [s if s in gene_sets.SOURCES else
               {"BP": "GO_BP", "KEGG": "KEGG", "REACTOME": "Reactome"}[s]
               for s in sources]
    min_size = cfge.get("gsea_min_size", 15)
    max_size = cfge.get("gsea_max_size", 500)
    n_perm = cfge.get("gsea_permutations", 1000)
    top_n = int(cfge.get("top_n_plot", 15))

    print("Ensuring gene-set annotation files (data/annotation/)...")
    files = gene_sets.ensure_gene_set_files(project.annotation)
    if not files:
        print("  [skip] no gene-set files available (offline); enrichment skipped.")
        return
    print("  parsed sources:", ", ".join(sorted(k for k in files)))

    print("Loading gene sets...")
    gi = project.annotation / "Homo_sapiens.gene_info.gz"
    if not gi.is_file():
        print("  [skip] gene_info missing; cannot map Entrez->SYMBOL for KEGG/Reactome.")
        return
    sym2ez = gene_sets.symbol_entrez_map(gi)
    ez2sym = {v: k for k, v in sym2ez.items()}
    gsets = gene_sets.load_gene_sets(project.annotation, sources, files=files, ez2sym=ez2sym)
    for src, d in gsets.items():
        print(f"  {src}: {len(d)} gene sets (symbol space)")

    disc = project.cfg["cohorts"]["discovery"]["accession"]
    vald = project.cfg["cohorts"]["validation"]["accession"]
    valid = _read(project.tables / "validated_DEGs.csv")

    tasks = []
    for acc in (disc, vald):
        sig = _read(project.tables / f"{acc}_DEG_significant.csv")
        full = _read(project.tables / f"{acc}_DEG_full.csv")
        universe = _universe_symbols(project, acc)
        if sig is None or full is None or universe is None:
            print(f"  [skip] {acc}: DEG tables / expression matrix missing.")
            continue
        tasks.append((acc, acc, list(sig["gene"]), universe,
                      full.set_index("gene")["log2FoldChange"]))

    if valid is not None:
        universe = sorted(set(_universe_symbols(project, disc) or []) |
                          set(_universe_symbols(project, vald) or []))
        # ORA only for the validated signature: a gene set of 348 DEGs is not a
        # full ranked transcriptome, so a pre-ranked GSEA would be biased.
        tasks.append(("validated", "validated", list(valid["gene"]), universe, None))

    for tag, label, query_sym, universe_sym, rank_sym in tasks:
        query = set(query_sym)
        univ = set(universe_sym)
        print(f"\n== enrichment: {tag} ({len(query)} query / {len(univ)} universe symbols) ==")
        for src, gs in gsets.items():
            ora = analysis.ora(query, univ, gs, min_size, max_size)
            if not ora.empty:
                out = project.tables / f"enrichment_{tag}_{src}.csv"
                ora.to_csv(out, index=False)
                dotplot(ora, f"{SOURCE_LABEL[src]} ORA - {tag}",
                        project.figures / f"enrichment_{tag}_{src}_dotplot.png",
                        top_n=top_n)
                print(f"  {src}: {len(ora)} terms ({(ora['padj']<0.05).sum()} FDR<0.05) -> {out.name}")
            else:
                print(f"  {src}: no significant over-representation")

            if rank_sym is not None:
                gs_df = analysis.preranked_gsea(
                    rank_sym, gs, min_size, max_size, n_perm=n_perm)
                if not gs_df.empty:
                    out = project.tables / f"gsea_{tag}_{src}.csv"
                    gs_df.to_csv(out, index=False)
                    gsea_barplot(gs_df, f"{SOURCE_LABEL[src]} GSEA - {tag}",
                                 project.figures / f"gsea_{tag}_{src}.png",
                                 top_n=top_n)
                    print(f"    GSEA: {len(gs_df)} sets -> {out.name}")

    print("\nStage 5 complete.")


if __name__ == "__main__":
    main()

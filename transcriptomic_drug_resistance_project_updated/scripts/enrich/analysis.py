"""Over-representation (hypergeometric) and pre-ranked GSEA statistics.

Pure numpy/scipy/pandas implementations so no Bioconductor (clusterProfiler /
ReactomePA / fgsea) is needed. All inputs use one identifier space (gene symbols).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import hypergeom, norm


def bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values."""
    p = np.asarray(pvals, dtype=float)
    n = p.size
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n, dtype=float)
    out[order] = np.clip(adj, 0, 1)
    return out


def ora(query, universe, gene_sets,
        min_size: int = 15, max_size: int = 500,
        min_overlap: int = 1) -> pd.DataFrame:
    """Over-representation analysis for one query set against many gene sets.

    All sets are keyed by the same identifier space (gene symbols here).

    Parameters
    ----------
    query : iterable of gene ids (the DEGs)
    universe : iterable of gene ids measured in the experiment
    gene_sets : {term_id: {"name": str, "genes": set(id)}}
    """
    universe = set(str(g) for g in universe)
    query = set(str(g) for g in query) & universe
    M = len(universe)
    K = len(query)
    rows = []
    if M == 0 or K == 0:
        return pd.DataFrame()
    for tid, info in gene_sets.items():
        members = set(str(g) for g in info["genes"]) & universe
        n = len(members)
        if n < min_size or n > max_size:
            continue
        overlap = members & query
        k = len(overlap)
        if k < min_overlap:
            continue
        p = hypergeom.sf(k - 1, M, n, K)
        expected = K * n / M
        fold = (k / K) / (n / M)
        genes = sorted(overlap)
        rows.append({
            "term_id": tid,
            "term_name": info["name"],
            "set_size": n,
            "overlap": k,
            "query_size": K,
            "expected": expected,
            "fold_enrichment": fold,
            "pvalue": p,
            "genes": ";".join(genes),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["padj"] = bh_fdr(df["pvalue"].to_numpy())
    df = df.sort_values("pvalue").reset_index(drop=True)
    return df


def _enrichment_score(n_genes: int, hits: np.ndarray) -> float:
    """Standard KS-style GSEA enrichment score on a pre-sorted ranked list.

    n_genes : total number of ranked genes
    hits    : sorted positions (0-based) of the set members in the ranking
    """
    s = len(hits)
    if s == 0 or s == n_genes:
        return 0.0
    weights = np.full(n_genes, -1.0 / (n_genes - s))
    weights[hits] = 1.0 / s
    cs = np.cumsum(weights)
    imax = int(np.argmax(cs))
    imin = int(np.argmin(cs))
    return float(cs[imax] if cs[imax] > -cs[imin] else cs[imin])


def preranked_gsea(ranking: pd.Series, gene_sets,
                   min_size: int = 15, max_size: int = 500,
                   n_perm: int = 1000, n_buckets: int = 40,
                   seed: int = 42) -> pd.DataFrame:
    """Pre-ranked GSEA with a size-bucketed permutation null.

    ``ranking`` is a Series indexed by gene id (symbols here), sorted internally
    by value (descending). Because the null distribution of the enrichment score
    depends on the gene-set size, we estimate it per size bucket from random gene
    sets. Returns ES, NES (= z-score vs the bucket null), p, padj.
    """
    r = ranking.dropna().sort_values(ascending=False)
    genes = [str(g) for g in r.index]
    n_genes = len(genes)
    if n_genes == 0:
        return pd.DataFrame()
    pos = {g: i for i, g in enumerate(genes)}
    rng = np.random.default_rng(seed)

    # candidate sets within size range
    cand = {}
    for tid, info in gene_sets.items():
        hits = sorted(pos[g] for g in info["genes"] if str(g) in pos)
        if min_size <= len(hits) <= max_size:
            cand[tid] = np.asarray(hits, dtype=int)
    if not cand:
        return pd.DataFrame()

    # size buckets -> null mean/sd of ES
    sizes = np.array([len(h) for h in cand.values()])
    lo, hi = max(min_size, sizes.min()), min(max_size, sizes.max())
    if hi <= lo:
        edges = np.array([lo - 0.5, hi + 0.5])
    else:
        edges = np.linspace(lo - 0.5, hi + 0.5, n_buckets + 1)
    bucket_null: dict[int, tuple[float, float]] = {}
    for b in range(len(edges) - 1):
        s_lo = int(np.ceil(edges[b]))
        s_hi = int(np.floor(edges[b + 1]))
        if s_hi < s_lo:
            continue
        # sample a representative size per bucket for the null
        s = max(s_lo, min(s_hi, (s_lo + s_hi) // 2))
        es_null = np.empty(n_perm)
        for i in range(n_perm):
            hits = np.sort(rng.choice(n_genes, size=s, replace=False))
            es_null[i] = _enrichment_score(n_genes, hits)
        bucket_null[b] = (float(es_null.mean()), float(es_null.std(ddof=1) or 1e-9))

    def bucket_of(size: int) -> int:
        return int(np.clip(np.searchsorted(edges, size, side="right") - 1,
                           0, len(edges) - 2))

    rows = []
    for tid, hits in cand.items():
        es = _enrichment_score(n_genes, hits)
        mean, sd = bucket_null.get(bucket_of(len(hits)), (0.0, 1.0))
        z = (es - mean) / sd if sd else 0.0
        p = float(2 * norm.sf(abs(z))) if z != 0 else 1.0
        members = sorted(gene_sets[tid]["genes"])
        rows.append({
            "term_id": tid,
            "term_name": gene_sets[tid]["name"],
            "set_size": len(hits),
            "ES": es,
            "NES": z,
            "pvalue": p,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["padj"] = bh_fdr(df["pvalue"].to_numpy())
    df = df.reindex(df["NES"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    return df

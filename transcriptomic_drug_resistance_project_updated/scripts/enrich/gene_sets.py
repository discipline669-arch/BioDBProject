"""Gene-set sources for Stage 5 enrichment (GO-BP, KEGG, Reactome).

Self-contained alternative to clusterProfiler / ReactomePA: the source files are
downloaded once into ``data/annotation/`` and parsed with the standard library +
pandas, so no Bioconductor host is required.

Sources
-------
* GO-BP      : Enrichr GMT ``GO_Biological_Process_2023`` (gene symbols)
* KEGG       : KEGG REST ``link/hsa/pathway`` + ``list/pathway/hsa`` (Entrez)
* Reactome   : ``NCBI2Reactome_All_Levels.txt`` (Entrez -> pathway)

Everything is unified on gene symbols: KEGG/Reactome Entrez IDs are converted
with ``ez2sym`` derived from ``Homo_sapiens.gene_info.gz``.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import pandas as pd

SOURCES = ("GO_BP", "KEGG", "Reactome")

FILES = {
    "go_gmt": (
        "https://maayanlab.cloud/Enrichr/geneSetLibrary"
        "?mode=text&libraryName=GO_Biological_Process_2023",
        "GO_Biological_Process_2023.gmt",
    ),
    "kegg_link": (
        "https://rest.kegg.jp/link/hsa/pathway",
        "kegg_hsa_pathway_link.tsv",
    ),
    "kegg_list": (
        "https://rest.kegg.jp/list/pathway/hsa",
        "kegg_hsa_pathway_list.tsv",
    ),
    "reactome": (
        "https://reactome.org/download/current/NCBI2Reactome_All_Levels.txt",
        "NCBI2Reactome_All_Levels.txt",
    ),
}

_UA = {"User-Agent": "Mozilla/5.0 (compatible; BioDBProject/1.0)"}


def _resume_download(url: str, dest: Path, timeout: int = 900) -> bool:
    """Robust download via curl (resume + retries); falls back to urllib."""
    part = dest.with_suffix(dest.suffix + ".part")
    curl = shutil.which("curl")
    if curl:
        cmd = [curl, "-L", "--fail", "--retry", "4", "--retry-delay", "3",
               "--retry-all-errors", "--connect-timeout", "30",
               "--max-time", str(timeout), "-C", "-"]
        if sys.platform == "win32":
            cmd.append("--ssl-no-revoke")
        cmd += ["-A", _UA["User-Agent"], "-o", str(part), url]
        try:
            rc = subprocess.run(cmd, capture_output=True).returncode
            if rc == 0 and part.is_file() and part.stat().st_size > 0:
                part.replace(dest)
                return True
        except Exception as exc:  # pragma: no cover
            print(f"    [warn] curl failed ({url}): {exc}")
    # urllib fallback (single attempt)
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(part, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        part.replace(dest)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"    [warn] download failed ({url}): {exc}")
        return False


def download(url: str, dest: Path, timeout: int = 900) -> bool:
    """Ensure ``dest`` exists (skips if already present). True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 0:
        return True
    return _resume_download(url, dest, timeout)


def ensure_gene_set_files(annot_dir: Path) -> dict[str, Path]:
    """Download any missing source files; return the ones that are present."""
    annot_dir = Path(annot_dir)
    present: dict[str, Path] = {}
    for key, (url, name) in FILES.items():
        dest = annot_dir / name
        if download(url, dest):
            present[key] = dest
    return present


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def parse_enrichr_gmt(path: Path) -> dict[str, dict]:
    """Enrichr GMT library -> gene sets keyed by gene SYMBOL.

    Line format: ``term<TAB>description_or_url<TAB>gene1<TAB>gene2...``.
    """
    out: dict[str, dict] = {}
    with open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 3:
                continue
            term = f[0].strip()
            genes = {g.strip() for g in f[2:] if g.strip()}
            if term and genes:
                out[term] = {"name": term, "genes": genes}
    return out


def parse_kegg(link_path: Path, list_path: Path) -> dict[str, dict]:
    names: dict[str, str] = {}
    with open(list_path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                names[parts[0]] = parts[1].replace(" - Homo sapiens (human)", "")
    genes: dict[str, set[str]] = {}
    with open(link_path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            a, b = parts[0], parts[1]
            pathway = (a if a.startswith("path:") else b).replace("path:", "")
            gene = b if a.startswith("path:") else a
            gene_id = gene.split(":")[-1]
            genes.setdefault(pathway, set()).add(gene_id)
    return {pid: {"name": names.get(pid, pid), "genes": g} for pid, g in genes.items()}


def parse_reactome(path: Path) -> dict[str, dict]:
    genes: dict[str, set[str]] = {}
    names: dict[str, str] = {}
    with open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 6:
                continue
            gid, rid, _url, name, _ev, species = f[:6]
            if species != "Homo sapiens":
                continue
            genes.setdefault(rid, set()).add(gid)
            names.setdefault(rid, name)
    return {rid: {"name": names.get(rid, rid), "genes": g} for rid, g in genes.items()}


def _entrez_to_symbol(gsets: dict[str, dict], ez2sym: dict[str, str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for tid, info in gsets.items():
        genes = {ez2sym[g] for g in info["genes"] if g in ez2sym}
        if genes:
            out[tid] = {"name": info["name"], "genes": genes}
    return out


def load_gene_sets(annot_dir: Path, sources=SOURCES,
                   files: dict[str, Path] | None = None,
                   ez2sym: dict[str, str] | None = None) -> dict[str, dict[str, dict]]:
    """Return ``{source: {term_id: {"name": str, "genes": set[symbol]}}}``.

    Everything is unified on HGNC symbols: GO comes from an Enrichr GMT
    (already symbols); KEGG/Reactome are Entrez-based and are converted with
    ``ez2sym`` (Entrez GeneID -> symbol).
    """
    annot_dir = Path(annot_dir)
    files = files if files is not None else {k: annot_dir / n for k, (_, n) in FILES.items()}
    out: dict[str, dict[str, dict]] = {}

    def _have(*keys):
        return all(k in files and files[k].is_file() for k in keys)

    if "GO_BP" in sources and _have("go_gmt"):
        out["GO_BP"] = parse_enrichr_gmt(files["go_gmt"])
    if "KEGG" in sources and _have("kegg_link", "kegg_list"):
        kegg = parse_kegg(files["kegg_link"], files["kegg_list"])
        out["KEGG"] = _entrez_to_symbol(kegg, ez2sym) if ez2sym else kegg
    if "Reactome" in sources and _have("reactome"):
        reac = parse_reactome(files["reactome"])
        out["Reactome"] = _entrez_to_symbol(reac, ez2sym) if ez2sym else reac
    return out


def symbol_entrez_map(gene_info_gz: Path) -> dict[str, str]:
    """Symbol -> Entrez GeneID (from NCBI gene_info)."""
    df = pd.read_csv(gene_info_gz, sep="\t", comment="#", header=None, dtype=str)
    df = df.iloc[:, [1, 2]]
    df.columns = ["GeneID", "Symbol"]
    df = df.dropna()
    return dict(zip(df["Symbol"], df["GeneID"]))

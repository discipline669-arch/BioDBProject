"""Cohort loading, gene-space alignment, and train/test assembly."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import Project


@dataclass
class Cohort:
    accession: str
    X: pd.DataFrame          # samples x genes (normalised expression)
    y: pd.Series             # condition, values in {"Sensitive","Resistant"}
    groups: pd.Series        # group key (cell_line) for group-aware splitting
    meta: pd.DataFrame       # full coldata rows for the retained samples


def _processed_csv(project: Project, accession: str) -> Path:
    return project.cohort_dir(accession) / "expression_processed.csv"


def load_cohort(project: Project, accession: str, exclude=("Normal",)) -> Cohort:
    """Load a processed cohort, dropping excluded conditions (e.g. Normals)."""
    csv = _processed_csv(project, accession)
    coldata_csv = project.cohort_dir(accession) / "coldata.csv"
    if not csv.is_file():
        raise FileNotFoundError(
            f"{csv} not found. Run the R track (scripts/02_preprocess_qc.R) first."
        )
    if not coldata_csv.is_file():
        raise FileNotFoundError(f"{coldata_csv} not found. Run scripts/01_build_metadata.R.")

    expr = pd.read_csv(csv)
    first = expr.columns[0]
    expr = expr.set_index(first)
    expr.index.name = "sample"

    cd = pd.read_csv(coldata_csv)
    cd["sample"] = cd["sample"].astype(str)
    cd["condition"] = cd["condition"].astype(str)

    keep = cd["condition"].isin(["Sensitive", "Resistant"])
    if exclude:
        keep &= ~cd["condition"].isin(exclude)
    cd = cd[keep].copy()

    shared = [s for s in cd["sample"] if s in expr.index]
    if len(shared) < 2:
        raise ValueError(
            f"{accession}: only {len(shared)} samples overlap between coldata and matrix. "
            f"check sample ids.\n  coldata: {list(cd['sample'][:5])}\n  matrix: {list(expr.index[:5])}"
        )
    cd = cd.set_index("sample").loc[shared]
    X = expr.loc[shared]
    y = cd["condition"]
    groups = cd["donor"] if "donor" in cd.columns else pd.Series(shared, index=shared)

    return Cohort(accession=accession, X=X, y=y, groups=groups, meta=cd.reset_index())


def align_gene_space(*cohorts: Cohort) -> tuple[Cohort, ...]:
    """Restrict all cohorts to the intersected, non-constant gene space.

    Genes with zero variance in any cohort are dropped: they carry no signal and
    make univariate F-tests divide by zero (``msw == 0``).
    """
    common_set: set[str] | None = None
    for c in cohorts:
        cols = set(c.X.columns)
        common_set = cols if common_set is None else (common_set & cols)
    common = sorted(common_set or [])
    for c in cohorts:
        var = c.X.loc[:, common].var(axis=0)
        common = [g for g in common if var[g] > 0]
    out = []
    for c in cohorts:
        c2 = Cohort(accession=c.accession, X=c.X.loc[:, common].copy(), y=c.y,
                    groups=c.groups, meta=c.meta)
        out.append(c2)
    return tuple(out)


def encode_labels(y: pd.Series) -> pd.Series:
    """Sensitive -> 0, Resistant -> 1."""
    return y.map({"Sensitive": 0, "Resistant": 1}).astype(int)

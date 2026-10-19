"""Cohort loading, gene-space alignment, and train/test assembly."""
from __future__ import annotations

import warnings
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


def resolve_groups(cd: pd.DataFrame, project: Project, accession: str) -> pd.Series:
    """Group-aware CV splitting key (see config: cohorts.*.group_by).

    Resolution chain (first column found wins):
      1. the cohort's configured ``group_by`` column (default ``cell_line``)
      2. ``cell_line``, then ``donor`` (legacy columns)
      3. per-sample groups as a loud last resort (one group per sample)

    Replicates of a cell line must never land in different folds.
    """
    cohort_cfg = project.cfg.get("cohorts", {}).get(accession, {})
    cv_cfg = project.cfg.get("ml", {}).get("cv", {})
    preferred = cohort_cfg.get("group_by") or cv_cfg.get("group_key") or "cell_line"
    candidates = [g for g in (preferred, "cell_line", "donor") if g]
    for col in candidates:
        if col in cd.columns:
            groups = cd[col].astype(str)
            print(f"  {accession}: group key = '{col}' ({groups.nunique()} unique groups)")
            return groups
    warnings.warn(
        f"{accession}: none of the group columns {candidates} found in coldata; "
        "falling back to per-sample groups (CV will NOT be group-aware)."
    )
    ids = [str(s) for s in (cd["sample"] if "sample" in cd.columns else cd.index)]
    return pd.Series(ids, index=cd.index)


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
    groups = resolve_groups(cd, project, accession)

    return Cohort(accession=accession, X=X, y=y, groups=groups, meta=cd.reset_index())


def align_gene_space(*cohorts: Cohort) -> tuple[Cohort, ...]:
    """Restrict all cohorts to the intersected, non-constant gene space.

    Genes with zero variance in ANY cohort are dropped: they carry no signal
    and make univariate F-tests divide by zero (``msw == 0``). Every filter
    step logs what it drops (fix X5: no silent shrinking of the feature
    space); per-cohort counts are computed over the full initial
    intersection so the log cannot understate the drops.
    """
    common_set: set[str] | None = None
    for c in cohorts:
        cols = set(c.X.columns)
        common_set = cols if common_set is None else (common_set & cols)
    measured = sorted(common_set or [])
    print(f"  align_gene_space: {len(measured)} genes measured in all "
          f"{len(cohorts)} cohort(s)")
    zero_var_all = set()
    NAME_CAP = 20
    for c in cohorts:
        var = c.X.var(axis=0)                       # over the cohort's own columns
        bad = [g for g in c.X.columns if not (var[g] > 0)]
        zero_var_all |= set(bad)
        not_shared = sorted(set(c.X.columns) - set(measured))
        shown = ", ".join(bad[:NAME_CAP]) + (f" ... (+{len(bad) - NAME_CAP} more)"
                                             if len(bad) > NAME_CAP else "")
        shown_ns = ", ".join(not_shared[:NAME_CAP]) + \
            (f" ... (+{len(not_shared) - NAME_CAP} more)" if len(not_shared) > NAME_CAP else "")
        print(f"  align_gene_space: {c.accession}: "
              f"{len(bad)} zero-variance gene(s) in this cohort [{shown}], "
              f"{len(not_shared)} gene(s) measured only here [{shown_ns}]")
    common = [g for g in measured if g not in zero_var_all]
    print(f"  align_gene_space: final aligned space = {len(common)} genes "
          f"({len(measured) - len(common)} dropped in total)")
    out = []
    for c in cohorts:
        c2 = Cohort(accession=c.accession, X=c.X.loc[:, common].copy(), y=c.y,
                    groups=c.groups, meta=c.meta)
        out.append(c2)
    return tuple(out)


def encode_labels(y: pd.Series) -> pd.Series:
    """Sensitive -> 0, Resistant -> 1."""
    return y.map({"Sensitive": 0, "Resistant": 1}).astype(int)

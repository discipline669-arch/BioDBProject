#!/usr/bin/env python
"""D7 - washout sensitivity: apply the LOCKED discovery models to the excluded
GSE193258 time-course samples (osi_acute, short_washout, long_washout_*, plus
DMSO/DTP kept samples as sane anchors).

Requires (in this order):
  * persisted models from 05_train_models.py (D9): results/models/*.joblib
  * the extended matrix from scripts/02b_vst_extended.R:
    data/<ACC>/expression_vst_extend.csv + washout_ext_coldata.csv

Approximations, documented up front:
  * the VST for the extension is refit on ALL 60 samples (blind), while the
    primary model was trained on the 18-sample fit - small distribution shift;
  * predictions are P(Resistant) per sample; no accuracy/AUC is claimed for
    time-course samples (they have no two-class labels by design).
  * two prediction schemes are reported: train_stats (pipe's own discovery
    scaler, strict) and target_z (scaler refit on the time-course rows,
    transductive) - mirroring the external-validation duality (D1).

Outputs:
  results/tables/washout_sensitivity.csv            per-sample probabilities
  results/tables/washout_sensitivity_groups.csv     group means per config
  results/figures/washout_sensitivity.png           strip plot, primary config

Run: .venv/bin/python scripts/10_washout_sensitivity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project  # noqa: E402

PRIMARY = ("LogisticRegression", 50)   # D2 pre-registered config


def _load_models(models_dir: Path, accession: str):
    out = []
    for p in sorted(models_dir.glob(f"{accession}_*_K*.joblib")):
        bundle = joblib.load(p)
        out.append(bundle)
    return out


def _prob_transductive(pipe, X: pd.DataFrame) -> np.ndarray:
    """Mirror transfer()'s target_z: scaler refit on the applied rows only."""
    sel = pipe.named_steps["select"]
    clf = pipe.named_steps["clf"]
    x_sel = sel.transform(X)
    ss = StandardScaler().fit(x_sel)
    return clf.predict_proba(ss.transform(x_sel))[:, 1]


def main():
    project = load_project()
    project.ensure_dirs()
    disc_acc = project.cfg["cohorts"]["discovery"]["accession"]
    val_acc = project.cfg["cohorts"]["validation"]["accession"]

    ext_csv = project.cohort_dir(val_acc) / "expression_vst_extend.csv"
    cd_csv = project.cohort_dir(val_acc) / "washout_ext_coldata.csv"
    if not ext_csv.is_file() or not cd_csv.is_file():
        raise SystemExit("run scripts/02b_vst_extend.R first "
                         f"(missing {ext_csv.name} / {cd_csv.name})")

    wide = pd.read_csv(ext_csv, index_col="gene")
    Xw = wide.T                       # samples x genes
    cd = pd.read_csv(cd_csv, index_col="sample").reindex(Xw.index)

    bundles = _load_models(project.models, disc_acc)
    if not bundles:
        raise SystemExit("no persisted discovery models - run 05_train_models.py "
                         "with model persistence (D9) first")

    rows, group_rows = [], []
    for b in bundles:
        pipe = b["pipeline"]
        cols = list(pipe.feature_names_in_)
        missing = [c for c in cols if c not in Xw.columns]
        if missing:
            print(f"  [skip] {b['model']} K={b['k']}: {len(missing)} training "
                  "features missing from the extended matrix")
            continue
        Xm = Xw[cols]
        prob_strict = pipe.predict_proba(Xm)[:, 1]
        prob_trans = _prob_transductive(pipe, Xm)
        for scheme, prob in (("train_stats", prob_strict),
                             ("target_z", prob_trans)):
            rows.append(pd.DataFrame({
                "sample": Xm.index,
                "cell_line": cd["cell_line"].to_numpy(),
                "group": cd["group"].to_numpy(),
                "keep": cd["keep"].to_numpy(),
                "discovery_model": b["model"], "k": b["k"], "scheme": scheme,
                "prob_resistant": prob,
            }))
        g = pd.DataFrame({"group": cd["group"].to_numpy(),
                          "train_stats": prob_strict, "target_z": prob_trans})
        grp = g.groupby("group")[["train_stats", "target_z"]].mean()
        for gid, r in grp.iterrows():
            group_rows.append({"model": b["model"], "k": b["k"],
                               "group": gid, "n": int((g["group"] == gid).sum()),
                               "prob_resistant_train_stats": r["train_stats"],
                               "prob_resistant_target_z": r["target_z"]})

    per_sample = pd.concat(rows, ignore_index=True)
    groups = pd.DataFrame(group_rows)
    out1 = project.tables / "washout_sensitivity.csv"
    out2 = project.tables / "washout_sensitivity_groups.csv"
    per_sample.to_csv(out1, index=False)
    groups.to_csv(out2, index=False)
    print(f"Wrote {out1.name} ({len(per_sample)} rows) and {out2.name}")

    # Primary-config visual (D2): strip plot of P(Resistant) by group
    sub = per_sample[(per_sample["discovery_model"] == PRIMARY[0]) &
                     (per_sample["k"] == PRIMARY[1]) &
                     (per_sample["scheme"] == "train_stats")]
    if not sub.empty:
        order = ["Parental_or_DMSO", "osi_acute", "short_washout",
                 *[g for g in sorted(sub["group"].unique())
                   if g.startswith("long_washout")],
                 "DTP"]
        order = [g for g in order if g in set(sub["group"])]
        fig, ax = plt.subplots(figsize=(8, 4.2))
        rng = np.random.default_rng(0)
        for i, gname in enumerate(order):
            v = sub.loc[sub["group"] == gname, "prob_resistant"].to_numpy()
            x = i + rng.uniform(-0.16, 0.16, size=len(v))
            ax.scatter(x, v, s=28, color="#4C72B0", alpha=0.85, edgecolor="k",
                       linewidth=0.4)
            ax.hlines(v.mean(), i - 0.25, i + 0.25, color="#c0392b", lw=2)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels(order, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel("P(Resistant) - train_stats")
        ax.set_title(f"Washout sensitivity (locked discovery model: {PRIMARY[0]}, "
                     f"K={PRIMARY[1]}; red = group mean)")
        ax.axhline(0.5, color="grey", ls="--", lw=0.8)
        fig.tight_layout()
        figp = project.figures / "washout_sensitivity.png"
        fig.savefig(figp, dpi=200)
        plt.close(fig)
        print(f"Wrote {figp.name}")

    # console digest for the D2 primary config
    pg = groups[(groups["model"] == PRIMARY[0]) & (groups["k"] == PRIMARY[1])]
    if not pg.empty:
        print("\nPrimary-config group means (P(Resistant), train_stats):")
        for _, r in pg.sort_values("prob_resistant_train_stats").iterrows():
            print(f"  {r['group']:18s} n={r['n']:2d}  {r['prob_resistant_train_stats']:.3f}"
                  f"  (target_z {r['prob_resistant_target_z']:.3f})")


if __name__ == "__main__":
    main()

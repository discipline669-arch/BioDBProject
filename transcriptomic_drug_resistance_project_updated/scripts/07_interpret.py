#!/usr/bin/env python
"""Phase 7 - Interpretation (SHAP, coefficients, permutation importance) and
the final candidate biomarker panel.

Fits each model on the discovery cohort (the pipeline used for clinical
transfer), computes SHAP values / coefficients / permutation importance, and
assembles a ranked candidate panel combining:
    stability selection frequency (Phase 4)
  + nested-CV selection frequency (Phase 5)
  + mean |SHAP| (this phase)
  + DEG log2FC where available

Outputs:
  results/tables/shap_importance.csv
  results/tables/permutation_importance.csv
  results/tables/biomarker_panel.csv
  results/figures/shap_summary.png, biomarker_panel.png

Run: python scripts/07_interpret.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project, set_global_seed  # noqa: E402
from ml.data import align_gene_space, encode_labels, load_cohort  # noqa: E402
from ml.models import make_pipeline, selected_genes  # noqa: E402


def fit_and_transform(X, y, model, k, cfg, seed):
    pipe = make_pipeline(model, k, seed, cfg)
    pipe.fit(X, y)
    genes = selected_genes(pipe, X.columns)
    Z = pipe.named_steps["scale"].transform(pipe.named_steps["select"].transform(X))
    return pipe, genes, Z


def shap_importance(model, clf, Z, genes):
    try:
        import shap
    except Exception:
        return None
    try:
        if model == "LogisticRegression":
            expl = shap.LinearExplainer(clf, Z)
            sv = expl.shap_values(Z)
        else:
            expl = shap.TreeExplainer(clf)
            sv = expl.shap_values(Z)
        sv = np.asarray(sv)
        if sv.ndim == 3:            # (samples, features, classes) e.g. RF
            sv = sv[..., 1]
        mean_abs = np.abs(sv).mean(axis=0)
        return pd.Series(mean_abs, index=genes, name="mean_abs_shap")
    except Exception as exc:  # pragma: no cover
        print(f"    [WARN] SHAP failed for {model}: {exc}")
        return None


def main():
    project = load_project()
    set_global_seed(project.cfg["project"]["seed"])
    project.ensure_dirs()

    disc = load_cohort(project, project.cfg["cohorts"]["discovery"]["accession"])
    clin = load_cohort(project, project.cfg["cohorts"]["validation"]["accession"])
    disc, clin = align_gene_space(disc, clin)

    models = project.cfg["ml"]["models"]
    ks = project.cfg["ml"]["feature_counts"]
    rep_k = ks[len(ks) // 2]
    seeds = project.cfg["ml"]["seeds"]
    X, y = disc.X, encode_labels(disc.y)

    shap_rows, perm_rows, coef_rows = [], [], []
    shap_df = None
    for model in models:
        print(f"Interpreting {model} (K={rep_k}) on {disc.accession}...")
        pipe, genes, Z = fit_and_transform(X, y, model, rep_k, project.cfg, seeds[model])
        clf = pipe.named_steps["clf"]

        si = shap_importance(model, clf, Z, genes)
        if si is not None and len(si):
            shap_rows.append(pd.DataFrame({"model": model, "gene": si.index,
                                           "mean_abs_shap": si.to_numpy()}))
            print(f"  top SHAP genes: {list(si.sort_values(ascending=False).head(5).index)}")

        pi = permutation_importance(clf, Z, y, scoring="roc_auc",
                                    n_repeats=20, random_state=project.cfg["project"]["seed"])
        perm_rows.append(pd.DataFrame({"model": model, "gene": genes,
                                       "perm_importance": pi.importances_mean,
                                       "perm_std": pi.importances_std}))

        if model == "LogisticRegression":
            coefs = np.asarray(clf.coef_).ravel()
            coef_rows.append(pd.DataFrame({"model": model, "gene": genes, "coef": coefs}))

    if shap_rows:
        shap_df = pd.concat(shap_rows, ignore_index=True)
        shap_df.to_csv(project.tables / "shap_importance.csv", index=False)
    perm_df = pd.concat(perm_rows, ignore_index=True)
    perm_df.to_csv(project.tables / "permutation_importance.csv", index=False)
    if coef_rows:
        pd.concat(coef_rows, ignore_index=True).to_csv(
            project.tables / "logreg_coefficients.csv", index=False)

    # ---------------- Candidate biomarker panel ----------------
    stab = project.tables / "feature_stability_discovery.csv"
    sel_freq_file = project.tables / "nested_cv_selection_freq.csv"
    parts = []
    if stab.is_file():
        s = pd.read_csv(stab).rename(columns={"stability_freq": "stability"})
        s = s.set_index(s.columns[0] if s.columns[0] != "stability" else "gene")
        parts.append(s[["stability"]])
    if sel_freq_file.is_file():
        sf = pd.read_csv(sel_freq_file)
        dsf = (sf[sf["accession"] == disc.accession]
               .groupby("gene")["selection_freq"].mean().rename("nested_sel_freq"))
        parts.append(dsf.to_frame())
    if shap_rows:
        ds = (shap_df.groupby("gene")["mean_abs_shap"].mean().rename("shap"))
        parts.append(ds.to_frame())

    if not parts:
        print("No panel inputs available; skipping panel.")
        return
    panel = pd.concat(parts, axis=1)
    for col in panel.columns:
        v = panel[col]
        rng = v.max() - v.min()
        panel[f"_{col}_z"] = (v - v.min()) / rng if rng > 0 else 0.0
    score_cols = [c for c in panel.columns if c.startswith("_") and c.endswith("_z")]
    panel["composite"] = panel[score_cols].fillna(0).mean(axis=1)
    panel = panel.sort_values("composite", ascending=False)
    panel.index.name = "gene"
    panel.head(100).to_csv(project.tables / "biomarker_panel.csv")

    # ---------------- Figures ----------------
    if shap_rows:
        top = (shap_df.groupby("gene")["mean_abs_shap"].mean()
               .sort_values(ascending=False).head(20))
        fig, ax = plt.subplots(figsize=(8, 7))
        ax.barh(top.index[::-1], top.to_numpy()[::-1], color="#377eb8")
        ax.set_xlabel("Mean |SHAP|")
        ax.set_title(f"Top 20 candidate genes by mean |SHAP| - {disc.accession}")
        fig.tight_layout(); fig.savefig(project.figures / "shap_summary.png", dpi=300); plt.close(fig)

    top = panel.head(20)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(top.index[::-1], top["composite"].to_numpy()[::-1], color="#e41a1c")
    ax.set_xlabel("Composite score")
    ax.set_title("Top 20 candidate biomarkers (composite)")
    fig.tight_layout(); fig.savefig(project.figures / "biomarker_panel.png", dpi=300); plt.close(fig)

    print(f"\nWrote {project.tables / 'biomarker_panel.csv'}")
    print("Phase 7 complete.")


if __name__ == "__main__":
    main()

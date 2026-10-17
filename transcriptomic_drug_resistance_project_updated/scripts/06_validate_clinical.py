#!/usr/bin/env python
"""Phase 6 - Independent external validation (cross-dataset).

Pipeline is fit on the full discovery cohort (GSE202859) and applied ONCE to the
held-out validation cohort (GSE193258), under two test-normalisations:
    train_stats : validation features scaled with discovery statistics (strict)
    target_z    : validation features scaled with their own statistics (transductive)

Reports ROC-AUC, PR-AUC, sensitivity, specificity, F1 and Brier with stratified
bootstrap 95% CIs, plus calibration, ROC/PR and confusion-matrix figures.

Outputs:
  results/tables/external_validation.csv
  results/tables/external_predictions.csv
  results/figures/external_roc.png, external_pr.png, external_calibration.png, external_confusion.png

Run: python scripts/06_validate_clinical.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (confusion_matrix, ConfusionMatrixDisplay,  # noqa: E402
                             precision_recall_curve, roc_curve)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project, set_global_seed  # noqa: E402
from ml.data import align_gene_space, load_cohort  # noqa: E402
from ml.metrics import binary_metrics, bootstrap_ci, calibration_points  # noqa: E402
from ml.cv import transfer  # noqa: E402


def main():
    project = load_project()
    set_global_seed(project.cfg["project"]["seed"])
    project.ensure_dirs()

    disc = load_cohort(project, project.cfg["cohorts"]["discovery"]["accession"])
    clin = load_cohort(project, project.cfg["cohorts"]["validation"]["accession"])
    disc, clin = align_gene_space(disc, clin)
    print(f"Discovery  {disc.accession}: {disc.X.shape[0]} samples")
    print(f"Validation {clin.accession}: {clin.X.shape[0]} samples "
          f"({dict(clin.y.value_counts())})")

    models = project.cfg["ml"]["models"]
    ks = project.cfg["ml"]["feature_counts"]
    seeds = project.cfg["ml"]["seeds"]
    n_boot = project.cfg["ml"]["bootstrap_ci"]

    rows, pred_frames = [], []
    for model in models:
        for k in ks:
            t = transfer(disc, clin, model, k, project.cfg, seeds[model])
            if not t["preds"]:
                print(f"  {model} K={k}: <2 features selected, skipped")
                continue
            y = t["y"].to_numpy()
            for norm, prob in t["preds"].items():
                met = binary_metrics(y, prob)
                row = {"model": model, "k": k, "normalization": norm,
                       "n_genes": len(t["genes"]), **met}
                for metric in ("roc_auc", "pr_auc", "sensitivity", "specificity", "f1", "brier"):
                    pt, lo, hi = bootstrap_ci(y, prob, metric, n_boot=n_boot,
                                              seed=project.cfg["project"]["seed"])
                    row[f"{metric}_lo"], row[f"{metric}_hi"] = lo, hi
                rows.append(row)

                for sample, p, yy in zip(t["target_index"], prob, y):
                    pred_frames.append({"model": model, "k": k, "normalization": norm,
                                        "sample": sample, "y": int(yy), "prob": float(p)})
                print(f"  {model:<18} K={k:<4} {norm:<11} "
                      f"AUC={met['roc_auc']:.3f} PR-AUC={met['pr_auc']:.3f} "
                      f"sens={met['sensitivity']:.2f} spec={met['specificity']:.2f}")

    ext = pd.DataFrame(rows)
    preds = pd.DataFrame(pred_frames)
    ext.to_csv(project.tables / "external_validation.csv", index=False)
    preds.to_csv(project.tables / "external_predictions.csv", index=False)

    # --- Figures at the representative K ---
    rep_k = ks[len(ks) // 2]
    sub = preds[(preds["k"] == rep_k) & (preds["normalization"] == "train_stats")]

    fig, ax = plt.subplots(figsize=(6, 5))
    for model, ms in sub.groupby("model"):
        if ms["y"].nunique() < 2:
            continue
        fpr, tpr, _ = roc_curve(ms["y"], ms["prob"])
        auc = binary_metrics(ms["y"], ms["prob"])["roc_auc"]
        ax.plot(fpr, tpr, label=f"{model} (AUC={auc:.2f})")
    ax.plot([0, 1], [0, 1], color="grey", ls="--", lw=1)
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title(f"External validation (GSE193258) ROC (K={rep_k}, train_stats)")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(); fig.savefig(project.figures / "external_roc.png", dpi=300); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    for model, ms in sub.groupby("model"):
        if ms["y"].nunique() < 2:
            continue
        pr, rc, _ = precision_recall_curve(ms["y"], ms["prob"])
        ax.plot(rc, pr, label=model)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title(f"External validation (GSE193258) PR (K={rep_k}, train_stats)")
    ax.legend(loc="lower left", fontsize=8)
    fig.tight_layout(); fig.savefig(project.figures / "external_pr.png", dpi=300); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    for model, ms in sub.groupby("model"):
        if ms["y"].nunique() < 2:
            continue
        mp, fp, _ = calibration_points(ms["y"], ms["prob"], n_bins=4)
        ax.plot(mp, fp, marker="o", label=model)
    ax.plot([0, 1], [0, 1], color="grey", ls="--", lw=1)
    ax.set_xlabel("Mean predicted probability"); ax.set_ylabel("Observed fraction")
    ax.set_title(f"Calibration - external validation (K={rep_k}, train_stats)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(project.figures / "external_calibration.png", dpi=300); plt.close(fig)

    # --- Confusion matrix (best model at representative K, train_stats) ---
    best = ext[(ext["k"] == rep_k) & (ext["normalization"] == "train_stats")]
    best = best[np.isfinite(best["roc_auc"])].sort_values("roc_auc", ascending=False)
    if not best.empty:
        model = best.iloc[0]["model"]
        ms = preds[(preds["k"] == rep_k) & (preds["normalization"] == "train_stats")
                   & (preds["model"] == model)]
        cm = confusion_matrix(ms["y"], (ms["prob"] >= 0.5).astype(int), labels=[0, 1])
        fig, ax = plt.subplots(figsize=(4.5, 4))
        ConfusionMatrixDisplay(cm, display_labels=["Sensitive", "Resistant"]).plot(
            ax=ax, colorbar=False, cmap="Blues")
        ax.set_title(f"External confusion - GSE193258\n{model} (K={rep_k}, train_stats)")
        fig.tight_layout()
        fig.savefig(project.figures / "external_confusion.png", dpi=300)
        plt.close(fig)

    print(f"\nWrote {project.tables / 'external_validation.csv'}")
    print("Phase 6 complete.")


if __name__ == "__main__":
    main()

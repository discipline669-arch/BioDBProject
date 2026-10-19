#!/usr/bin/env python
"""Phase 5 - Train resistance-prediction models with group-aware nested CV.

For each cohort, model (LR / RF / SVM / XGBoost) and feature count K:
  * outer StratifiedGroupKFold (grouped by cell line)
  * per-fold feature selection + scaling + inner-CV tuning (see ml.cv)
  * out-of-fold predictions -> metrics

Outputs:
  results/tables/nested_cv_metrics.csv
  results/tables/nested_cv_oof_predictions.csv
  results/tables/nested_cv_selection_freq.csv
  results/figures/<ACC>_roc.png, <ACC>_pr.png, <ACC>_auc_vs_k.png, <ACC>_confusion.png

Run: python scripts/05_train_models.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (average_precision_score, confusion_matrix,  # noqa: E402
                             ConfusionMatrixDisplay, precision_recall_curve, roc_curve)

import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ml.config import load_project, set_global_seed  # noqa: E402
from ml.data import align_gene_space, encode_labels, load_cohort  # noqa: E402
from ml.cv import fit_full, nested_cv  # noqa: E402
from ml.metrics import bootstrap_ci  # noqa: E402


def main():
    project = load_project()
    set_global_seed(project.cfg["project"]["seed"])
    project.ensure_dirs()

    disc = load_cohort(project, project.cfg["cohorts"]["discovery"]["accession"])
    clin = load_cohort(project, project.cfg["cohorts"]["validation"]["accession"])
    disc, clin = align_gene_space(disc, clin)

    models = project.cfg["ml"]["models"]
    ks = project.cfg["ml"]["feature_counts"]
    seeds = project.cfg["ml"]["seeds"]

    metric_rows, pred_frames, freq_frames = [], [], []

    for cohort in (disc, clin):
        print(f"\n===== Nested CV: {cohort.accession} "
              f"({cohort.X.shape[0]} samples, {cohort.X.shape[1]} genes) =====")
        for model in models:
            for k in ks:
                res = nested_cv(cohort, model, k, project.cfg, seeds[model])
                # D9: persist the final locked model for this config
                # (same selection+scaling+inner-CV tuning on ALL samples).
                full_model = fit_full(cohort, model, k, project.cfg, seeds[model])
                mpath = project.models / f"{cohort.accession}_{model}_K{k}.joblib"
                joblib.dump({"pipeline": full_model,
                             "accession": cohort.accession, "model": model,
                             "k": k, "cfg_seed": project.cfg["project"]["seed"]},
                            mpath)
                m = dict(res["metrics"])
                m.update(accession=cohort.accession, model=model, k=k, n_splits=res["n_splits"])

                # Bootstrap 95% CIs for the headline metrics (fix X10/B1).
                # Stratified resampling of the OOF predictions only.
                y_enc = encode_labels(cohort.y).reindex(res["oof_prob"].index).to_numpy()
                p_arr = res["oof_prob"].to_numpy()
                valid = np.isfinite(p_arr)
                if valid.any() and len(set(y_enc[valid].tolist())) > 1:
                    n_boot = int(project.cfg["ml"].get("bootstrap_ci", 2000))
                    for metric in ("roc_auc", "pr_auc", "f1"):
                        _, lo, hi = bootstrap_ci(
                            y_enc[valid], p_arr[valid], metric,
                            n_boot=n_boot, seed=project.cfg["project"]["seed"])
                        m[f"{metric}_lo"], m[f"{metric}_hi"] = lo, hi
                metric_rows.append(m)

                y = encode_labels(cohort.y)
                pred_frames.append(pd.DataFrame({
                    "accession": cohort.accession, "model": model, "k": k,
                    "sample": res["oof_prob"].index,
                    "y": y.reindex(res["oof_prob"].index).to_numpy(),
                    "prob": res["oof_prob"].to_numpy(),
                }))
                sf = res["selection_freq"]
                freq_frames.append(pd.DataFrame({
                    "accession": cohort.accession, "model": model, "k": k,
                    "gene": sf.index, "selection_freq": sf.to_numpy(),
                }))
                print(f"  {model:<18} K={k:<4} n_splits={res['n_splits']} "
                      f"ROC-AUC={m['roc_auc']:.3f} PR-AUC={m['pr_auc']:.3f}")

    metrics = pd.DataFrame(metric_rows)
    oof = pd.concat(pred_frames, ignore_index=True)
    # NOTE: the selection-frequency table must keep the FULL gene space
    # (zero rows included). Phase 7 averages nested_sel_freq over all
    # (model x K) combos for a gene, so dropping zero rows would change the
    # mean denominators and silently shift the biomarker panel. The ~40 MB
    # file is generated artefact bloat, solved by .gitignore (untracked),
    # not by shrinking the table.
    freq = pd.concat(freq_frames, ignore_index=True)
    metrics.to_csv(project.tables / "nested_cv_metrics.csv", index=False)
    oof.to_csv(project.tables / "nested_cv_oof_predictions.csv", index=False)
    freq.to_csv(project.tables / "nested_cv_selection_freq.csv", index=False)

    # --- AUC vs K figure per cohort ---
    for acc, sub in metrics.groupby("accession"):
        fig, ax = plt.subplots(figsize=(7, 5))
        for model, ms in sub.groupby("model"):
            ms = ms.sort_values("k")
            ax.plot(ms["k"], ms["roc_auc"], marker="o", label=model)
        ax.set_xscale("log")
        ax.set_xlabel("Top-K features")
        ax.set_ylabel("ROC-AUC (out-of-fold)")
        ax.set_title(f"Nested CV ROC-AUC vs K - {acc}")
        ax.axhline(0.5, color="grey", ls="--", lw=1)
        ax.legend()
        fig.tight_layout()
        fig.savefig(project.figures / f"{acc}_auc_vs_k.png", dpi=300)
        plt.close(fig)

    # --- ROC / PR curves at a representative K (median of the grid) ---
    rep_k = ks[len(ks) // 2]
    for acc, sub in oof[oof["k"] == rep_k].groupby("accession"):
        fig, ax = plt.subplots(figsize=(6, 5))
        for model, ms in sub.groupby("model"):
            if ms["y"].nunique() < 2:
                continue
            fpr, tpr, _ = roc_curve(ms["y"], ms["prob"])
            ax.plot(fpr, tpr, label=f"{model} (AUC={average_precision_score(ms['y'], ms['prob']):.2f})")
        ax.plot([0, 1], [0, 1], color="grey", ls="--", lw=1)
        ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
        ax.set_title(f"Out-of-fold ROC - {acc} (K={rep_k})")
        ax.legend(loc="lower right", fontsize=8)
        fig.tight_layout()
        fig.savefig(project.figures / f"{acc}_roc.png", dpi=300)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6, 5))
        for model, ms in sub.groupby("model"):
            if ms["y"].nunique() < 2:
                continue
            pr, rc, _ = precision_recall_curve(ms["y"], ms["prob"])
            ax.plot(rc, pr, label=f"{model} (AP={average_precision_score(ms['y'], ms['prob']):.2f})")
        ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
        ax.set_title(f"Out-of-fold PR - {acc} (K={rep_k})")
        ax.legend(loc="lower left", fontsize=8)
        fig.tight_layout()
        fig.savefig(project.figures / f"{acc}_pr.png", dpi=300)
        plt.close(fig)

    # --- Confusion matrix (best model per cohort, representative K) ---
    for acc, sub in oof[oof["k"] == rep_k].groupby("accession"):
        cand = metrics[(metrics["accession"] == acc) & (metrics["k"] == rep_k)]
        cand = cand[np.isfinite(cand["roc_auc"])].sort_values("roc_auc", ascending=False)
        if cand.empty:
            continue
        model = cand.iloc[0]["model"]
        ms = sub[sub["model"] == model]
        cm = confusion_matrix(ms["y"], (ms["prob"] >= 0.5).astype(int), labels=[0, 1])
        fig, ax = plt.subplots(figsize=(4.5, 4))
        ConfusionMatrixDisplay(cm, display_labels=["Sensitive", "Resistant"]).plot(
            ax=ax, colorbar=False, cmap="Blues")
        ax.set_title(f"OOF confusion - {acc}\n{model} (K={rep_k})")
        fig.tight_layout()
        fig.savefig(project.figures / f"{acc}_confusion.png", dpi=300)
        plt.close(fig)

    print(f"\nWrote metrics -> {project.tables / 'nested_cv_metrics.csv'}")
    print("Phase 5 complete.")


if __name__ == "__main__":
    main()

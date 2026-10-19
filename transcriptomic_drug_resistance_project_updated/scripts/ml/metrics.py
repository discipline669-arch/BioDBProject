"""Classification metrics, bootstrap confidence intervals, calibration."""
from __future__ import annotations

from typing import Callable

import numpy as np
import scipy.stats
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def binary_metrics(y_true, y_prob, threshold: float = 0.5) -> dict:
    """All headline metrics at a fixed threshold plus threshold-free AUCs."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    spec = tn / (tn + fp) if (tn + fp) else float("nan")

    out = {
        "n": int(len(y_true)),
        "pos": int(y_true.sum()),
        "neg": int((1 - y_true).sum()),
        "threshold": threshold,
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "sensitivity": sens,
        "specificity": spec,
        "brier": brier_score_loss(y_true, y_prob),
    }
    # AUCs are probabilities in [0, 1] by definition. sklearn's
    # average_precision_score / roc_auc_score can overshoot by ~1e-16 through
    # float accumulation on perfectly separated folds, which then breaks
    # bootstrap bounds (lo <= point <= hi). Clamp to the valid domain.
    out["roc_auc"] = float(min(max(
        roc_auc_score(y_true, y_prob) if len(set(y_true)) > 1 else float("nan"), 0.0), 1.0))
    out["pr_auc"] = float(min(max(
        average_precision_score(y_true, y_prob) if len(set(y_true)) > 1 else float("nan"), 0.0), 1.0))
    return out


def _stratified_resample(y_true: np.ndarray, rng: np.random.Generator):
    idx = np.arange(len(y_true))
    pos = idx[y_true == 1]
    neg = idx[y_true == 0]
    take = np.concatenate([
        rng.choice(pos, size=len(pos), replace=True),
        rng.choice(neg, size=len(neg), replace=True),
    ])
    rng.shuffle(take)
    return take


def _fast_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    """Vectorised metric computation used inside the bootstrap (sklearn's
    per-call overhead dominates at tiny n and thousands of resamples)."""
    y = y_true.astype(int)
    p = y_prob.astype(float)
    pred = (p >= threshold).astype(int)

    tp = int(np.sum((pred == 1) & (y == 1)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))

    acc = (tp + tn) / len(y)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    sens = rec
    spec = tn / (tn + fp) if (tn + fp) else float("nan")
    brier = float(np.mean((p - y) ** 2))

    roc_auc = pr_auc = float("nan")
    if len(set(y.tolist())) > 1:
        ranks = scipy.stats.rankdata(p)
        n1 = int(y.sum())
        n0 = len(y) - n1
        roc_auc = (ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        order = np.argsort(-p)
        ys = y[order]
        tp_c = np.cumsum(ys)
        fp_c = np.cumsum(1 - ys)
        precision = tp_c / (tp_c + fp_c)
        recall = tp_c / tp_c[-1]
        recall_prev = np.concatenate([[0.0], recall[:-1]])
        pr_auc = float(np.sum((recall - recall_prev) * precision))
        # AUCs are probabilities in [0, 1] by definition; the rank/trapezoid
        # arithmetic above can overshoot by float rounding (~1e-16) on
        # perfectly separated folds, which then breaks bootstrap bounds
        # (lo <= point <= hi). Clamp to the valid domain.
        roc_auc = float(min(max(roc_auc, 0.0), 1.0))
        pr_auc = float(min(max(pr_auc, 0.0), 1.0))
    return {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1,
            "sensitivity": sens, "specificity": spec, "brier": brier,
            "roc_auc": float(roc_auc), "pr_auc": pr_auc}


def bootstrap_ci(y_true, y_prob, metric: str, n_boot: int = 2000, seed: int = 42,
                 alpha: float = 0.05) -> tuple[float, float, float]:
    """Return (point, lo, hi) 95% CI for a metric, stratified bootstrap."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    point = _fast_metrics(y_true, y_prob)[metric]
    if len(set(y_true.tolist())) < 2:
        return float(point), float("nan"), float("nan")

    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        idx = _stratified_resample(y_true, rng)
        v = _fast_metrics(y_true[idx], y_prob[idx])[metric]
        if np.isfinite(v):
            vals.append(v)
    vals = np.asarray(vals)
    if len(vals) == 0:
        return float(point), float("nan"), float("nan")
    lo, hi = np.quantile(vals, [alpha / 2, 1 - alpha / 2])
    return float(point), float(lo), float(hi)


def calibration_points(y_true, y_prob, n_bins: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple reliability curve (equal-width bins). Returns (mean_pred, frac_pos, counts)."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    mp, fp, cnt = [], [], []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        m = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        if m.sum() == 0:
            continue
        mp.append(y_prob[m].mean())
        fp.append(y_true[m].mean())
        cnt.append(int(m.sum()))
    return np.asarray(mp), np.asarray(fp), np.asarray(cnt)

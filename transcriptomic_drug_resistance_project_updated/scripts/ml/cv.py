"""Group-aware nested cross-validation and cross-cohort transfer."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from .data import Cohort, encode_labels
from .metrics import binary_metrics
from .models import make_pipeline, param_grid, selected_genes


def _n_splits(requested: int, groups, y) -> int:
    groups = pd.Series(groups)
    y = pd.Series(y)
    n_groups = int(groups.nunique())
    min_class = int(y.value_counts().min())
    return max(2, min(requested, n_groups, min_class))


def _fit_fold(Xtr, ytr, gtr, model_name, k, cfg, seed):
    """Nested selection+scaling+classification on one training fold, with
    inner-CV tuning. Falls back to default hyperparameters if tuning fails."""
    pipe = make_pipeline(model_name, k, seed, cfg)
    grid = param_grid(model_name, k, cfg)
    inner = _n_splits(cfg["ml"]["cv"]["inner_folds"], gtr, pd.Series(ytr))
    try:
        gs = GridSearchCV(
            pipe, grid,
            cv=StratifiedGroupKFold(n_splits=inner, shuffle=True, random_state=seed),
            scoring="roc_auc", n_jobs=1, error_score=np.nan, refit=True,
        )
        gs.fit(Xtr, ytr, groups=gtr)
        if np.isfinite(getattr(gs, "best_score_", np.nan)):
            return gs.best_estimator_
    except Exception:
        pass
    return pipe.fit(Xtr, ytr)


def nested_cv(cohort: Cohort, model_name: str, k: int, cfg: dict, seed: int) -> dict:
    """Outer StratifiedGroupKFold; per-fold selection+scaling+tuning.

    Returns out-of-fold probabilities, metrics and per-gene selection counts.
    """
    X, y, groups = cohort.X, encode_labels(cohort.y), cohort.groups
    splits = _n_splits(cfg["ml"]["cv"]["outer_folds"], groups, y)
    cv = StratifiedGroupKFold(n_splits=splits, shuffle=True, random_state=seed)

    oof = pd.Series(np.nan, index=X.index, dtype=float)
    sel_counts = pd.Series(0.0, index=X.columns)
    n_folds = 0
    for tr, te in cv.split(X, y, groups):
        gtr, ytr = groups.iloc[tr], y.iloc[tr]
        pipe = _fit_fold(X.iloc[tr], ytr.to_numpy(), gtr.to_numpy(), model_name, k, cfg, seed)
        genes = selected_genes(pipe, X.columns)
        sel_counts[genes] += 1.0
        n_folds += 1
        prob = pipe.predict_proba(X.iloc[te])[:, 1]
        oof.iloc[te] = prob

    valid = oof.notna()
    metrics = binary_metrics(y[valid].to_numpy(), oof[valid].to_numpy()) if valid.any() else {}
    sel_freq = (sel_counts / max(n_folds, 1)).sort_values(ascending=False)
    return {
        "accession": cohort.accession,
        "cohort": cohort.accession,
        "model": model_name,
        "k": k,
        "n_splits": splits,
        "oof_prob": oof,
        "y": y,
        "metrics": metrics,
        "selection_freq": sel_freq,
    }


def fit_full(cohort: Cohort, model_name: str, k: int, cfg: dict, seed: int):
    """D9: final locked model - the same selection+scaling+inner-CV tuning
    applied to ALL samples of the cohort (no outer holdout)."""
    X, y, groups = cohort.X, encode_labels(cohort.y), cohort.groups
    return _fit_fold(X, y.to_numpy(), groups.to_numpy(), model_name, k, cfg, seed)


def transfer(discovery: Cohort, validation: Cohort, model_name: str, k: int,
             cfg: dict, seed: int) -> dict:
    """Fit on the full discovery cohort, predict the validation cohort under two
    test-normalisations:
      train_stats : validation features scaled with discovery statistics (strict)
      target_z    : validation features scaled with their own statistics (transductive)
    The classifier is fit once on discovery; only test-row scaling differs.
    """
    Xtr, ytr = discovery.X, encode_labels(discovery.y)
    pipe = _fit_fold(Xtr, ytr.to_numpy(), discovery.groups.to_numpy(), model_name, k, cfg, seed)
    genes = selected_genes(pipe, Xtr.columns)
    if len(genes) < 2:
        return {"model": model_name, "k": k, "genes": genes, "preds": {}}

    clf = pipe.named_steps["clf"]
    scaler = pipe.named_steps["scale"]
    Xte = validation.X[genes]

    preds = {}
    # strict: discovery statistics
    preds["train_stats"] = clf.predict_proba(scaler.transform(Xte))[:, 1]
    # transductive: validation's own statistics
    scaler_te = StandardScaler().fit(Xte)
    preds["target_z"] = clf.predict_proba(scaler_te.transform(Xte))[:, 1]

    return {
        "model": model_name, "k": k, "genes": genes,
        "preds": preds,
        "target_index": validation.X.index,
        "y": encode_labels(validation.y),
    }

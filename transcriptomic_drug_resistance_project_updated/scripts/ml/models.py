"""Model pipelines (leakage-safe selection + scaling + classifier) and stability selection."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.feature_selection import SelectFromModel, SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

try:  # xgboost is optional at import time
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:  # pragma: no cover
    XGBClassifier = None
    HAS_XGB = False


# model_name -> display, must match cfg["ml"]["models"]
MODEL_NAMES = ["LogisticRegression", "RandomForest", "SVM", "XGBoost"]


class ProbabilitySVC(SVC):
    """SVC whose predict_proba is a monotone sigmoid of the decision function.

    Platt scaling (``probability=True``) is numerically unstable on tiny, nearly
    separable training folds and can invert the ranking. This wrapper keeps the
    ranking (AUC) exact and places the natural 0.5 threshold at decision == 0.

    Caveat (fix X11): the sigmoid is monotone, NOT calibrated. Rank metrics
    (ROC-AUC, PR-AUC, sensitivity/specificity at a training-fixed threshold) are
    valid for these scores, but Brier/calibration numbers are reference-only and
    must be labelled as such in the report.
    """

    def predict_proba(self, X):
        d = np.asarray(self.decision_function(X), dtype=float)
        p = 1.0 / (1.0 + np.exp(-d))
        return np.column_stack([1.0 - p, p])


def _elastic_net_selector(seed: int, cfg: dict):
    ml = cfg["ml"]
    lr = ml["lr"]
    base = LogisticRegression(
        penalty="elasticnet", solver="saga",
        l1_ratio=lr.get("l1_ratio", 0.5), C=lr.get("C", 1.0),
        class_weight="balanced",
        max_iter=lr.get("max_iter", 2000), tol=lr.get("tol", 1e-3),
        random_state=seed,
    )
    return SelectFromModel(base, threshold="mean")


def _safe_f_classif(X, y):
    """f_classif with divide-by-zero (constant feature) warnings suppressed.

    Constant features give ``msw == 0`` -> ``msb / msw`` is inf/nan. We zero the
    resulting F-scores so they rank last instead of flooding warnings.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        F, p = f_classif(X, y)
    F = np.nan_to_num(F, nan=0.0, posinf=0.0, neginf=0.0)
    p = np.nan_to_num(p, nan=1.0, posinf=1.0, neginf=1.0)
    return F, p


def _univariate_selector(k: int):
    return SelectKBest(_safe_f_classif, k=k)


def _classifier(model_name: str, seed: int, cfg: dict):
    ml = cfg["ml"]
    if model_name == "LogisticRegression":
        lr = ml["lr"]
        return LogisticRegression(
            penalty="elasticnet", solver="saga",
            l1_ratio=lr.get("l1_ratio", 0.5), C=lr.get("C", 1.0),
            class_weight="balanced",
            max_iter=lr.get("max_iter", 2000), tol=lr.get("tol", 1e-3),
            random_state=seed,
        )
    if model_name == "RandomForest":
        rf = ml["rf"]
        return RandomForestClassifier(
            n_estimators=rf["n_estimators"],
            min_samples_leaf=rf.get("min_samples_leaf", 2),
            max_features=rf.get("max_features", "sqrt"),
            class_weight="balanced", random_state=seed, n_jobs=1,
        )
    if model_name == "SVM":
        sv = ml["svm"]
        return ProbabilitySVC(
            kernel=sv.get("kernel", "rbf"), C=sv.get("C", 1.0),
            gamma=sv.get("gamma", "scale"), class_weight="balanced",
            random_state=seed,
        )
    if model_name == "XGBoost":
        if not HAS_XGB:
            raise ImportError("xgboost not installed")
        x = ml["xgb"]
        return XGBClassifier(
            max_depth=x["max_depth"], min_child_weight=x["min_child_weight"],
            subsample=x["subsample"], colsample_bytree=x["colsample_bytree"],
            learning_rate=x["learning_rate"], n_estimators=x["n_estimators"],
            reg_lambda=x["reg_lambda"], eval_metric="logloss",
            random_state=seed, n_jobs=1,
        )
    raise ValueError(f"unknown model: {model_name}")


def make_pipeline(model_name: str, k: int, seed: int, cfg: dict,
                  selector: str = "univariate") -> Pipeline:
    """Pipeline: [select] -> [scale] -> [classify]. Selection+scaling are
    fit only on the data passed to .fit(), i.e. inside each training fold."""
    if selector == "univariate":
        sel = _univariate_selector(k)
    elif selector == "elasticnet":
        sel = _elastic_net_selector(seed, cfg)
    else:
        raise ValueError(f"unknown selector: {selector}")
    clf = _classifier(model_name, seed, cfg)
    return Pipeline([("select", sel), ("scale", StandardScaler()), ("clf", clf)])


def param_grid(model_name: str, k: int, cfg: dict) -> dict:
    """Small inner-CV grid (kept tiny: small n and nested CV)."""
    grid = {"select__k": [k]} if model_name else {}
    ml = cfg["ml"]
    if model_name == "LogisticRegression":
        grid["clf__C"] = [0.1, 1.0, 10.0]
    elif model_name == "RandomForest":
        grid["clf__min_samples_leaf"] = [1, 2, 3]
        grid["clf__max_depth"] = [None, 3]
    elif model_name == "SVM":
        grid["clf__C"] = [0.1, 1.0, 10.0]
        grid["clf__gamma"] = ["scale", 0.01]
    elif model_name == "XGBoost":
        grid["clf__max_depth"] = [1, 2, 3]
        grid["clf__learning_rate"] = [0.03, 0.05, 0.1]
    return grid


def selected_genes(fitted_pipeline: Pipeline, gene_names) -> list[str]:
    """Gene names surviving the fitted selector step."""
    sel = fitted_pipeline.named_steps["select"]
    mask = sel.get_support()
    return list(np.asarray(gene_names)[mask])


def stability_selection(X: pd.DataFrame, y: pd.Series, seed: int, cfg: dict,
                        n_resamples: int | None = None) -> pd.Series:
    """Elastic-net selection frequency over stratified bootstrap resamples of
    the *training* data. Returns per-gene frequency in [0, 1]."""
    ml = cfg["ml"]["feature_selection"]
    n_resamples = n_resamples or ml.get("stability_resamples", 100)
    max_genes = ml.get("stability_max_genes", None)

    # Pre-filter to the top-variable genes before EN stability (screening only;
    # the decision feature set is still chosen inside each training fold).
    genes_all = np.asarray(X.columns)
    if max_genes and len(genes_all) > max_genes:
        var = X.var(axis=0).to_numpy()
        keep = np.argsort(var)[::-1][:max_genes]
        X = X.iloc[:, keep]
        genes_all = np.asarray(X.columns)

    rng = np.random.default_rng(seed)
    genes = genes_all
    y_arr = np.asarray(y).astype(int)
    pos = np.where(y_arr == 1)[0]
    neg = np.where(y_arr == 0)[0]

    counts = np.zeros(len(genes), dtype=float)
    for _ in range(n_resamples):
        take = np.concatenate([
            rng.choice(pos, size=len(pos), replace=True),
            rng.choice(neg, size=len(neg), replace=True),
        ])
        pipe = Pipeline([
            ("select", _elastic_net_selector(seed, cfg)),
        ])
        try:
            pipe.fit(X.iloc[take], y_arr[take])
            counts[pipe.named_steps["select"].get_support()] += 1
        except Exception:
            continue
    return pd.Series(counts / n_resamples, index=genes, name="stability_freq")

"""
FastAPI backend that serves the ML drug-resistance results.

Run from the project root (or anywhere):

    python backend/app.py
    # or
    uvicorn backend.app:app --reload --port 8000

Then open http://127.0.0.1:8000/

It reads the CSV/PNG artifacts produced by scripts/03_ML_biomarkers.R out of
results/ml/ and exposes them as JSON plus a small dashboard. The project root is
auto-detected (parent of this file's folder) and can be overridden with the
BIODB_PROJ environment variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("BIODB_PROJ", BACKEND_DIR.parent)).resolve()
MLOUT = PROJECT_ROOT / "results" / "ml"
STATIC_DIR = BACKEND_DIR / "static"

MODELS = ["LogisticRegression", "RandomForest", "SVM"]
K_VALUES = [20, 50, 100, 200, 500]

# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
app = FastAPI(
    title="Ovarian Cancer Drug-Resistance ML Results",
    description="Read-only API over results/ml produced by 03_ML_biomarkers.R",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _path(name: str) -> Path:
    p = MLOUT / name
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Missing artifact: {p}")
    return p


def _read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(_path(name))


def _records(df: pd.DataFrame) -> list[dict]:
    # to_json maps NaN -> null, which is valid JSON (unlike json.dumps on NaN).
    return json.loads(df.to_json(orient="records"))


def _gene_count() -> int | None:
    """Count gene columns from the wide CSV header without loading the matrix."""
    p = MLOUT / "expression_matrix.csv"
    if not p.exists():
        return None
    with p.open() as fh:
        header = fh.readline().rstrip("\n").rstrip("\r")
    if not header:
        return None
    return max(header.count(",") , 0)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "project_root": str(PROJECT_ROOT),
        "ml_dir": str(MLOUT),
        "ml_dir_exists": MLOUT.is_dir(),
    }


@app.get("/api/summary")
def summary() -> dict:
    labels = _read_csv("labels.csv")
    ext = _read_csv("external_by_direction.csv")
    loocv = _read_csv("ml_metrics_summary.csv")
    loocv = loocv[loocv["validation"] == "LOOCV"]

    best_ext = (
        ext.sort_values("ROC_AUC", ascending=False)
        .head(1)[["model", "K", "direction", "Accuracy", "ROC_AUC"]]
        .to_dict("records")
    )

    return {
        "n_samples": int(len(labels)),
        "n_genes": _gene_count(),
        "n_datasets": int(labels["dataset"].nunique()),
        "datasets": labels["dataset"].value_counts().to_dict(),
        "conditions": labels["condition"].value_counts().to_dict(),
        "models": MODELS,
        "k_values": K_VALUES,
        "directions": sorted(ext["direction"].unique().tolist()),
        "loocv_min_auc": float(loocv["ROC_AUC"].min()) if len(loocv) else None,
        "loocv_min_accuracy": float(loocv["Accuracy"].min()) if len(loocv) else None,
        "best_external": best_ext[0] if best_ext else None,
    }


@app.get("/api/external")
def external() -> list[dict]:
    df = _read_csv("external_by_direction.csv")
    return _records(df.sort_values(["model", "K", "direction"]))


@app.get("/api/metrics")
def metrics() -> list[dict]:
    df = _read_csv("ml_metrics_summary.csv")
    return _records(df)


@app.get("/api/loocv")
def loocv() -> list[dict]:
    df = _read_csv("ml_metrics_summary.csv")
    return _records(df[df["validation"] == "LOOCV"].sort_values(["model", "K"]))


@app.get("/api/predictions/external")
def predictions_external(
    model: str | None = Query(default=None),
    k: int | None = Query(default=None),
    direction: str | None = Query(default=None),
) -> list[dict]:
    df = _read_csv("predictions_external.csv")
    if model:
        df = df[df["model"] == model]
    if k is not None:
        df = df[df["K"] == k]
    if direction:
        df = df[df["direction"] == direction]
    return _records(df)


@app.get("/api/predictions/loocv")
def predictions_loocv(
    model: str | None = Query(default=None),
    k: int | None = Query(default=None),
) -> list[dict]:
    df = _read_csv("predictions_LOOCV.csv")
    if model:
        df = df[df["model"] == model]
    if k is not None:
        df = df[df["K"] == k]
    return _records(df)


@app.get("/api/biomarkers")
def biomarkers(limit: int = Query(default=30, ge=1, le=500)) -> list[dict]:
    df = _read_csv("biomarker_panel.csv")
    return _records(df.head(limit))


@app.get("/api/feature-importance")
def feature_importance(limit: int = Query(default=25, ge=1, le=500)) -> list[dict]:
    df = _read_csv("feature_importance.csv")
    top_genes = (
        df.groupby("gene")["mean_selection_freq"].mean()
        .sort_values(ascending=False)
        .head(limit)
        .index
    )
    sub = df[df["gene"].isin(top_genes)].sort_values(
        ["gene", "model"]
    )
    return {
        "genes": top_genes.tolist(),
        "rows": _records(sub),
    }


@app.get("/api/files")
def files() -> list[dict]:
    if not MLOUT.is_dir():
        return []
    out = []
    for p in sorted(MLOUT.iterdir()):
        if p.is_file():
            out.append(
                {
                    "name": p.name,
                    "size": p.stat().st_size,
                    "modified": p.stat().st_mtime,
                    "kind": "plot" if p.suffix.lower() == ".png" else "data",
                }
            )
    return out


# --------------------------------------------------------------------------
# Static assets: plots from results/ml and the dashboard itself
# --------------------------------------------------------------------------
if MLOUT.is_dir():
    app.mount("/images", StaticFiles(directory=str(MLOUT)), name="images")
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    idx = STATIC_DIR / "index.html"
    if not idx.exists():
        raise HTTPException(status_code=404, detail="dashboard not found")
    return FileResponse(idx)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

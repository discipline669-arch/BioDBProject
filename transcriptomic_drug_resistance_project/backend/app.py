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
from typing import Any

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
NORMALIZATIONS = ["target_z", "train_stats"]

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
def _read_csv(name: str) -> pd.DataFrame:
    path = MLOUT / name
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return pd.read_csv(path)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    # to_json maps NaN -> null, which is valid JSON (unlike json.dumps on NaN).
    payload = df.to_json(orient="records")
    if payload is None:
        return []
    return json.loads(payload)


def _read_records(name: str) -> list[dict[str, Any]]:
    return _records(_read_csv(name))


def _gene_count() -> int | None:
    """Count gene columns from the wide CSV header without loading the matrix."""
    path = MLOUT / "expression_matrix.csv"
    if not path.exists():
        return None
    with path.open() as fh:
        header = fh.readline().rstrip("\n").rstrip("\r")
    return header.count(",") if header else None


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "project_root": str(PROJECT_ROOT),
        "ml_dir": str(MLOUT),
        "ml_dir_exists": MLOUT.is_dir(),
    }


@app.get("/api/summary")
def summary() -> dict[str, Any]:
    labels = _read_csv("labels.csv")
    ext = _read_csv("external_by_direction.csv")
    mm = _read_csv("ml_metrics_summary.csv")
    loocv = mm[mm["validation"] == "LOOCV"]

    tz = ext.query("normalization == 'target_z'")
    ts = ext.query("normalization == 'train_stats'")
    best = tz.sort_values(by="ROC_AUC", ascending=False).head(1)
    best_strict = ts.sort_values(by="ROC_AUC", ascending=False).head(1)

    return {
        "n_samples": int(len(labels)),
        "n_genes": _gene_count(),
        "n_datasets": int(labels["dataset"].nunique()),
        "datasets": labels["dataset"].value_counts().to_dict(),
        "conditions": labels["condition"].value_counts().to_dict(),
        "models": MODELS,
        "k_values": K_VALUES,
        "normalizations": NORMALIZATIONS,
        "directions": sorted(ext["direction"].unique().tolist()),
        "loocv_min_auc": float(loocv["ROC_AUC"].min()) if len(loocv) else None,
        "loocv_min_accuracy": float(loocv["Accuracy"].min()) if len(loocv) else None,
        "best_external": _records(best)[0] if len(best) else None,
        "best_external_train_stats": _records(best_strict)[0] if len(best_strict) else None,
    }


@app.get("/api/external")
def external(
    normalization: str | None = Query(default="target_z"),
) -> list[dict[str, Any]]:
    rows = _read_records("external_by_direction.csv")
    if normalization:
        rows = [r for r in rows if r.get("normalization") == normalization]
    return rows


@app.get("/api/metrics")
def metrics() -> list[dict[str, Any]]:
    return _read_records("ml_metrics_summary.csv")


@app.get("/api/loocv")
def loocv() -> list[dict[str, Any]]:
    rows = _read_records("ml_metrics_summary.csv")
    return [r for r in rows if r.get("validation") == "LOOCV"]


@app.get("/api/predictions/external")
def predictions_external(
    model: str | None = Query(default=None),
    k: int | None = Query(default=None),
    direction: str | None = Query(default=None),
    normalization: str | None = Query(default="target_z"),
) -> list[dict[str, Any]]:
    rows = _read_records("predictions_external.csv")
    if normalization:
        rows = [r for r in rows if r.get("normalization") == normalization]
    if model:
        rows = [r for r in rows if r["model"] == model]
    if k is not None:
        rows = [r for r in rows if r["K"] == k]
    if direction:
        rows = [r for r in rows if r["direction"] == direction]
    return rows


@app.get("/api/predictions/loocv")
def predictions_loocv(
    model: str | None = Query(default=None),
    k: int | None = Query(default=None),
) -> list[dict[str, Any]]:
    rows = _read_records("predictions_LOOCV.csv")
    if model:
        rows = [r for r in rows if r["model"] == model]
    if k is not None:
        rows = [r for r in rows if r["K"] == k]
    return rows


@app.get("/api/biomarkers")
def biomarkers(limit: int = Query(default=30, ge=1, le=500)) -> list[dict[str, Any]]:
    return _read_records("biomarker_panel.csv")[:limit]


@app.get("/api/feature-importance")
def feature_importance(limit: int = Query(default=25, ge=1, le=500)) -> dict[str, Any]:
    rows_all = _read_records("feature_importance.csv")

    agg: dict[str, list[float]] = {}
    for r in rows_all:
        v = r.get("mean_selection_freq")
        if v is not None:
            agg.setdefault(r["gene"], []).append(float(v))

    ranked = sorted(
        agg.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), reverse=True
    )
    top_genes = [gene for gene, _ in ranked[:limit]]
    keep = set(top_genes)
    rows = [r for r in rows_all if r["gene"] in keep]
    return {"genes": top_genes, "rows": rows}


@app.get("/api/files")
def files() -> list[dict[str, Any]]:
    if not MLOUT.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(MLOUT.iterdir()):
        if p.is_file():
            st = p.stat()
            out.append(
                {
                    "name": p.name,
                    "size": st.st_size,
                    "modified": st.st_mtime,
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
        raise FileNotFoundError("dashboard not found")
    return FileResponse(idx)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

"""Configuration loading and path resolution for the ML track."""
from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

RELATIVE_CANDIDATES = [
    ".",
    "E:/BioDBProject/BioDBProject/transcriptomic_drug_resistance_project_updated",
    "/home/nianderbrox/BioDB_Project/transcriptomic_drug_resistance_project_updated",
]


def resolve_root() -> Path:
    """Locate the project root (env override > config.yaml > candidates)."""
    env = os.environ.get("BIODB_PROJ_UPDATED", "")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    for cand in RELATIVE_CANDIDATES:
        p = Path(cand)
        if (p / "config" / "config.yaml").is_file():
            return p.resolve()
    return Path.cwd().resolve()


@dataclass
class Project:
    root: Path
    cfg: dict

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    @property
    def data(self) -> Path:
        return self.path(self.cfg["paths"]["data"])

    @property
    def results(self) -> Path:
        return self.path(self.cfg["paths"]["results"])

    @property
    def tables(self) -> Path:
        return self.path(self.cfg["paths"]["tables"])

    @property
    def figures(self) -> Path:
        return self.path(self.cfg["paths"]["figures"])

    @property
    def models(self) -> Path:
        return self.path(self.cfg["paths"]["models"])

    @property
    def reports(self) -> Path:
        return self.path(self.cfg["paths"]["reports"])

    @property
    def synthetic(self) -> Path:
        return self.path(self.cfg["paths"]["synthetic"])

    @property
    def annotation(self) -> Path:
        return self.path(self.cfg["paths"].get("annotation", "data/annotation"))

    @property
    def synthetic_mode(self) -> bool:
        return os.environ.get("BIODB_SYNTHETIC", "") == "1"

    def cohort_dir(self, accession: str) -> Path:
        """Cohort directory, switched to the synthetic tree when BIODB_SYNTHETIC=1."""
        base = self.synthetic if self.synthetic_mode else self.data
        return base / accession

    def ensure_dirs(self) -> None:
        for p in (self.results, self.tables, self.figures, self.models,
                  self.reports, self.results / "logs"):
            p.mkdir(parents=True, exist_ok=True)


def load_project() -> Project:
    root = resolve_root()
    with open(root / "config" / "config.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return Project(root=root, cfg=cfg)


def set_global_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

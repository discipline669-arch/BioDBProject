#!/usr/bin/env python
"""Run the Python track (Stage 5 enrichment + ML Phases 4-8) in order.

Usage:
    python scripts/run_pipeline.py                 # use real data/ if present
    python scripts/run_pipeline.py --synthetic     # force the synthetic data tree
    python scripts/run_pipeline.py --synthetic --make  # (re)generate synthetic first

The R track (scripts/00-03) must have produced data/<ACC>/expression_processed.csv
and coldata.csv before running against real data. Stage 5
(03b_enrichment.py) additionally needs the DEG tables in results/tables/;
it self-skips if they or the gene-set files are absent.
"""
from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STEPS = [
    "03b_enrichment.py",
    "04_feature_selection.py",
    "05_train_models.py",
    "06_validate_clinical.py",
    "07_interpret.py",
    "08_report.py",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true",
                    help="use the synthetic data tree (data/_synthetic)")
    ap.add_argument("--make", action="store_true",
                    help="(re)generate synthetic data before running")
    args = ap.parse_args()

    if args.synthetic:
        os.environ["BIODB_SYNTHETIC"] = "1"
    if args.make:
        runpy.run_path(str(HERE / "make_synthetic_data.py"), run_name="__main__")

    for step in STEPS:
        print(f"\n{'='*70}\n>>> {step}\n{'='*70}")
        runpy.run_path(str(HERE / step), run_name="__main__")


if __name__ == "__main__":
    main()

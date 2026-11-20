"""Build the private Kaggle notebook that rebuilds the leaderboard.

Writes kaggle/notebook/ (kernel-metadata.json + the notebook) for
a push with the Kaggle helper:

  python3 scripts/build_notebook.py
  python3 <kaggle helper> kernels-push kaggle/notebook

The notebook reads the private dataset
omidgolchin/grid-load-index-data, recomputes the leaderboard
tables from the per-window scores (skill, win rate, MASE,
coverage, peak-hour error, failed windows — the same aggregation
the harness scorer uses), checks every recomputed number against
the shipped scores_summary.csv, and prints both horizon tables.
The bootstrap intervals and the beats-operator column are taken
from the shipped summary: the intervals need the harness's
paired resampling, and beats-operator pairs day errors at hourly
operator coverage, which the per-window file does not carry.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "kaggle" / "notebook"

METADATA = {
    "id": "omidgolchin/grid-load-index-leaderboard-rebuild",
    "title": "Grid Load Index Leaderboard Rebuild",
    "code_file": "rebuild_leaderboard.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": False,
    "dataset_sources": ["omidgolchin/grid-load-index-data"],
    "competition_sources": [],
    "kernel_sources": [],
    "model_sources": [],
    "machine_shape": "None",
}

INTRO = """# Grid Load Forecasting Index — leaderboard rebuild

This notebook rebuilds the index's leaderboard tables from the
attached dataset (`grid-load-index-data`) and checks them against
the shipped summary. It runs on the free CPU tier and needs no
internet.

**What the index is.** A versioned leaderboard of zero-shot
time-series foundation models on hourly EIA Form 930 demand
across 49 US balancing authorities: weekly Monday issue days
from 2025-11-03 to 2026-10-19, forecasts issued at 15:00 UTC
from the 2,048 hours published by 13:00 UTC, at day-ahead and
week-ahead horizons. Every model is scored against seasonal
naive (the demand at the same hour last week) and compared with
statistical baselines and each operator's own day-ahead
forecast.

**How the rebuild works.** `window_scores.parquet` carries one
row per method × authority × issue window with the window's
MASE, coverage, peak-hour error and failure flag (failed windows
already carry the seasonal-naive score, per the index's failure
rule). The headline skill score is 1 − the geometric mean of the
per-window MASE ratio against seasonal naive, with ratios
clipped to [0.01, 100], expressed as a percentage — the
fev-bench aggregation. This notebook recomputes the tables from
those window scores and verifies each number against
`scores_summary.csv`. The 95% bootstrap intervals and the
beats-operator column are taken from the shipped summary: the
intervals come from the harness's paired bootstrap, and
beats-operator pairs day errors over the hours the operator
forecast covers in full, which the window file does not carry.
"""

AGGREGATE_CODE = '''import glob
import os

import numpy as np
import pandas as pd

pd.set_option("display.width", 200)

# Locate the attached dataset (its mount point is the dataset slug
# on Kaggle; GLI_DATA_DIR overrides it for a local run).
candidates = [os.environ.get("GLI_DATA_DIR", "")]
candidates += [os.path.dirname(p) for p in
               glob.glob("/kaggle/input/**/window_scores.parquet", recursive=True)]
DATA = next(d for d in candidates if d and os.path.exists(os.path.join(d, "window_scores.parquet")))
print("dataset directory:", DATA)

window_scores = pd.read_parquet(os.path.join(DATA, "window_scores.parquet"))
summary = pd.read_csv(os.path.join(DATA, "scores_summary.csv"))
print("window scores:", len(window_scores), "rows;",
      window_scores["method"].nunique(), "methods;",
      window_scores["series"].nunique(), "balancing authorities")

CLIP_LO, CLIP_HI = 0.01, 100.0
REFERENCE = "seasonal_naive"

NAMES = {
    "operator": "Operator forecast", "chronos_2": "Chronos-2",
    "moirai_2": "Moirai 2.0", "tirex": "TiRex",
    "chronos_bolt": "Chronos-Bolt (base)", "timesfm_2_5": "TimesFM 2.5",
    "moirai_moe": "Moirai-MoE", "sundial": "Sundial", "toto": "Toto",
    "ttm": "Granite TTM r2", "time_moe": "Time-MoE",
    "autoarima": "AutoARIMA", "autoets": "AutoETS", "naive": "Naive",
    "seasonal_naive": "Seasonal naive",
}
RELEASED_DURING_WINDOW = set()  # MODELS.md: no v1 model was released during the window (dates re-based 2026-11-20)


def aggregate(ws):
    """The leaderboard aggregation, recomputed from window scores."""
    ref = (ws[ws["method"] == REFERENCE]
           .set_index(["series", "window"])["mase"])
    rows = []
    for (method, horizon), g in ws.groupby(["method", "horizon"]):
        ref_mase = ref.loc[list(zip(g["series"], g["window"]))].to_numpy(dtype=float)
        mase = g["mase"].to_numpy(dtype=float)
        rel = np.ones_like(mase)
        np.divide(mase, ref_mase, out=rel, where=ref_mase != 0)
        rel = np.where((ref_mase == 0) & (mase != 0), CLIP_HI, rel)
        log_rel = np.log(np.clip(rel, CLIP_LO, CLIP_HI))
        rows.append({
            "method": method, "horizon": horizon,
            "windows": len(g), "failed_windows": int(g["failed"].sum()),
            "skill_pct": (1.0 - np.exp(log_rel.mean())) * 100.0,
            "beats_snaive": float(np.mean(mase < ref_mase)),
            "mean_mase": float(mase.mean()),
            "mean_coverage80": (float(g["coverage80"].mean())
                                if g["coverage80"].notna().any() else None),
            "mean_peak_error": float(g["peak_error"].mean()),
        })
    return pd.DataFrame(rows)


rebuilt = aggregate(window_scores)
rebuilt.head()
'''

VERIFY_CODE = '''# Check every recomputed number against the shipped summary.
check = rebuilt.merge(
    summary, on=["method", "horizon"], suffixes=("_rebuilt", "_shipped"))
tolerances = {"skill_pct": 0.02, "beats_snaive": 0.001,
              "mean_coverage80": 0.001, "mean_peak_error": 0.02,
              "windows": 0, "failed_windows": 0}
failures = []
for column, tol in tolerances.items():
    both = check.dropna(subset=[column + "_rebuilt", column + "_shipped"])
    diff = (both[column + "_rebuilt"] - both[column + "_shipped"]).abs()
    if (diff > tol).any():
        failures.append((column, float(diff.max())))
assert not failures, f"rebuilt numbers disagree with the shipped summary: {failures}"
print(f"verified: {len(check)} method-horizon rows match scores_summary.csv "
      "on skill, win rate, coverage, peak error, windows and failed windows")
'''

TABLE_CODE = '''# The leaderboard tables. Intervals and beats-operator are the
# harness-computed columns from the shipped summary (see intro).
def leaderboard(horizon):
    t = rebuilt[rebuilt["horizon"] == horizon].merge(
        summary[["method", "horizon", "skill_ci_lo", "skill_ci_hi", "beats_operator"]],
        on=["method", "horizon"], how="left")
    t["model"] = t["method"].map(NAMES)
    t["released_during_window"] = t["method"].isin(RELEASED_DURING_WINDOW)
    t = t.sort_values("skill_pct", ascending=False)
    return t[["model", "skill_pct", "skill_ci_lo", "skill_ci_hi", "beats_snaive",
              "mean_mase", "mean_coverage80", "beats_operator",
              "failed_windows", "windows", "released_during_window"]]


print("Day-ahead (24 h)")
display(leaderboard("day"))
print("Week-ahead (168 h)")
display(leaderboard("week"))
'''


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": source.strip().splitlines(keepends=True)}


def code(source: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": source.strip().splitlines(keepends=True)}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "kernel-metadata.json").write_text(json.dumps(METADATA, indent=2) + "\n")
    notebook = {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                    "name": "python3"},
                     "language_info": {"name": "python", "version": "3.12"}},
        "cells": [md(INTRO), code(AGGREGATE_CODE), code(VERIFY_CODE), code(TABLE_CODE)],
    }
    out = OUT_DIR / "rebuild_leaderboard.ipynb"
    out.write_text(json.dumps(notebook, indent=1) + "\n")
    print(f"wrote {OUT_DIR}")


if __name__ == "__main__":
    main()

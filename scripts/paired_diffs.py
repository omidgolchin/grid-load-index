"""Paired skill differences between methods (review item 2).

The headline table's intervals are marginal: they overlap
heavily even where a paired comparison is decisive. This
script computes paired skill differences on the same
bootstrap resamples (src/scoring.py's bootstrap_skill_diff_ci,
the machinery DECISIONS.md #23 fixed), from the effective
per-window scores in results/scores/window_scores.parquet,
and writes results/scores/paired.csv.

Families:
  vs_top        — every method against the top-scoring
                  foundation model of that horizon (the
                  headline method), both horizons;
  vs_autoarima  — every foundation model against AutoARIMA,
                  the best statistical baseline, both horizons;
  vs_operator   — every method against the operator forecast,
                  day-ahead only, restricted to the windows
                  where the operator forecast exists (its
                  non-failed windows), so the comparison is
                  made on the windows the operator covers.

A difference is "beats" only where its 95% paired interval
excludes 0; otherwise the two methods are level. The verdict
column records which case each row is.

Usage: .venv/bin/python scripts/paired_diffs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import scoring, snapshots, spec  # noqa: E402

REFERENCE = "seasonal_naive"
OPERATOR = "operator"
BASELINE_REF = "autoarima"
FOUNDATION_MODELS = [
    "chronos_2", "moirai_2", "toto", "tirex", "chronos_bolt",
    "timesfm_2_5", "moirai_moe", "sundial", "ttm",
]


def _aligned(ws: pd.DataFrame, horizon: str, method: str,
             ref_rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """log-relative-MASE for `method` on the reference rows'
    windows, plus the bootstrap index arrays."""
    sub = ws[(ws["method"] == method) & (ws["horizon"] == horizon)]
    sub = sub.set_index(["series", "window"]).loc[
        list(zip(ref_rows["series"], ref_rows["window"]))]
    return sub


def main() -> None:
    ws = pd.read_parquet(spec.ROOT / "results" / "scores" / "window_scores.parquet")
    summary = pd.read_csv(spec.ROOT / "results" / "scores" / "summary.csv")
    series_order = {s: i for i, s in enumerate(snapshots.qualifying_series()["ba"])}
    day_order = {d.isoformat(): i for i, d in enumerate(spec.issue_days())}

    def log_rel(frame: pd.DataFrame, ref_mase: np.ndarray) -> np.ndarray:
        return scoring.log_relative_mase(frame["mase"].to_numpy(dtype=float), ref_mase)

    def diff_row(family, horizon, method, reference, frame_a, frame_b,
                 ref_mase, keys) -> dict:
        la = log_rel(frame_a, ref_mase)
        lb = log_rel(frame_b, ref_mase)
        s_idx = keys["series"].map(series_order).to_numpy()
        d_idx = keys["issue_date"].map(day_order).to_numpy()
        point, lo, hi = scoring.bootstrap_skill_diff_ci(la, lb, s_idx, d_idx)
        verdict = ("method_beats_reference" if lo > 0 else
                   "reference_beats_method" if hi < 0 else "level")
        return {"family": family, "horizon": horizon, "method": method,
                "reference": reference, "diff_pct": round(point, 2),
                "ci_lo": round(lo, 2), "ci_hi": round(hi, 2),
                "windows": len(frame_a), "verdict": verdict}

    rows = []
    for horizon in spec.HORIZONS:
        present = sorted(ws[ws["horizon"] == horizon]["method"].unique())
        ref = ws[(ws["method"] == REFERENCE) & (ws["horizon"] == horizon)]
        ref = ref.sort_values(["series", "window"]).reset_index(drop=True)
        ref_mase = ref["mase"].to_numpy(dtype=float)
        frames = {m: _aligned(ws, horizon, m, ref).reset_index() for m in present}

        top = (summary[(summary["horizon"] == horizon)
                       & (summary["method"].isin(FOUNDATION_MODELS))]
               .sort_values("skill_pct", ascending=False).iloc[0]["method"])
        for method in present:
            if method in (top, REFERENCE):
                continue
            rows.append(diff_row("vs_top", horizon, method, top,
                                 frames[method], frames[top], ref_mase, ref))
        for method in FOUNDATION_MODELS:
            if method in frames:
                rows.append(diff_row("vs_autoarima", horizon, method, BASELINE_REF,
                                     frames[method], frames[BASELINE_REF], ref_mase, ref))
        print(horizon, "top:", top)

    # vs_operator: day-ahead, on the windows the operator covers
    # (its non-failed windows).
    horizon = spec.HORIZON_DAY
    op = ws[(ws["method"] == OPERATOR) & (ws["horizon"] == horizon)]
    covered = op[~op["failed"]].sort_values(["series", "window"]).reset_index(drop=True)
    ref_all = ws[(ws["method"] == REFERENCE) & (ws["horizon"] == horizon)]
    ref_cov = ref_all.set_index(["series", "window"]).loc[
        list(zip(covered["series"], covered["window"]))].reset_index()
    ref_mase_cov = ref_cov["mase"].to_numpy(dtype=float)
    for method in sorted(ws[ws["horizon"] == horizon]["method"].unique()):
        if method == OPERATOR:
            continue
        frame = _aligned(ws, horizon, method, ref_cov).reset_index()
        rows.append(diff_row("vs_operator", horizon, method, OPERATOR,
                             frame, covered, ref_mase_cov, ref_cov))
    print("vs_operator windows:", len(covered))

    out = pd.DataFrame(rows)
    out_path = spec.ROOT / "results" / "scores" / "paired.csv"
    out.to_csv(out_path, index=False)
    print(f"wrote {out_path} ({len(out)} rows)")


if __name__ == "__main__":
    main()

"""Score forecast files against the snapshot targets.

Reads the merged forecasts in results/forecasts/, scores every
window with src/scoring.py (reported, unflagged actuals only),
applies the failure rule (a failed window takes the
seasonal-naive score, flagged), and aggregates per method and
horizon: skill score with a 95% paired-bootstrap interval, the
share of windows beating seasonal naive (beats_snaive), the
fev-bench average win rate against all other methods
(avg_win_rate), mean coverage and peak-hour error, and —
day-ahead only — the share of series-days beating the operator
forecast.

Outputs: results/scores/window_scores.parquet (per-window detail)
and results/scores/summary.csv (the aggregate table).

Usage: .venv/bin/python scripts/score_forecasts.py [--methods ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import scoring, snapshots, spec  # noqa: E402

REFERENCE = "seasonal_naive"
OPERATOR = "operator"
# Horizons each method produces (mirrors scripts/run_baselines.py).
METHOD_HORIZONS = {
    "seasonal_naive": spec.HORIZONS,
    "naive": (spec.HORIZON_DAY,),
    "operator": (spec.HORIZON_DAY,),
    "autoets": spec.HORIZONS,
    "autoarima": spec.HORIZONS,
}


def load_forecasts(method: str) -> pd.DataFrame:
    path = spec.FORECAST_DIR / f"{method}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path).set_index(["series", "issue_date", "horizon", "timestamp_utc"])


def window_frame(method: str, fc: pd.DataFrame, targets: pd.DataFrame,
                 scales: dict, failures: set) -> pd.DataFrame:
    rows = []
    for _, t in targets.iterrows():
        series, issue_date, horizon = t["series"], t["issue_date"], t["horizon"]
        index = pd.DatetimeIndex(t["timestamps_utc"])
        y = np.where(np.asarray(t["scored"], dtype=bool),
                     np.asarray(t["y_reported"], dtype=float), np.nan)
        groups = np.asarray(t["local_day"])
        failed = (series, issue_date, horizon) in failures
        point = np.full(len(index), np.nan)
        quantiles = None
        if not failed and len(fc):
            try:
                sub = fc.loc[(series, issue_date, horizon)]
                aligned = sub.reindex(index)
                point = aligned["point"].to_numpy(dtype=float)
                quantiles = {q: aligned[f"q{q:.1f}"].to_numpy(dtype=float) for q in spec.QUANTILES}
                if all(np.isnan(v).all() for v in quantiles.values()):
                    quantiles = None
            except KeyError:
                failed = True
        if method != OPERATOR and (failed or not np.isfinite(point).any()):
            failed = True
            metrics = {"n_hours": 0, "mae": None, "mase": None, "sql": None,
                       "coverage80": None, "peak_error": None}
        else:
            metrics = scoring.score_window(y, point, quantiles, scales[(series, issue_date)], groups)
            if metrics["n_hours"] == 0:
                failed = True
        rows.append({"series": series, "window": f"{issue_date}|{horizon}",
                     "issue_date": issue_date, "horizon": horizon, "method": method,
                     "failed": failed, **metrics})
    return pd.DataFrame(rows)


def beats_operator(method: str, fc: pd.DataFrame, targets: pd.DataFrame) -> float | None:
    """Share of series-days where the method's day MAE is below the
    operator forecast's, over days the operator forecast covers in
    full (day-ahead horizon only)."""
    if method == OPERATOR:
        return None
    day_targets = targets[targets["horizon"] == spec.HORIZON_DAY]
    model_days: dict = {}
    operator_days: dict = {}
    for _, t in day_targets.iterrows():
        series, issue_date = t["series"], t["issue_date"]
        index = pd.DatetimeIndex(t["timestamps_utc"])
        y = np.where(np.asarray(t["scored"], dtype=bool),
                     np.asarray(t["y_reported"], dtype=float), np.nan)
        groups = np.asarray(t["local_day"])
        op_values = np.asarray(t["operator"], dtype=float)
        full_days = {g for g in np.unique(groups)
                     if np.isfinite(op_values[groups == g]).all()}
        if not full_days or not len(fc):
            continue
        try:
            sub = fc.loc[(series, issue_date, spec.HORIZON_DAY)]
            point = sub.reindex(index)["point"].to_numpy(dtype=float)
        except KeyError:
            continue
        m = scoring.day_mae(y, point, groups)
        o = scoring.day_mae(y, op_values, groups)
        for g in full_days:
            if g in m and g in o:
                model_days[(series, issue_date, g)] = m[g]
                operator_days[(series, issue_date, g)] = o[g]
    return scoring.share_beating_reference(model_days, operator_days)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=None)
    args = ap.parse_args()

    snaps = snapshots.load_snapshots()
    targets = snapshots.load_targets()
    scales = {(r["series"], r["issue_date"]): r["scale"] for _, r in snaps.iterrows()}
    failures_path = spec.FORECAST_DIR / "failures.csv"
    failure_set = set()
    if failures_path.exists():
        f = pd.read_csv(failures_path)
        failure_set = set(zip(f["series"], f["issue_date"], f["horizon"]))

    methods = args.methods or [p.stem for p in sorted(spec.FORECAST_DIR.glob("*.parquet"))]
    frames = {}
    forecasts = {}
    for method in methods:
        forecasts[method] = load_forecasts(method)
        method_targets = targets[targets["horizon"].isin(METHOD_HORIZONS.get(method, spec.HORIZONS))]
        frames[method] = window_frame(method, forecasts[method], method_targets, scales, failure_set)
        print(method, "windows:", len(frames[method]), "failed:", int(frames[method]["failed"].sum()))

    ref = frames[REFERENCE]
    # Windows with no scored hours at all (whole target days or weeks
    # missing or flagged in the source) carry no information for any
    # method: exclude them from every method's aggregation rather
    # than counting them as failures.
    unscored = set(zip(ref.loc[ref["n_hours"] == 0, "series"], ref.loc[ref["n_hours"] == 0, "window"]))
    if unscored:
        print(f"excluding {len(unscored)} windows with no scored hours (data gaps, all methods alike)")
        for m in frames:
            keep = [k not in unscored for k in zip(frames[m]["series"], frames[m]["window"])]
            frames[m] = frames[m][keep].reset_index(drop=True)
        ref = frames[REFERENCE]
    ref_by_window = ref.set_index(["series", "window"])
    series_order = {s: i for i, s in enumerate(snapshots.qualifying_series()["ba"])}
    day_order = {d.isoformat(): i for i, d in enumerate(spec.issue_days())}

    summary_rows = []
    effective = {}
    for method in methods:
        eff = scoring.apply_failure_rule(frames[method], ref)
        eff["method"] = method
        effective[method] = eff
    effective_frames = [effective[m] for m in methods]

    # Per-horizon MASE pivots (windows x methods) for the
    # fev-bench average win rate: every method in a horizon is
    # scored on the same windows, so the pivot is complete.
    pivots = {}
    for horizon in spec.HORIZONS:
        frames_h = [effective[m][effective[m]["horizon"] == horizon] for m in methods]
        frames_h = [f for f in frames_h if len(f)]
        if frames_h:
            pivots[horizon] = pd.concat(frames_h).pivot_table(
                index=["series", "window"], columns="method", values="mase")

    for method in methods:
        eff = effective[method]
        for horizon in spec.HORIZONS:
            sub = eff[eff["horizon"] == horizon]
            if not len(sub):
                continue
            ref_sub = ref_by_window.loc[list(zip(sub["series"], sub["window"]))]
            log_rel = scoring.log_relative_mase(sub["mase"].to_numpy(dtype=float),
                                                ref_sub["mase"].to_numpy(dtype=float))
            s_idx = sub["series"].map(series_order).to_numpy()
            d_idx = sub["issue_date"].map(day_order).to_numpy()
            skill, lo, hi = scoring.bootstrap_skill_ci(log_rel, s_idx, d_idx)
            beats = beats_operator(method, forecasts[method], targets) if horizon == spec.HORIZON_DAY else None
            pivot = pivots[horizon]
            aligned = pivot.loc[list(zip(sub["series"], sub["window"]))]
            avg_wr = scoring.average_win_rate(
                aligned[method].to_numpy(dtype=float),
                aligned.drop(columns=[method]).to_numpy(dtype=float))
            row = {
                "method": method, "horizon": horizon,
                "windows": len(sub), "failed_windows": int(sub["failed"].sum()),
                "skill_pct": round(skill, 2), "skill_ci_lo": round(lo, 2), "skill_ci_hi": round(hi, 2),
                "beats_snaive": round(scoring.beats_snaive(sub["mase"].to_numpy(dtype=float),
                                                           ref_sub["mase"].to_numpy(dtype=float)), 4),
                "avg_win_rate": round(avg_wr, 4),
                "mean_coverage80": (round(float(sub["coverage80"].mean()), 4)
                                    if sub["coverage80"].notna().any() else None),
                "mean_peak_error": round(float(sub["peak_error"].mean()), 2),
                "beats_operator": (round(beats, 4) if beats is not None else None),
            }
            summary_rows.append(row)
            print(row)

    out_dir = spec.ROOT / "results" / "scores"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(effective_frames, ignore_index=True).to_parquet(out_dir / "window_scores.parquet", index=False)
    pd.DataFrame(summary_rows).to_csv(out_dir / "summary.csv", index=False)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()

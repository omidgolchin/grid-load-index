"""Run the baseline methods over the retrospective snapshots.

Methods: seasonal_naive, naive (day-ahead only), operator
(day-ahead only, from the stored forecast values), autoets and
autoarima (statsforecast MSTL; one fit per series x issue day
forecasts the week span, and the day-ahead result is its first
local day).

Work is checkpointed per (method, series) under
results/forecasts/parts/; rerunning skips finished parts. A
window whose fit fails is recorded in a failures file and gets
no forecast rows — the scorer applies the failure rule from
PLAN.md (the seasonal-naive score) at scoring time.

Progress is recorded in RUN_STATE.md (command, PID, start time,
per-method counts, elapsed and ETA).

Usage:
  .venv/bin/python scripts/run_baselines.py [--methods ...]
      [--series ...] [--max-issues N] [--workers 4] [--force]
  .venv/bin/python scripts/run_baselines.py --merge
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import snapshots, spec  # noqa: E402
from src.adapters.base import ForecastResult  # noqa: E402
from src.adapters.naive import NaiveAdapter  # noqa: E402
from src.adapters.operator import OperatorAdapter  # noqa: E402
from src.adapters.seasonal_naive import SeasonalNaiveAdapter  # noqa: E402
from src.adapters.statsforecast_mstl import StatsForecastMSTLAdapter  # noqa: E402

FAST_METHODS = ("seasonal_naive", "naive", "operator")
STATS_METHODS = ("autoets", "autoarima")
ALL_METHODS = FAST_METHODS + STATS_METHODS
METHOD_HORIZONS = {
    "seasonal_naive": spec.HORIZONS,
    "naive": (spec.HORIZON_DAY,),
    "operator": (spec.HORIZON_DAY,),
    "autoets": spec.HORIZONS,
    "autoarima": spec.HORIZONS,
}
QUANTILE_COLUMNS = [f"q{q:.1f}" for q in spec.QUANTILES]

_CFG: dict = {}


def make_adapter(method: str, series: str):
    if method == "seasonal_naive":
        return SeasonalNaiveAdapter()
    if method == "naive":
        return NaiveAdapter()
    if method == "operator":
        df = snapshots.load_eval_series(series)
        return OperatorAdapter(df["demand_forecast_mwh"])
    if method == "autoets":
        return StatsForecastMSTLAdapter("ets")
    if method == "autoarima":
        return StatsForecastMSTLAdapter("arima")
    raise ValueError(method)


def rows_from_result(method: str, series: str, issue_date: str, horizon: str,
                     target_index: pd.DatetimeIndex, result: ForecastResult) -> list[dict]:
    rows = []
    quantiles = result.quantiles or {}
    for i, ts in enumerate(target_index):
        row = {"method": method, "series": series, "issue_date": issue_date,
               "horizon": horizon, "timestamp_utc": ts, "point": float(result.point[i])}
        for q in spec.QUANTILES:
            arr = quantiles.get(q)
            row[f"q{q:.1f}"] = float(arr[i]) if arr is not None else np.nan
        rows.append(row)
    return rows


def run_series(method: str, series: str) -> dict:
    """Produce the part file for one (method, series)."""
    t0 = time.time()
    snaps = _CFG["snaps"][_CFG["snaps"]["series"] == series].sort_values("issue_date")
    targets = _CFG["targets"][_CFG["targets"]["series"] == series]
    if _CFG["max_issues"]:
        keep = set(snaps["issue_date"].tolist()[: _CFG["max_issues"]])
        snaps = snaps[snaps["issue_date"].isin(keep)]
        targets = targets[targets["issue_date"].isin(keep)]
    adapter = make_adapter(method, series)
    tgt = {(r["issue_date"], r["horizon"]): r for _, r in targets.iterrows()}
    rows: list[dict] = []
    failures: list[dict] = []
    windows_done = 0
    for _, snap in snaps.iterrows():
        issue_date = snap["issue_date"]
        context = snapshots.context_series(snap)
        week_index = pd.DatetimeIndex(tgt[(issue_date, spec.HORIZON_WEEK)]["timestamps_utc"])
        day_index = pd.DatetimeIndex(tgt[(issue_date, spec.HORIZON_DAY)]["timestamps_utc"])
        assert (week_index[: len(day_index)] == day_index).all(), "day span is not the week's first day"
        if method in STATS_METHODS:
            try:
                result = adapter.forecast(context, week_index, spec.QUANTILES)
                day_quantiles = None
                if result.quantiles:
                    day_quantiles = {q: a[: len(day_index)] for q, a in result.quantiles.items()}
                results = {
                    spec.HORIZON_WEEK: result,
                    spec.HORIZON_DAY: ForecastResult(point=result.point[: len(day_index)],
                                                     quantiles=day_quantiles),
                }
                for horizon in METHOD_HORIZONS[method]:
                    index = day_index if horizon == spec.HORIZON_DAY else week_index
                    rows += rows_from_result(method, series, issue_date, horizon, index, results[horizon])
                    windows_done += 1
            except Exception as exc:  # one failed fit fails both horizons of the window
                for horizon in METHOD_HORIZONS[method]:
                    failures.append({"method": method, "series": series, "issue_date": issue_date,
                                     "horizon": horizon, "error": f"{type(exc).__name__}: {exc}"})
        else:
            for horizon in METHOD_HORIZONS[method]:
                index = day_index if horizon == spec.HORIZON_DAY else week_index
                try:
                    result = adapter.forecast(context, index, spec.QUANTILES)
                    if method != "operator" and not np.isfinite(result.point).all():
                        raise ValueError("non-finite point forecast")
                    rows += rows_from_result(method, series, issue_date, horizon, index, result)
                    windows_done += 1
                except Exception as exc:
                    failures.append({"method": method, "series": series, "issue_date": issue_date,
                                     "horizon": horizon, "error": f"{type(exc).__name__}: {exc}"})
    parts_dir = Path(_CFG["parts_dir"])
    parts_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=["method", "series", "issue_date", "horizon",
                                        "timestamp_utc", "point"] + QUANTILE_COLUMNS)
    frame.to_parquet(parts_dir / f"{method}__{series}.parquet", index=False)
    if failures:
        pd.DataFrame(failures).to_csv(parts_dir / f"{method}__{series}.failures.csv", index=False)
    return {"method": method, "series": series, "rows": len(frame),
            "windows": windows_done, "failures": len(failures),
            "seconds": round(time.time() - t0, 2)}


def _init_worker(max_issues: int | None, parts_dir: str) -> None:
    _CFG["snaps"] = snapshots.load_snapshots()
    _CFG["targets"] = snapshots.load_targets()
    _CFG["max_issues"] = max_issues
    _CFG["parts_dir"] = parts_dir


def write_state(path: Path, lines: list[str]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n")
    os.replace(tmp, path)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def merge(parts_dir: Path) -> None:
    spec.FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    failure_frames = []
    for f in sorted(parts_dir.glob("*.failures.csv")):
        failure_frames.append(pd.read_csv(f))
    all_failures = pd.concat(failure_frames, ignore_index=True) if failure_frames else pd.DataFrame()
    for method in ALL_METHODS:
        parts = sorted(parts_dir.glob(f"{method}__*.parquet"))
        if not parts:
            continue
        frame = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
        frame = frame.sort_values(["series", "issue_date", "horizon", "timestamp_utc"]).reset_index(drop=True)
        out = spec.FORECAST_DIR / f"{method}.parquet"
        frame.to_parquet(out, index=False)
        n_failed = int((all_failures["method"] == method).sum()) if len(all_failures) else 0
        manifest_rows.append({
            "method": method,
            "file": f"results/forecasts/{method}.parquet",
            "rows": len(frame),
            "series": int(frame["series"].nunique()),
            "windows": int(frame.groupby(["series", "issue_date", "horizon"]).ngroups),
            "failed_windows": n_failed,
            "sha256": sha256_of(out),
        })
        print(method, manifest_rows[-1])
    if len(all_failures):
        all_failures.to_csv(spec.FORECAST_DIR / "failures.csv", index=False)
    manifest = pd.DataFrame(manifest_rows)
    manifest["index_version"] = spec.INDEX_VERSION
    try:
        manifest["statsforecast_version"] = importlib.metadata.version("statsforecast")
    except importlib.metadata.PackageNotFoundError:
        manifest["statsforecast_version"] = ""
    manifest["created_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest.to_csv(spec.FORECAST_DIR / "MANIFEST.csv", index=False)
    print(f"wrote {spec.FORECAST_DIR / 'MANIFEST.csv'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--methods", nargs="+", default=list(ALL_METHODS), choices=list(ALL_METHODS))
    ap.add_argument("--series", nargs="+", default=None)
    ap.add_argument("--max-issues", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--parts-dir", default=str(spec.FORECAST_PARTS_DIR))
    ap.add_argument("--state-file", default=str(spec.ROOT / "RUN_STATE.md"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()

    parts_dir = Path(args.parts_dir)
    if args.merge:
        merge(parts_dir)
        return

    series_list = args.series or snapshots.qualifying_series()["ba"].tolist()
    tasks = []
    for method in args.methods:
        for series in series_list:
            part = parts_dir / f"{method}__{series}.parquet"
            if part.exists() and not args.force:
                continue
            tasks.append((method, series))
    state_path = Path(args.state_file)
    started = datetime.now(timezone.utc)
    header = [
        "# Baseline run state",
        "",
        f"- Command: `{' '.join(sys.argv)}`",
        f"- PID: {os.getpid()}",
        f"- Started (UTC): {started.isoformat(timespec='seconds')}",
        f"- Tasks: {len(tasks)} (method x series parts)",
        "- Status: running",
    ]
    write_state(state_path, header)
    print(f"{len(tasks)} tasks; state in {state_path}", flush=True)

    done: dict[str, int] = {m: 0 for m in args.methods}
    totals: dict[str, int] = {m: sum(1 for t in tasks if t[0] == m) for m in args.methods}
    failures_total = 0
    t_start = time.time()

    def record(result: dict) -> None:
        nonlocal failures_total
        done[result["method"]] += 1
        failures_total += result["failures"]
        elapsed = time.time() - t_start
        finished = sum(done.values())
        eta = (elapsed / finished) * (len(tasks) - finished) if finished else 0
        lines = header[:-1] + [
            "- Status: running",
            f"- Elapsed: {elapsed:.0f}s; ETA: {eta:.0f}s",
            f"- Failed windows so far: {failures_total}",
        ] + [f"- {m}: {done[m]}/{totals[m]} series parts" for m in args.methods]
        write_state(state_path, lines)
        print(result, f"elapsed {elapsed:.0f}s", flush=True)

    fast_tasks = [t for t in tasks if t[0] in FAST_METHODS]
    stats_tasks = [t for t in tasks if t[0] in STATS_METHODS]
    _init_worker(args.max_issues, str(parts_dir))
    for method, series in fast_tasks:
        record(run_series(method, series))
    if stats_tasks:
        with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker,
                                 initargs=(args.max_issues, str(parts_dir))) as pool:
            futures = {pool.submit(run_series, m, s): (m, s) for m, s in stats_tasks}
            for fut in as_completed(futures):
                record(fut.result())

    elapsed = time.time() - t_start
    lines = header[:-1] + [
        "- Status: complete",
        f"- Finished (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Elapsed: {elapsed:.0f}s",
        f"- Failed windows: {failures_total}",
    ] + [f"- {m}: {done[m]}/{totals[m]} series parts" for m in args.methods]
    write_state(state_path, lines)
    print(f"complete in {elapsed:.0f}s; failed windows: {failures_total}", flush=True)


if __name__ == "__main__":
    main()

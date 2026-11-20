"""Issue the live track's forecasts for one issue day.

The live track issues a day-ahead forecast every day and a
week-ahead forecast every Monday, at 15:00 UTC, from the data
published by 13:00 UTC (the 2-hour publication lag in PLAN.md).
Each run writes, under live/:

- forecasts/<issue_date>/<method>.parquet — one file per method,
  in the same schema as the retrospective forecasts;
- snapshots/<issue_date>.parquet — the cleaned context each
  forecast was made from (the data snapshot the brief requires
  the live track to store);
- targets/<issue_date>.parquet — the target hours and the
  operator forecast as published at issue time;
- manifest.csv — one appended row per method run.

Methods run in worker subprocesses, one per method, each with
the interpreter named in live/methods.json: the CPU-feasible
methods have incompatible environments (the statistical
baselines, Granite TTM and Sundial pin different libraries), so
each method runs in the environment its retrospective run used.
The GPU foundation models are not in the live method set: a
GitHub Actions CPU runner cannot run them (DECISIONS.md,
live-track entry).

Data sources:
- --source eia: the EIA API v2 (src/eia_api.py); needs
  EIA_API_KEY in the environment.
- --source pudl: the pinned PUDL extraction in data/eval/ —
  the dry-run path. Only data up to the snapshot cutoff is
  used, exactly as the live path uses only published data.

Usage:
  .venv/bin/python scripts/live_forecast.py [--date YYYY-MM-DD]
      [--source pudl|eia] [--out DIR] [--methods a,b,c]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import cleaning, eia_api, snapshots, spec  # noqa: E402

ROOT = spec.ROOT
LIVE_DIR = ROOT / "live"
METHODS_FILE = LIVE_DIR / "methods.json"
HISTORY_DAYS = 120  # fetched history: context (86 d) + cleaning lookback

# Horizons each live method produces (mirrors the retrospective
# METHOD_HORIZONS in scripts/score_forecasts.py): naive is a
# day-ahead method; a week of naivety is not a forecast.
METHOD_HORIZONS = {"naive": (spec.HORIZON_DAY,)}

# Worker-mode adapter registry: method -> (module, class, init arg).
ADAPTERS = {
    "seasonal_naive": ("src.adapters.seasonal_naive", "SeasonalNaiveAdapter", None),
    "naive": ("src.adapters.naive", "NaiveAdapter", None),
    "autoets": ("src.adapters.statsforecast_mstl", "StatsForecastMSTLAdapter", "ets"),
    "autoarima": ("src.adapters.statsforecast_mstl", "StatsForecastMSTLAdapter", "arima"),
    "ttm": ("src.adapters.ttm", "TTMAdapter", None),
    "sundial": ("src.adapters.sundial", "SundialAdapter", None),
}


# ----------------------------------------------------------------------
# Data loading: one cleaned frame per series, in the eval shape.
# ----------------------------------------------------------------------

def load_history_pudl(issue_day: date) -> tuple[dict[str, pd.DataFrame], dict[str, pd.Series]]:
    """The pinned extraction, cut at the snapshot cutoff.

    Only rows at or before the cutoff are returned — the dry run
    must not see demand data the live track could not have seen.
    The operator series is returned separately and uncut: the
    day-ahead forecast for the target hours is published before
    the issue time by design (in this historical extraction it is
    the stored EIA-930 forecast column).
    """
    cutoff = snapshots.cutoff_for(issue_day)
    frames, operator = {}, {}
    for _, row in snapshots.qualifying_series().iterrows():
        df = snapshots.load_eval_series(row["ba"])
        frames[row["ba"]] = df[df.index <= cutoff]
        operator[row["ba"]] = df["demand_forecast_mwh"]
    return frames, operator


def load_history_eia(issue_day: date, api_key: str) -> tuple[dict[str, pd.DataFrame], dict[str, pd.Series]]:
    """Fetch region-data from the EIA API: HISTORY_DAYS of history
    up to the cutoff for the contexts, plus the operator forecast
    over the coming target span (published before issue time)."""
    cutoff = snapshots.cutoff_for(issue_day)
    start = cutoff - timedelta(days=HISTORY_DAYS)
    target_end = cutoff + timedelta(days=9)
    fmt = "%Y-%m-%dT%H"
    series_table = snapshots.qualifying_series()
    respondents = series_table["ba"].tolist()
    payload = eia_api.fetch_region_data(
        api_key, start.strftime(fmt), target_end.strftime(fmt), respondents)
    parsed = eia_api.parse_region_data(payload)
    frames, operator = {}, {}
    for _, row in series_table.iterrows():
        ba = row["ba"]
        if ba not in parsed:
            raise RuntimeError(f"EIA response carries no rows for {ba}")
        frames[ba] = eia_api.to_eval_frame(parsed[ba], start, cutoff)
        operator[ba] = parsed[ba]["demand_forecast_mwh"]
    return frames, operator


def build_jobs(issue_day: date, frames: dict[str, pd.DataFrame],
               operator: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build (jobs, snapshot record, target record) for an issue day.

    Jobs carry, per series and horizon, the cleaned 2,048-hour
    context ending at the cutoff and the target timestamps.
    Series whose context still contains NaN after cleaning are
    marked failed in the snapshot record and get no jobs.
    """
    cutoff = snapshots.cutoff_for(issue_day)
    horizons = [spec.HORIZON_DAY]
    if issue_day.weekday() == 0:
        horizons.append(spec.HORIZON_WEEK)
    job_rows, snap_rows, target_rows = [], [], []
    for _, row in snapshots.qualifying_series().iterrows():
        ba, tz_name = row["ba"], row["timezone"]
        df = frames[ba]
        grid = df.index
        reported = df["demand_reported_mwh"].to_numpy(dtype=float)
        flagged = df["imputation_code"].notna().to_numpy()
        clean, _ = cleaning.clean_series(reported, flagged)
        end_pos = int(grid.get_loc(cutoff))
        start_pos = end_pos - spec.CONTEXT_HOURS + 1
        context = clean[start_pos:end_pos + 1]
        usable = len(context) == spec.CONTEXT_HOURS and np.isfinite(context).all()
        snap_rows.append({
            "series": ba, "issue_date": issue_day.isoformat(),
            "context_start_utc": grid[start_pos] if start_pos >= 0 else None,
            "context_end_utc": cutoff,
            "context": context.tolist(), "usable": bool(usable),
        })
        if not usable:
            continue
        for horizon in horizons:
            hours, local_dates = snapshots.target_span(tz_name, issue_day, horizon)
            job_rows.append({
                "series": ba, "issue_date": issue_day.isoformat(), "horizon": horizon,
                "context": context.tolist(),
                "context_end_utc": cutoff,
                "timestamps_utc": list(hours),
            })
            op_values = operator[ba].reindex(hours).to_numpy(dtype=float)
            target_rows.append({
                "series": ba, "issue_date": issue_day.isoformat(), "horizon": horizon,
                "timestamps_utc": list(hours), "local_day": local_dates.tolist(),
                "operator": op_values.tolist(),
            })
    return pd.DataFrame(job_rows), pd.DataFrame(snap_rows), pd.DataFrame(target_rows)


# ----------------------------------------------------------------------
# Worker mode: run one method's jobs in this interpreter.
# ----------------------------------------------------------------------

def run_worker(method: str, jobs_path: Path, out_path: Path) -> None:
    import importlib

    module_name, class_name, init_arg = ADAPTERS[method]
    adapter_class = getattr(importlib.import_module(module_name), class_name)
    adapter = adapter_class() if init_arg is None else adapter_class(init_arg)
    jobs = pd.read_parquet(jobs_path)
    rows = []
    for _, job in jobs.iterrows():
        index = pd.date_range(end=job["context_end_utc"], periods=spec.CONTEXT_HOURS, freq="1h")
        context = pd.Series(np.asarray(job["context"], dtype=float), index=index)
        target_index = pd.DatetimeIndex(job["timestamps_utc"])
        result = adapter.forecast(context, target_index, list(spec.QUANTILES))
        row = {"method": method, "series": job["series"],
               "issue_date": job["issue_date"], "horizon": job["horizon"],
               "timestamp_utc": target_index, "point": np.asarray(result.point, dtype=float)}
        if result.quantiles:
            for q in spec.QUANTILES:
                row[f"q{q:.1f}"] = np.asarray(result.quantiles[q], dtype=float)
        rows.append(pd.DataFrame(row))
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    out.to_parquet(out_path, index=False)


# ----------------------------------------------------------------------
# Coordinator.
# ----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="issue date (UTC); default: today")
    ap.add_argument("--source", choices=("eia", "pudl"), default="eia")
    ap.add_argument("--out", default=None, help="output root; default: live/")
    ap.add_argument("--methods", default=None, help="comma-separated subset")
    ap.add_argument("--worker", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--jobs", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--worker-out", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.worker:
        run_worker(args.worker, Path(args.jobs), Path(args.worker_out))
        return

    issue_day = (date.fromisoformat(args.date) if args.date
                 else datetime.now(timezone.utc).date())
    out_root = Path(args.out) if args.out else LIVE_DIR
    method_pythons: dict[str, str] = json.loads(METHODS_FILE.read_text())
    methods = (args.methods.split(",") if args.methods else list(method_pythons))

    if args.source == "eia":
        api_key = os.environ.get("EIA_API_KEY")
        if not api_key:
            raise SystemExit("EIA_API_KEY is not set; the live source needs it "
                             "(or run the dry-run path with --source pudl)")
        frames, operator = load_history_eia(issue_day, api_key)
    else:
        frames, operator = load_history_pudl(issue_day)

    jobs, snap_record, target_record = build_jobs(issue_day, frames, operator)
    issued_at = datetime.now(timezone.utc).isoformat()
    print(f"issue day {issue_day}: {len(jobs)} jobs "
          f"({snap_record['usable'].sum()}/{len(snap_record)} series usable)")

    (out_root / "snapshots").mkdir(parents=True, exist_ok=True)
    (out_root / "targets").mkdir(parents=True, exist_ok=True)
    (out_root / "forecasts" / issue_day.isoformat()).mkdir(parents=True, exist_ok=True)
    snap_record.to_parquet(out_root / "snapshots" / f"{issue_day.isoformat()}.parquet", index=False)
    target_record.to_parquet(out_root / "targets" / f"{issue_day.isoformat()}.parquet", index=False)

    # Workers get a thread-limited environment: the numerical
    # libraries otherwise spawn a thread per core and spin-wait,
    # which thrashes a small shared runner (measured on the
    # 2026-10-26 dry run: the Sundial worker accumulated several
    # times the CPU its retrospective run needed per window).
    worker_env = dict(os.environ)
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "NUMEXPR_NUM_THREADS"):
        worker_env[var] = "2"

    manifest_rows = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for method in methods:
            method_jobs = jobs[jobs["horizon"].isin(
                METHOD_HORIZONS.get(method, spec.HORIZONS))]
            jobs_path = tmp_dir / f"jobs_{method}.parquet"
            method_jobs.to_parquet(jobs_path, index=False)
            worker_out = tmp_dir / f"{method}.parquet"
            cmd = [method_pythons[method], str(Path(__file__).resolve()),
                   "--worker", method, "--jobs", str(jobs_path),
                   "--worker-out", str(worker_out)]
            proc = subprocess.run(cmd, capture_output=True, text=True, env=worker_env)
            if proc.returncode != 0:
                print(f"{method}: WORKER FAILED\n{proc.stderr[-2000:]}")
                manifest_rows.append({
                    "issue_date": issue_day.isoformat(), "method": method,
                    "issued_at_utc": issued_at, "source": args.source,
                    "rows": 0, "series": 0, "status": "worker failed"})
                continue
            forecasts = pd.read_parquet(worker_out)
            dest = out_root / "forecasts" / issue_day.isoformat() / f"{method}.parquet"
            forecasts.to_parquet(dest, index=False)
            manifest_rows.append({
                "issue_date": issue_day.isoformat(), "method": method,
                "issued_at_utc": issued_at, "source": args.source,
                "rows": len(forecasts), "series": int(forecasts["series"].nunique()),
                "status": "ok"})
            print(f"{method}: {len(forecasts)} rows -> {dest}")

    manifest_path = out_root / "manifest.csv"
    new = pd.DataFrame(manifest_rows)
    if manifest_path.exists():
        new = pd.concat([pd.read_csv(manifest_path), new], ignore_index=True)
    new.to_csv(manifest_path, index=False)
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()

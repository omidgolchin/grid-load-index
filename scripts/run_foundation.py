"""Run one foundation model over the retrospective snapshots.

One adapter call per (series, issue day) forecasts the week
span; the day-ahead result is its first local day (the same
convention as the statistical baselines, DECISIONS.md #20).

Work is checkpointed per (method, series) under
results/forecasts/parts/; rerunning skips finished parts. A
window whose forecast call fails is recorded in a failures file
and gets no forecast rows — the scorer applies the failure rule
from PLAN.md (the seasonal-naive score) at scoring time.

Per-snapshot timings and the adapter's reported effective
context length are written next to the parts
(<method>__timings.csv), and progress is recorded in a run-state
file (command, PID, start time, per-series counts, elapsed).

Usage:
  .venv-fm/bin/python scripts/run_foundation.py --method ttm
      [--series ...] [--max-issues N] [--force]
      [--state-file RUN_STATE_ttm.md]
  .venv-fm/bin/python scripts/run_foundation.py --method ttm --merge
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import snapshots, spec  # noqa: E402
from src.adapters.base import ForecastResult  # noqa: E402

# method name -> (adapter module, adapter class, library distribution)
METHODS = {
    "chronos_bolt": ("src.adapters.chronos_bolt", "ChronosBoltAdapter", "chronos-forecasting"),
    "chronos_2": ("src.adapters.chronos_2", "Chronos2Adapter", "chronos-forecasting"),
    "timesfm_2_5": ("src.adapters.timesfm_2_5", "TimesFM25Adapter", "timesfm"),
    "moirai_2": ("src.adapters.moirai_2", "Moirai2Adapter", "uni2ts"),
    "tirex": ("src.adapters.tirex", "TiRexAdapter", "tirex-ts"),
    "toto": ("src.adapters.toto", "TotoAdapter", "toto-ts"),
    "sundial": ("src.adapters.sundial", "SundialAdapter", "transformers"),
    "ttm": ("src.adapters.ttm", "TTMAdapter", "granite-tsfm"),
    "moirai_moe": ("src.adapters.moirai_moe", "MoiraiMoEAdapter", "uni2ts"),
    "time_moe": ("src.adapters.time_moe", "TimeMoEAdapter", "transformers"),
}
QUANTILE_COLUMNS = [f"q{q:.1f}" for q in spec.QUANTILES]


def make_adapter(method: str, revision: str | None = None,
                 context_length: int | None = None):
    module_name, class_name, _ = METHODS[method]
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    if method == "ttm" and (revision is not None or context_length is not None):
        kwargs = {}
        if revision is not None:
            kwargs["revision"] = revision
        if context_length is not None:
            kwargs["context_length"] = context_length
        return cls(**kwargs)
    return cls()


def library_version(method: str) -> str:
    dist = METHODS[method][2]
    try:
        return f"{dist} {importlib.metadata.version(dist)}"
    except importlib.metadata.PackageNotFoundError:
        return dist


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


def run_method(method: str, series_list: list[str], max_issues: int | None,
               parts_dir: Path, force: bool, state_path: Path,
               revision: str | None = None, context_length: int | None = None) -> dict:
    snaps_all = snapshots.load_snapshots()
    targets_all = snapshots.load_targets()
    adapter = make_adapter(method, revision=revision, context_length=context_length)
    started = datetime.now(timezone.utc)
    header = [
        f"# Foundation run state — {method}",
        "",
        f"- Command: `{' '.join(sys.argv)}`",
        f"- PID: {os.getpid()}",
        f"- Started (UTC): {started.isoformat(timespec='seconds')}",
        f"- Library: {library_version(method)}",
        "- Status: running",
    ]
    write_state(state_path, header)
    parts_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    totals = {"rows": 0, "windows": 0, "failures": 0}
    done_series = 0
    for series in series_list:
        part = parts_dir / f"{method}__{series}.parquet"
        if part.exists() and not force:
            done_series += 1
            continue
        t0 = time.time()
        snaps = snaps_all[snaps_all["series"] == series].sort_values("issue_date")
        targets = targets_all[targets_all["series"] == series]
        if max_issues:
            keep = set(snaps["issue_date"].tolist()[:max_issues])
            snaps = snaps[snaps["issue_date"].isin(keep)]
            targets = targets[targets["issue_date"].isin(keep)]
        tgt = {(r["issue_date"], r["horizon"]): r for _, r in targets.iterrows()}
        rows: list[dict] = []
        failures: list[dict] = []
        timings: list[dict] = []
        windows_done = 0
        for _, snap in snaps.iterrows():
            issue_date = snap["issue_date"]
            context = snapshots.context_series(snap)
            week_index = pd.DatetimeIndex(tgt[(issue_date, spec.HORIZON_WEEK)]["timestamps_utc"])
            day_index = pd.DatetimeIndex(tgt[(issue_date, spec.HORIZON_DAY)]["timestamps_utc"])
            assert (week_index[: len(day_index)] == day_index).all(), "day span is not the week's first day"
            t_call = time.time()
            n_fail_before = len(failures)
            try:
                result = adapter.forecast(context, week_index, spec.QUANTILES)
                if not np.isfinite(result.point).all():
                    raise ValueError("non-finite point forecast")
                day_quantiles = None
                if result.quantiles:
                    day_quantiles = {q: a[: len(day_index)] for q, a in result.quantiles.items()}
                results = {
                    spec.HORIZON_WEEK: result,
                    spec.HORIZON_DAY: ForecastResult(point=result.point[: len(day_index)],
                                                     quantiles=day_quantiles),
                }
                for horizon in spec.HORIZONS:
                    index = day_index if horizon == spec.HORIZON_DAY else week_index
                    rows += rows_from_result(method, series, issue_date, horizon, index, results[horizon])
                    windows_done += 1
            except Exception as exc:  # one failed call fails both horizons of the window
                for horizon in spec.HORIZONS:
                    failures.append({"method": method, "series": series, "issue_date": issue_date,
                                     "horizon": horizon, "error": f"{type(exc).__name__}: {exc}"})
            timings.append({"method": method, "series": series, "issue_date": issue_date,
                            "seconds": round(time.time() - t_call, 3),
                            "effective_context": getattr(adapter, "effective_context_len", None),
                            "failed": len(failures) > n_fail_before})
        frame = pd.DataFrame(rows, columns=["method", "series", "issue_date", "horizon",
                                            "timestamp_utc", "point"] + QUANTILE_COLUMNS)
        frame.to_parquet(part, index=False)
        if failures:
            pd.DataFrame(failures).to_csv(parts_dir / f"{method}__{series}.failures.csv", index=False)
        pd.DataFrame(timings).to_csv(parts_dir / f"{method}__{series}.timings.csv", index=False)
        totals["rows"] += len(frame)
        totals["windows"] += windows_done
        totals["failures"] += len(failures)
        done_series += 1
        elapsed = time.time() - t_start
        lines = header[:-1] + [
            "- Status: running",
            f"- Elapsed: {elapsed:.0f}s",
            f"- Series done: {done_series}/{len(series_list)}",
            f"- Windows done: {totals['windows']}; failed windows: {totals['failures']}",
            f"- Last series: {series} ({time.time() - t0:.0f}s)",
        ]
        write_state(state_path, lines)
        print({"series": series, "rows": len(frame), "windows": windows_done,
               "failures": len(failures), "seconds": round(time.time() - t0, 1),
               "elapsed": round(elapsed)}, flush=True)
    elapsed = time.time() - t_start
    lines = header[:-1] + [
        "- Status: complete",
        f"- Finished (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Elapsed: {elapsed:.0f}s",
        f"- Rows: {totals['rows']}; windows: {totals['windows']}; failed windows: {totals['failures']}",
    ]
    write_state(state_path, lines)
    print(f"complete in {elapsed:.0f}s; failed windows: {totals['failures']}", flush=True)
    return totals


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


def merge(method: str, parts_dir: Path) -> None:
    spec.FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    parts = sorted(parts_dir.glob(f"{method}__*.parquet"))
    if not parts:
        raise SystemExit(f"no parts for {method}")
    frame = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    frame = frame.sort_values(["series", "issue_date", "horizon", "timestamp_utc"]).reset_index(drop=True)
    out = spec.FORECAST_DIR / f"{method}.parquet"
    frame.to_parquet(out, index=False)
    failure_frames = [pd.read_csv(f) for f in sorted(parts_dir.glob(f"{method}__*.failures.csv"))]
    n_failed = int(sum(len(f) for f in failure_frames))
    if failure_frames:
        all_fail = pd.concat(failure_frames, ignore_index=True)
        fail_path = spec.FORECAST_DIR / "failures.csv"
        if fail_path.exists():
            prev = pd.read_csv(fail_path)
            prev = prev[prev["method"] != method]
            all_fail = pd.concat([prev, all_fail], ignore_index=True)
        all_fail.to_csv(fail_path, index=False)
    row = {
        "method": method,
        "file": f"results/forecasts/{method}.parquet",
        "rows": len(frame),
        "series": int(frame["series"].nunique()),
        "windows": int(frame.groupby(["series", "issue_date", "horizon"]).ngroups),
        "failed_windows": n_failed,
        "sha256": sha256_of(out),
        "index_version": spec.INDEX_VERSION,
        "statsforecast_version": "",
        "library_version": library_version(method),
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path = spec.FORECAST_DIR / "MANIFEST.csv"
    manifest = pd.read_csv(manifest_path) if manifest_path.exists() else pd.DataFrame()
    if "library_version" not in manifest.columns:
        manifest["library_version"] = ""
    manifest = manifest[manifest["method"] != method] if len(manifest) else manifest
    manifest = pd.concat([manifest, pd.DataFrame([row])], ignore_index=True)
    manifest.to_csv(manifest_path, index=False)
    print(row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=sorted(METHODS))
    ap.add_argument("--series", nargs="+", default=None)
    ap.add_argument("--max-issues", type=int, default=None)
    ap.add_argument("--parts-dir", default=str(spec.FORECAST_PARTS_DIR))
    ap.add_argument("--state-file", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--adapter-revision", default=None,
                    help="checkpoint revision to load (ttm: e.g. 1536-96-r2)")
    ap.add_argument("--adapter-context", type=int, default=None,
                    help="context length the adapter passes (ttm)")
    args = ap.parse_args()
    parts_dir = Path(args.parts_dir)
    if args.merge:
        merge(args.method, parts_dir)
        return
    state_path = Path(args.state_file) if args.state_file else spec.ROOT / f"RUN_STATE_{args.method}.md"
    series_list = args.series or snapshots.qualifying_series()["ba"].tolist()
    run_method(args.method, series_list, args.max_issues, parts_dir, args.force, state_path,
               revision=args.adapter_revision, context_length=args.adapter_context)


if __name__ == "__main__":
    main()

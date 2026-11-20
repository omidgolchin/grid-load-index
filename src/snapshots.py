"""Snapshot and target construction.

For every (series, issue day) in the retrospective window this
builds exactly what PLAN.md fixes:

- the context: the CONTEXT_HOURS cleaned hours ending at the
  snapshot cutoff (13:00 UTC on the issue date — the 15:00 UTC
  issue time minus the 2-hour publication lag);
- the targets: the whole local calendar days starting with the
  next local day after the issue instant, in the series' own
  timezone — the next 1 local day (day-ahead) and the next 7
  local days (week-ahead), with transition days taken as they
  occur (23/25-hour days, 167/169-hour weeks).

Outputs (under data/snapshots/, gitignored; hashes in the
committed manifest):

- snapshots.parquet: one row per (series, issue day) — the
  context values, its start/end, and the seasonal scale.
- targets.parquet: one row per (series, issue day, horizon) —
  the target timestamps, each hour's local date, the reported
  value, whether the hour is scored (reported and unflagged),
  and the operator forecast stored against that hour.
"""

from __future__ import annotations

from datetime import date, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import spec
from .scoring import seasonal_scale


def load_eval_series(series: str) -> pd.DataFrame:
    """The pinned per-series extraction, indexed by UTC hour."""
    df = pd.read_parquet(spec.EVAL_DIR / f"{series}.parquet")
    return df.set_index("datetime_utc")


def qualifying_series() -> pd.DataFrame:
    """Series code -> reporting timezone, from the committed screen."""
    return pd.read_csv(spec.QUALIFYING_CSV)


def cutoff_for(issue_day: date) -> pd.Timestamp:
    """The snapshot cutoff: 13:00 UTC on the issue date."""
    return pd.Timestamp(issue_day) + pd.Timedelta(hours=spec.CUTOFF_HOUR_UTC)


def issue_instant(issue_day: date) -> pd.Timestamp:
    """The issue instant: 15:00 UTC on the issue date."""
    return pd.Timestamp(issue_day) + pd.Timedelta(hours=spec.ISSUE_HOUR_UTC)


def target_span(tz_name: str, issue_day: date, horizon: str) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Target hours (naive UTC) and each hour's local date.

    The first target day is the next local day after the issue
    instant in the series' timezone. Days are taken as they
    occur, so a transition day contributes 23 or 25 hours.
    """
    tz = ZoneInfo(tz_name)
    local_issue_date = issue_instant(issue_day).tz_localize("UTC").tz_convert(tz).date()
    first_date = local_issue_date + timedelta(days=1)
    n_days = 1 if horizon == spec.HORIZON_DAY else 7
    last_date = first_date + timedelta(days=n_days - 1)
    start_utc = pd.Timestamp(first_date, tz=tz).tz_convert("UTC").tz_localize(None)
    end_utc = pd.Timestamp(last_date + timedelta(days=1), tz=tz).tz_convert("UTC").tz_localize(None)
    hours = pd.date_range(start_utc, end_utc - pd.Timedelta(hours=1), freq="1h")
    local_dates = hours.tz_localize("UTC").tz_convert(tz).strftime("%Y-%m-%d").to_numpy()
    return hours, local_dates


def build_all() -> dict:
    """Build snapshots.parquet and targets.parquet; return counts."""
    series_table = qualifying_series()
    days = spec.issue_days()
    snap_rows: list[dict] = []
    target_rows: list[dict] = []
    for _, row in series_table.iterrows():
        series, tz_name = row["ba"], row["timezone"]
        df = load_eval_series(series)
        grid_start = df.index[0]
        clean = df["demand_clean_mwh"].to_numpy(dtype=float)
        reported = df["demand_reported_mwh"].to_numpy(dtype=float)
        flagged = df["imputation_code"].notna().to_numpy()
        operator = df["demand_forecast_mwh"].to_numpy(dtype=float)

        def pos(ts: pd.Timestamp) -> int:
            return int((ts - grid_start) / pd.Timedelta(hours=1))

        for issue_day in days:
            cutoff = cutoff_for(issue_day)
            end_pos = pos(cutoff)
            assert df.index[end_pos] == cutoff, "grid is not the expected hourly UTC grid"
            start_pos = end_pos - spec.CONTEXT_HOURS + 1
            context = clean[start_pos:end_pos + 1]
            snap_rows.append({
                "series": series,
                "issue_date": issue_day.isoformat(),
                "context_start_utc": df.index[start_pos],
                "context_end_utc": cutoff,
                "context": context.tolist(),
                "scale": seasonal_scale(context),
                "n_context_nan": int(np.isnan(context).sum()),
            })
            for horizon in spec.HORIZONS:
                hours, local_dates = target_span(tz_name, issue_day, horizon)
                positions = np.array([pos(h) for h in hours])
                assert (df.index[positions] == hours).all()
                y = reported[positions]
                scored = np.isfinite(y) & (~flagged[positions])
                target_rows.append({
                    "series": series,
                    "issue_date": issue_day.isoformat(),
                    "horizon": horizon,
                    "timestamps_utc": list(hours),
                    "local_day": local_dates.tolist(),
                    "y_reported": y.tolist(),
                    "scored": scored.tolist(),
                    "operator": operator[positions].tolist(),
                })
    spec.SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snaps = pd.DataFrame(snap_rows)
    targets = pd.DataFrame(target_rows)
    snaps.to_parquet(spec.SNAPSHOTS_PARQUET, index=False)
    targets.to_parquet(spec.TARGETS_PARQUET, index=False)
    return {
        "series": int(snaps["series"].nunique()),
        "issue_days": len(days),
        "snapshot_rows": len(snaps),
        "target_rows": len(targets),
        "day_target_hours": int(sum(len(r) for r in targets.loc[targets["horizon"] == "day", "timestamps_utc"])),
        "week_target_hours": int(sum(len(r) for r in targets.loc[targets["horizon"] == "week", "timestamps_utc"])),
        "contexts_with_nan": int((snaps["n_context_nan"] > 0).sum()),
    }


def load_snapshots() -> pd.DataFrame:
    return pd.read_parquet(spec.SNAPSHOTS_PARQUET)


def load_targets() -> pd.DataFrame:
    return pd.read_parquet(spec.TARGETS_PARQUET)


def context_series(snap_row: pd.Series) -> pd.Series:
    """A snapshot row's context as a Series on its UTC hour index."""
    index = pd.date_range(end=snap_row["context_end_utc"], periods=spec.CONTEXT_HOURS, freq="1h")
    return pd.Series(np.asarray(snap_row["context"], dtype=float), index=index, name=snap_row["series"])

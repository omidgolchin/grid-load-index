"""Task specification for the retrospective track.

Every value here is fixed by PLAN.md (fixed 2026-11-19, before any
model was scored on the evaluation window). This module only records
the specification; it contains no method logic.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --- Window (PLAN: retrospective window) -----------------------------------
WINDOW_START = date(2025, 11, 3)  # first issue day (a Monday)
WINDOW_END = date(2026, 10, 19)  # last issue day (a Monday)


def issue_days() -> list[date]:
    """Weekly issue days, Mondays from WINDOW_START to WINDOW_END."""
    days = []
    d = WINDOW_START
    while d <= WINDOW_END:
        assert d.weekday() == 0, f"issue day {d} is not a Monday"
        days.append(d)
        d += timedelta(days=7)
    return days


# --- Issue time and snapshot (PLAN: issue time and snapshot) ---------------
ISSUE_HOUR_UTC = 15  # forecasts are issued daily at 15:00 UTC
PUBLICATION_LAG_HOURS = 2  # snapshot drops the last 2 hours
CUTOFF_HOUR_UTC = ISSUE_HOUR_UTC - PUBLICATION_LAG_HOURS  # last context hour: 13:00 UTC
CONTEXT_HOURS = 2048

# --- Horizons (PLAN: horizons) ----------------------------------------------
HORIZON_DAY = "day"  # the next local day
HORIZON_WEEK = "week"  # the next 7 local days
HORIZONS = (HORIZON_DAY, HORIZON_WEEK)

# --- Series / periods --------------------------------------------------------
SEASONAL_PERIOD = 168  # hours in a week; the seasonal-naive period and scale lag
DAILY_PERIOD = 24

# --- Scores (PLAN: scores) ----------------------------------------------------
QUANTILES = tuple(round(0.1 * i, 1) for i in range(1, 10))  # 0.1 .. 0.9
COVERAGE_LO, COVERAGE_HI = 0.1, 0.9  # the 80% interval
REL_MASE_CLIP_LO = 0.01
REL_MASE_CLIP_HI = 100.0
BOOTSTRAP_B = 1000
BOOTSTRAP_DAY_BLOCK = 4  # blocks of 4 consecutive issue days

# --- Paths ---------------------------------------------------------------------
EVAL_DIR = ROOT / "data" / "eval"
QUALIFYING_CSV = ROOT / "data" / "manifests" / "qualifying_series.csv"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
SNAPSHOTS_PARQUET = SNAPSHOT_DIR / "snapshots.parquet"
TARGETS_PARQUET = SNAPSHOT_DIR / "targets.parquet"
FORECAST_DIR = ROOT / "results" / "forecasts"
FORECAST_PARTS_DIR = FORECAST_DIR / "parts"
INDEX_VERSION = "v2026.11"

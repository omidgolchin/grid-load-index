"""Alignment tests (DECISIONS.md #36): the defect they guard.

The target span starts after the snapshot cutoff — the
day-ahead span is the next local day, 15–21 hours after the
context end depending on the balancing authority. An adapter
must generate forward from the context end through the last
target hour and keep only the target hours
(`base.target_steps`). The first foundation adapters generated
only the span's length from the context end, shifting every
forecast by the gap; two full runs were discarded before
scoring exposed it. These tests pin the helper's arithmetic
and the generate-and-slice contract on plain days and on both
daylight-saving transitions.
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.adapters.base import ForecastResult, target_steps

CUTOFF_HOUR = 13  # snapshot cutoff: 13:00 UTC on the issue day


def context_ending(issue_day: date, hours: int = 2048) -> pd.Series:
    end = pd.Timestamp(issue_day) + pd.Timedelta(hours=CUTOFF_HOUR)
    index = pd.date_range(end=end, periods=hours, freq="1h")
    return pd.Series(np.arange(hours, dtype=float), index=index)


def local_day_index(day: date, tz_name: str) -> pd.DatetimeIndex:
    """The naive-UTC hourly index of one local calendar day."""
    tz = ZoneInfo(tz_name)
    start_local = pd.Timestamp(day, tz=tz)
    end_local = pd.Timestamp(day + timedelta(days=1), tz=tz)
    start_utc = start_local.tz_convert("UTC").tz_localize(None)
    end_utc = end_local.tz_convert("UTC").tz_localize(None)
    n = int((end_utc - start_utc) / pd.Timedelta(hours=1))
    return pd.date_range(start=start_utc, periods=n, freq="1h")


def test_plain_day_new_york():
    # Issue Monday 2025-11-03 (the index's first issue day);
    # the target is Tuesday 2025-11-04 in New York (EST, UTC-5):
    # midnight is 05:00 UTC, 16 hours after the 13:00 UTC cutoff.
    context = context_ending(date(2025, 11, 3))
    target = local_day_index(date(2025, 11, 4), "America/New_York")
    assert len(target) == 24
    total, skip = target_steps(context, target)
    assert skip == 15
    assert total == 39
    assert total - skip == len(target)


def test_plain_day_sydney():
    # Same cutoff; Sydney (AEDT, UTC+11) is already on Tuesday
    # 2025-11-04 at the 15:00 UTC issue instant, so its next
    # local day is Wednesday 2025-11-05, starting exactly 24
    # hours after the cutoff.
    context = context_ending(date(2025, 11, 3))
    target = local_day_index(date(2025, 11, 5), "Australia/Sydney")
    assert len(target) == 24
    total, skip = target_steps(context, target)
    assert skip == 23
    assert total == 47
    assert total - skip == len(target)


def test_fall_back_day_has_25_hours():
    # Sunday 2025-11-02 is the US fall-back day: 25 local hours.
    # Issued Saturday 2025-11-01, cutoff 13:00 UTC; the New York
    # day starts at 04:00 UTC (EDT, UTC-4), 15 hours later.
    context = context_ending(date(2025, 11, 1))
    target = local_day_index(date(2025, 11, 2), "America/New_York")
    assert len(target) == 25
    total, skip = target_steps(context, target)
    assert skip == 14
    assert total == 39
    assert total - skip == len(target)


def test_spring_forward_day_has_23_hours():
    # Sunday 2025-03-09 is the US spring-forward day: 23 local
    # hours. Issued Saturday 2025-03-08, cutoff 13:00 UTC; the
    # New York day starts at 05:00 UTC (EST, UTC-5), 16 hours
    # later, and ends at 04:00 UTC the next day (EDT, UTC-4).
    context = context_ending(date(2025, 3, 8))
    target = local_day_index(date(2025, 3, 9), "America/New_York")
    assert len(target) == 23
    total, skip = target_steps(context, target)
    assert skip == 15
    assert total == 38
    assert total - skip == len(target)


class StepNumberStub:
    """A stub model in the adapters' shape: it "generates" its
    own step numbers — step k is the value k hours after the
    context end — and slices with target_steps exactly as the
    real adapters do (generate through the last target hour,
    keep [skip:total])."""

    name = "stub"

    def forecast(self, context, target_index, quantiles):
        total, skip = target_steps(context, target_index)
        steps = np.arange(1, total + 1, dtype=float)
        return ForecastResult(point=steps[skip:total], quantiles=None)


def _assert_steps_match_target_hours(context, target):
    result = StepNumberStub().forecast(context, target, ())
    assert len(result.point) == len(target)
    expected = ((target - context.index[-1]) / pd.Timedelta(hours=1)).to_numpy(dtype=float)
    np.testing.assert_array_equal(result.point, expected)


def test_stub_output_matches_target_hours_plain_days():
    context = context_ending(date(2025, 11, 3))
    _assert_steps_match_target_hours(
        context, local_day_index(date(2025, 11, 4), "America/New_York"))
    _assert_steps_match_target_hours(
        context, local_day_index(date(2025, 11, 5), "Australia/Sydney"))


def test_stub_output_matches_target_hours_on_dst_days():
    _assert_steps_match_target_hours(
        context_ending(date(2025, 11, 1)),
        local_day_index(date(2025, 11, 2), "America/New_York"))  # 25 h
    _assert_steps_match_target_hours(
        context_ending(date(2025, 3, 8)),
        local_day_index(date(2025, 3, 9), "America/New_York"))  # 23 h

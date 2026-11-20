"""No-look-ahead tests over the built snapshots (not a toy):
for every snapshot in data/snapshots/, the context ends at the
snapshot cutoff, before the issue instant; every target hour is
after the cutoff; the context values are the cleaned series at
those hours; and the scored mask marks exactly the reported,
unflagged hours.
"""

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from src import snapshots, spec

pytestmark = pytest.mark.skipif(
    not spec.SNAPSHOTS_PARQUET.exists() or not spec.TARGETS_PARQUET.exists(),
    reason="snapshots not built in this checkout (data is gitignored)",
)


@pytest.fixture(scope="module")
def snaps() -> pd.DataFrame:
    return snapshots.load_snapshots()


@pytest.fixture(scope="module")
def targets() -> pd.DataFrame:
    return snapshots.load_targets()


def test_every_context_ends_at_the_cutoff_before_the_issue_instant(snaps):
    for _, row in snaps.iterrows():
        issue_day = pd.Timestamp(row["issue_date"]).date()
        assert row["context_end_utc"] == snapshots.cutoff_for(issue_day)
        assert row["context_end_utc"] < snapshots.issue_instant(issue_day)
        assert len(row["context"]) == spec.CONTEXT_HOURS
        expected_start = pd.Timestamp(row["context_end_utc"]) - pd.Timedelta(hours=spec.CONTEXT_HOURS - 1)
        assert pd.Timestamp(row["context_start_utc"]) == expected_start


def test_window_shape(snaps, targets):
    days = spec.issue_days()
    assert len(days) == 51
    assert len(snaps) == 49 * 51
    assert len(targets) == 49 * 51 * 2
    for horizon, lo, hi in ((spec.HORIZON_DAY, 23, 25), (spec.HORIZON_WEEK, 167, 169)):
        lengths = targets.loc[targets["horizon"] == horizon, "timestamps_utc"].map(len)
        assert lengths.between(lo, hi).all()


def test_targets_start_the_next_local_day_and_follow_the_cutoff(snaps, targets):
    tz_by_series = dict(zip(*[snapshots.qualifying_series()[c] for c in ("ba", "timezone")]))
    cutoffs = {(r["series"], r["issue_date"]): r["context_end_utc"] for _, r in snaps.iterrows()}
    for _, row in targets.iterrows():
        tz = ZoneInfo(tz_by_series[row["series"]])
        hours = pd.DatetimeIndex(row["timestamps_utc"])
        cutoff = cutoffs[(row["series"], row["issue_date"])]
        assert (hours > cutoff).all(), "a target hour is not after the snapshot cutoff"
        issue_local_date = snapshots.issue_instant(pd.Timestamp(row["issue_date"]).date()) \
            .tz_localize("UTC").tz_convert(tz).date()
        first_local = hours[0].tz_localize("UTC").tz_convert(tz)
        assert str(first_local.date()) == row["local_day"][0]
        assert (first_local.date() - issue_local_date).days == 1
        assert first_local.hour == 0 and first_local.minute == 0
        # the span is contiguous hours ending at the next local midnight
        assert (np.diff(hours.values) == np.timedelta64(1, "h")).all()
        last_local = hours[-1].tz_localize("UTC").tz_convert(tz)
        assert str(last_local.date()) == row["local_day"][-1]


def test_context_values_are_the_cleaned_series(snaps):
    for series, group in snaps.groupby("series"):
        df = snapshots.load_eval_series(series)
        clean = df["demand_clean_mwh"]
        for _, row in group.iterrows():
            expected = clean.loc[row["context_start_utc"]:row["context_end_utc"]].to_numpy(dtype=float)
            assert len(expected) == spec.CONTEXT_HOURS
            assert np.allclose(np.asarray(row["context"], dtype=float), expected, equal_nan=True)


def test_scored_mask_marks_reported_unflagged_hours(targets):
    checked = 0
    for series, group in targets.groupby("series"):
        df = snapshots.load_eval_series(series)
        reported = df["demand_reported_mwh"]
        flagged = df["imputation_code"].notna()
        for _, row in group.iterrows():
            hours = pd.DatetimeIndex(row["timestamps_utc"])
            expected_scored = (reported.loc[hours].notna() & ~flagged.loc[hours]).to_numpy()
            assert (np.asarray(row["scored"], dtype=bool) == expected_scored).all()
            y = np.asarray(row["y_reported"], dtype=float)
            assert np.allclose(y, reported.loc[hours].to_numpy(dtype=float), equal_nan=True)
            checked += 1
    assert checked == 49 * 51 * 2

"""Cleaning-rule tests (PLAN.md): a flagged, missing or
non-positive hour is replaced by the cleaned value 168 hours
earlier, stepping back in whole weeks; the rule looks backwards
only.
"""

import numpy as np
import pytest

from src import spec
from src.cleaning import clean_series, is_usable

WEEK = 168


def base_series(n: int = 400) -> np.ndarray:
    t = np.arange(n)
    return 100.0 + (t % 24) + 0.5 * (t % WEEK)


def test_missing_hour_filled_from_one_week_earlier():
    reported = base_series()
    flagged = np.zeros(len(reported), dtype=bool)
    reported[200] = np.nan
    clean, n_filled = clean_series(reported, flagged)
    assert clean[200] == pytest.approx(reported[200 - WEEK])
    assert n_filled == 1


def test_flagged_and_nonpositive_hours_are_filled():
    reported = base_series()
    flagged = np.zeros(len(reported), dtype=bool)
    flagged[201] = True
    reported[202] = -5.0
    reported[203] = 0.0
    clean, n_filled = clean_series(reported, flagged)
    for t in (201, 202, 203):
        assert clean[t] == pytest.approx(base_series()[t - WEEK])
    assert n_filled == 3


def test_step_back_multiple_weeks():
    reported = base_series(600)
    flagged = np.zeros(len(reported), dtype=bool)
    reported[500] = np.nan
    reported[500 - WEEK] = np.nan  # the one-week donor is itself missing
    clean, _ = clean_series(reported, flagged)
    # the chain steps back two weeks to the usable hour at 500 - 336
    assert clean[500] == pytest.approx(base_series(600)[500 - 2 * WEEK])


def test_donor_is_the_cleaned_value_not_the_reported_one():
    reported = base_series(600)
    flagged = np.zeros(len(reported), dtype=bool)
    reported[500] = np.nan
    reported[500 - WEEK] = np.nan
    clean, _ = clean_series(reported, flagged)
    # position 332 was itself filled from 164; position 500 takes that
    # filled (cleaned) value, not the missing reported one
    assert clean[500 - WEEK] == pytest.approx(base_series(600)[164])
    assert clean[500] == pytest.approx(clean[500 - WEEK])


def test_unfillable_hours_stay_nan():
    reported = base_series()
    flagged = np.zeros(len(reported), dtype=bool)
    reported[32] = np.nan  # before the first week: no donor exists
    reported[200] = np.nan  # its only lattice donor is position 32
    clean, _ = clean_series(reported, flagged)
    assert np.isnan(clean[32])
    assert np.isnan(clean[200])


def test_cleaning_looks_backwards_only():
    reported = base_series()
    flagged = np.zeros(len(reported), dtype=bool)
    reported[250] = np.nan
    clean_before, _ = clean_series(reported.copy(), flagged)
    changed = reported.copy()
    changed[300:] = 9999.0  # alter the future
    clean_after, _ = clean_series(changed, flagged)
    assert np.allclose(clean_before[:300], clean_after[:300], equal_nan=True)


def test_usable_hours_pass_through_unchanged():
    reported = base_series()
    flagged = np.zeros(len(reported), dtype=bool)
    clean, n_filled = clean_series(reported, flagged)
    assert n_filled == 0
    assert np.array_equal(clean, reported)


def test_is_usable():
    assert is_usable(10.0, False)
    assert not is_usable(10.0, True)
    assert not is_usable(float("nan"), False)
    assert not is_usable(0.0, False)
    assert not is_usable(-1.0, False)


@pytest.mark.skipif(not (spec.EVAL_DIR / "PJM.parquet").exists(),
                    reason="pinned extraction not present in this checkout")
def test_cleaning_matches_the_pinned_extraction():
    """Re-cleaning one series' reported values reproduces the
    extraction's cleaned column exactly."""
    import pandas as pd

    df = pd.read_parquet(spec.EVAL_DIR / "PJM.parquet")
    flagged = df["imputation_code"].notna().to_numpy()
    clean, _ = clean_series(df["demand_reported_mwh"].to_numpy(dtype=float), flagged)
    expected = df["demand_clean_mwh"].to_numpy(dtype=float)
    assert np.allclose(clean, expected, equal_nan=True)

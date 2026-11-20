"""Scorer tests against hand-computed cases.

Every expected value below is worked out in the test itself from
the definition, not by calling the scorer.
"""

import numpy as np
import pandas as pd
import pytest

from src import scoring


def test_seasonal_scale_hand_computed():
    context = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    # period 2: |3-1|, |4-2|, |5-3|, |6-4| = 2, 2, 2, 2 -> mean 2
    assert scoring.seasonal_scale(context, period=2) == pytest.approx(2.0)


def test_seasonal_scale_skips_nonfinite_pairs():
    context = np.array([1.0, np.nan, 3.0, 4.0, 5.0, 6.0])
    # pairs: |3-1|=2, |4-nan| dropped, |5-3|=2, |6-4|=2 -> mean 2
    assert scoring.seasonal_scale(context, period=2) == pytest.approx(2.0)


def test_score_window_hand_computed():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 33.0])
    quantiles = {0.1: np.array([8.0, 18.0, 28.0]), 0.9: np.array([12.0, 22.0, 32.0])}
    groups = np.array(["d1", "d1", "d2"])
    out = scoring.score_window(y_true, y_pred, quantiles, scale=2.0, group_ids=groups)
    # absolute errors 2, 2, 3 -> MAE 7/3; MASE = (7/3)/2 = 7/6
    assert out["n_hours"] == 3
    assert out["mae"] == pytest.approx(7.0 / 3.0)
    assert out["mase"] == pytest.approx(7.0 / 6.0)
    # pinball at 0.1: errors y-q = 2,2,2, all >= 0 -> 0.1*2 = 0.2 each
    # pinball at 0.9: errors y-q = -2,-2,-2 -> (0.9-1)*(-2) = 0.2 each
    # SQL = mean(0.2, 0.2)/scale = 0.1
    assert out["sql"] == pytest.approx(0.1)
    # every true value lies inside [q0.1, q0.9]
    assert out["coverage80"] == pytest.approx(1.0)
    # peak: d1 peaks at 20 (pred 18) -> 2; d2 peaks at 30 (pred 33) -> 3; mean 2.5
    assert out["peak_error"] == pytest.approx(2.5)


def test_score_window_drops_nonfinite_hours():
    y_true = np.array([10.0, np.nan, 30.0])
    y_pred = np.array([12.0, 18.0, np.nan])
    out = scoring.score_window(y_true, y_pred, None, scale=2.0)
    assert out["n_hours"] == 1
    assert out["mae"] == pytest.approx(2.0)
    assert out["sql"] is None and out["coverage80"] is None and out["peak_error"] is None


def test_score_window_empty():
    out = scoring.score_window(np.array([np.nan]), np.array([1.0]), None, scale=2.0)
    assert out["n_hours"] == 0 and out["mase"] is None


def test_pinball_loss_hand_computed():
    y = np.array([10.0, 20.0])
    q = np.array([8.0, 25.0])
    # q=0.25: err 2 -> 0.5; err -5 -> (0.25-1)*(-5) = 3.75; mean 2.125
    assert scoring.pinball_loss(y, q, 0.25) == pytest.approx(2.125)


def test_skill_score_hand_computed():
    # geometric mean of 0.25 and 4.0 is 1 -> skill 0%
    assert scoring.skill_score(np.array([0.25, 4.0])) == pytest.approx(0.0)
    # constant relative error 0.5 -> skill 50%
    assert scoring.skill_score(np.array([0.5, 0.5, 0.5])) == pytest.approx(50.0)
    # clipping: 1000 clips to 100 -> skill (1-100)*100
    assert scoring.skill_score(np.array([1000.0])) == pytest.approx(-9900.0)
    # clipping below: 0.001 clips to 0.01 -> skill 99%
    assert scoring.skill_score(np.array([0.001])) == pytest.approx(99.0)


def test_beats_snaive_hand_computed():
    mase = np.array([1.0, 2.0, 3.0])
    ref = np.array([2.0, 2.0, 2.0])
    assert scoring.beats_snaive(mase, ref) == pytest.approx(1.0 / 3.0)


def test_average_win_rate_hand_computed():
    # method beats A in 2/3 windows and B in 1/3 -> (2/3 + 1/3) / 2
    mase = np.array([1.0, 2.0, 3.0])
    others = np.array([[2.0, 0.5],
                       [2.0, 2.5],
                       [2.0, 4.0]])
    assert scoring.average_win_rate(mase, others) == pytest.approx(0.5)


def test_share_beating_reference_hand_computed():
    model = {"a": 1.0, "b": 3.0}
    ref = {"a": 2.0, "b": 2.0, "c": 0.5}
    # shared groups a (win) and b (loss); c is not shared -> 0.5
    assert scoring.share_beating_reference(model, ref) == pytest.approx(0.5)
    assert scoring.share_beating_reference({}, ref) is None


def test_day_mae_hand_computed():
    y = np.array([10.0, 20.0, 30.0, 40.0])
    p = np.array([11.0, 18.0, 30.0, 44.0])
    g = np.array(["a", "a", "b", "b"])
    out = scoring.day_mae(y, p, g)
    assert out["a"] == pytest.approx(1.5)  # (1 + 2)/2
    assert out["b"] == pytest.approx(2.0)  # (0 + 4)/2


def test_log_relative_mase_zero_reference():
    out = scoring.log_relative_mase(np.array([0.0, 1.0]), np.array([0.0, 0.0]))
    assert out[0] == pytest.approx(0.0)  # both zero -> relative 1
    assert out[1] == pytest.approx(np.log(100.0))  # ref zero, model not -> clipped at 100


def test_apply_failure_rule():
    scores = pd.DataFrame([
        {"series": "s1", "window": "w1", "method": "m", "failed": False,
         "mae": 3.0, "mase": 1.5, "sql": 0.4, "coverage80": 0.8, "peak_error": 9.0},
        {"series": "s1", "window": "w2", "method": "m", "failed": True,
         "mae": None, "mase": None, "sql": None, "coverage80": None, "peak_error": None},
    ])
    ref = pd.DataFrame([
        {"series": "s1", "window": "w1", "method": "ref", "failed": False,
         "mae": 4.0, "mase": 2.0, "sql": 0.5, "coverage80": 0.7, "peak_error": 10.0},
        {"series": "s1", "window": "w2", "method": "ref", "failed": False,
         "mae": 6.0, "mase": 3.0, "sql": 0.6, "coverage80": 0.6, "peak_error": 12.0},
    ])
    out = scoring.apply_failure_rule(scores, ref)
    assert out.loc[0, "mase"] == pytest.approx(1.5) and not out.loc[0, "imputed"]
    # the failed window takes the reference's scores and is flagged
    assert out.loc[1, "mase"] == pytest.approx(3.0)
    assert out.loc[1, "mae"] == pytest.approx(6.0)
    assert bool(out.loc[1, "imputed"]) and bool(out.loc[1, "failed"])


def test_bootstrap_identical_methods_have_zero_difference():
    rng = np.random.default_rng(1)
    log_rel = np.log(rng.uniform(0.3, 2.0, size=200))
    series_idx = np.repeat(np.arange(10), 20)
    day_idx = np.tile(np.arange(20), 10)
    point, lo, hi = scoring.bootstrap_skill_diff_ci(log_rel, log_rel, series_idx, day_idx, B=200)
    assert point == pytest.approx(0.0) and lo == pytest.approx(0.0) and hi == pytest.approx(0.0)


def test_bootstrap_constant_relative_error():
    log_rel = np.full(200, np.log(0.5))
    series_idx = np.repeat(np.arange(10), 20)
    day_idx = np.tile(np.arange(20), 10)
    point, lo, hi = scoring.bootstrap_skill_ci(log_rel, series_idx, day_idx, B=200)
    assert point == pytest.approx(50.0) and lo == pytest.approx(50.0) and hi == pytest.approx(50.0)


def test_bootstrap_better_method_has_positive_difference():
    rng = np.random.default_rng(2)
    base = np.log(rng.uniform(0.5, 1.5, size=400))
    better = base - np.log(2.0)  # half the relative error in every window
    series_idx = np.repeat(np.arange(20), 20)
    day_idx = np.tile(np.arange(20), 20)
    point, lo, hi = scoring.bootstrap_skill_diff_ci(better, base, series_idx, day_idx, B=200)
    assert point > 0 and lo > 0  # the interval excludes the reference value 0

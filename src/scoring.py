"""Scoring for the evaluation harness.

This module is generic: it knows about series, windows, horizons
and groups, and nothing about the domain the series come from.
All definitions follow the task specification in `spec.py`
(per-window scaled errors, a geometric-mean skill score against a
reference method, and a paired bootstrap that resamples series
and blocks of consecutive windows).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .spec import (
    BOOTSTRAP_B,
    BOOTSTRAP_DAY_BLOCK,
    COVERAGE_HI,
    COVERAGE_LO,
    REL_MASE_CLIP_HI,
    REL_MASE_CLIP_LO,
    SEASONAL_PERIOD,
)

QUANTILE_KEYS = tuple(round(0.1 * i, 1) for i in range(1, 10))


# --- Per-window quantities ---------------------------------------------------


def seasonal_scale(context: np.ndarray, period: int = SEASONAL_PERIOD) -> float:
    """Mean absolute seasonal difference of the context.

    Pairs (t, t - period) with both values finite. This is the
    in-sample scale every scaled error in a window is divided by.
    """
    context = np.asarray(context, dtype=float)
    if len(context) <= period:
        raise ValueError("context is not longer than the seasonal period")
    diffs = np.abs(context[period:] - context[:-period])
    diffs = diffs[np.isfinite(diffs)]
    if len(diffs) == 0:
        raise ValueError("context has no finite seasonal differences")
    scale = float(np.mean(diffs))
    if scale <= 0:
        raise ValueError("seasonal scale is not positive")
    return scale


def pinball_loss(y_true: np.ndarray, y_pred_q: np.ndarray, q: float) -> float:
    """Mean pinball (quantile) loss at level q."""
    err = np.asarray(y_true, dtype=float) - np.asarray(y_pred_q, dtype=float)
    return float(np.mean(np.where(err >= 0, q * err, (q - 1.0) * err)))


def score_window(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    quantiles: dict[float, np.ndarray] | None,
    scale: float,
    group_ids: np.ndarray | None = None,
) -> dict:
    """Score one window (one series, one issue point, one horizon).

    Hours whose true or predicted value is not finite are dropped.
    Returns n_hours, mae, mase, and — when the inputs support them —
    sql (scaled quantile loss over the provided quantiles),
    coverage80 (share of hours inside [q_lo, q_hi]) and peak_error
    (mean over groups of the absolute error at the group's
    highest-true-value hour). Missing quantities are None.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    yt, yp = y_true[mask], y_pred[mask]
    out: dict = {"n_hours": int(mask.sum()), "mae": None, "mase": None,
                 "sql": None, "coverage80": None, "peak_error": None}
    if len(yt) == 0:
        return out
    mae = float(np.mean(np.abs(yt - yp)))
    out["mae"] = mae
    out["mase"] = mae / scale

    if quantiles:
        losses = []
        for q, arr in sorted(quantiles.items()):
            arr = np.asarray(arr, dtype=float)[mask]
            ok = np.isfinite(arr)
            if ok.any():
                losses.append(pinball_loss(yt[ok], arr[ok], q))
        if losses:
            out["sql"] = float(np.mean(losses)) / scale
        lo = quantiles.get(COVERAGE_LO)
        hi = quantiles.get(COVERAGE_HI)
        if lo is not None and hi is not None:
            lo = np.asarray(lo, dtype=float)[mask]
            hi = np.asarray(hi, dtype=float)[mask]
            ok = np.isfinite(lo) & np.isfinite(hi)
            if ok.any():
                out["coverage80"] = float(np.mean((yt[ok] >= lo[ok]) & (yt[ok] <= hi[ok])))

    if group_ids is not None:
        groups = np.asarray(group_ids)[mask]
        peak_errors = []
        for g in pd.unique(groups):
            sel = groups == g
            if sel.any():
                peak = int(np.argmax(yt[sel]))
                peak_errors.append(abs(yp[sel][peak] - yt[sel][peak]))
        if peak_errors:
            out["peak_error"] = float(np.mean(peak_errors))
    return out


def day_mae(y_true: np.ndarray, y_pred: np.ndarray, group_ids: np.ndarray) -> dict:
    """Mean absolute error per group (e.g. per series-day)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    groups = np.asarray(group_ids)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    result = {}
    for g in pd.unique(groups[mask]):
        sel = mask & (groups == g)
        result[g] = float(np.mean(np.abs(y_true[sel] - y_pred[sel])))
    return result


# --- Aggregation across windows ------------------------------------------------


def relative_mase(mase: float, ref_mase: float) -> float:
    """A window's error relative to the reference method's."""
    if ref_mase == 0:
        return 1.0 if mase == 0 else REL_MASE_CLIP_HI
    return mase / ref_mase


def log_relative_mase(mase: np.ndarray, ref_mase: np.ndarray) -> np.ndarray:
    """Log of the clipped relative error, per window."""
    mase = np.asarray(mase, dtype=float)
    ref_mase = np.asarray(ref_mase, dtype=float)
    rel = np.ones_like(mase)
    np.divide(mase, ref_mase, out=rel, where=ref_mase != 0)
    rel = np.where((ref_mase == 0) & (mase != 0), REL_MASE_CLIP_HI, rel)
    return np.log(np.clip(rel, REL_MASE_CLIP_LO, REL_MASE_CLIP_HI))


def skill_score(relative_mases: np.ndarray) -> float:
    """Headline skill, as a percentage: 1 - geometric mean of the
    clipped relative errors, times 100."""
    rel = np.clip(np.asarray(relative_mases, dtype=float), REL_MASE_CLIP_LO, REL_MASE_CLIP_HI)
    return float((1.0 - np.exp(np.mean(np.log(rel)))) * 100.0)


def beats_snaive(mase: np.ndarray, ref_mase: np.ndarray) -> float:
    """Share of windows where the method's error is below the
    reference's (here, seasonal naive's). Named for what it
    counts; fev-bench's "win rate" is a different quantity (the
    average win rate against all other models — see
    `average_win_rate`)."""
    return float(np.mean(np.asarray(mase, dtype=float) < np.asarray(ref_mase, dtype=float)))


def average_win_rate(mase: np.ndarray, others: np.ndarray) -> float:
    """fev-bench's win rate: for each other method, the share of
    windows where this method's error is below the other's,
    averaged over the other methods. `mase` is (n_windows,) and
    `others` is (n_windows, n_other_methods), aligned by window."""
    mase = np.asarray(mase, dtype=float)
    others = np.asarray(others, dtype=float)
    if others.ndim != 2 or others.shape[1] == 0:
        raise ValueError("others must be a non-empty (n_windows, n_methods) array")
    return float(np.mean(np.mean(mase[:, None] < others, axis=0)))


def share_beating_reference(model_day_mae: dict, ref_day_mae: dict) -> float | None:
    """Share of shared groups where the method's group error is
    below the reference's. Groups present for only one side are
    not counted."""
    shared = [g for g in model_day_mae if g in ref_day_mae]
    if not shared:
        return None
    return float(np.mean([model_day_mae[g] < ref_day_mae[g] for g in shared]))


def apply_failure_rule(scores: pd.DataFrame, ref_scores: pd.DataFrame) -> pd.DataFrame:
    """Failed windows take the reference method's scores.

    `scores` has one row per (series, window, method) with a
    `failed` flag and the metric columns; `ref_scores` is the
    reference method's rows for the same windows. Failed rows keep
    their flag and gain `imputed=True`; their metric values are
    replaced by the reference's.
    """
    metrics = [c for c in ("mae", "mase", "sql", "coverage80", "peak_error") if c in scores.columns]
    ref = ref_scores.set_index(["series", "window"])[metrics]
    out = scores.copy()
    out["imputed"] = out["failed"].astype(bool)
    failed_idx = out.index[out["failed"]]
    for idx in failed_idx:
        key = (out.at[idx, "series"], out.at[idx, "window"])
        if key in ref.index:
            for m in metrics:
                out.at[idx, m] = ref.at[key, m]
    return out


# --- Paired bootstrap ------------------------------------------------------------


def _resample_weights(series_idx: np.ndarray, day_idx: np.ndarray,
                      B: int, seed: int, block: int) -> np.ndarray:
    """(B, n_windows) weights: series resampled with replacement,
    and blocks of `block` consecutive issue days resampled with
    replacement. A window's weight is the product of its series
    count and its day count."""
    rng = np.random.default_rng(seed)
    series_idx = np.asarray(series_idx)
    day_idx = np.asarray(day_idx)
    n_series = int(series_idx.max()) + 1
    n_days = int(day_idx.max()) + 1
    block_of_day = day_idx // block
    n_blocks = int(block_of_day.max()) + 1
    series_counts = rng.multinomial(n_series, np.full(n_series, 1.0 / n_series), size=B)
    block_counts = rng.multinomial(n_blocks, np.full(n_blocks, 1.0 / n_blocks), size=B)
    membership = np.zeros((n_blocks, n_days))
    for d in range(n_days):
        membership[d // block, d] = 1.0
    day_counts = block_counts @ membership
    weights = series_counts[:, series_idx] * day_counts[:, day_idx]
    return weights.astype(float)


def _bootstrap_skill(log_rel: np.ndarray, weights: np.ndarray) -> np.ndarray:
    totals = weights.sum(axis=1)
    weighted_mean = (weights @ log_rel) / totals
    return (1.0 - np.exp(weighted_mean)) * 100.0


def bootstrap_skill_ci(log_rel: np.ndarray, series_idx: np.ndarray, day_idx: np.ndarray,
                       B: int = BOOTSTRAP_B, seed: int = 20261119,
                       block: int = BOOTSTRAP_DAY_BLOCK) -> tuple[float, float, float]:
    """(point, lo, hi): the skill score and its 95% paired-bootstrap
    interval, resampling series and blocks of issue days."""
    log_rel = np.asarray(log_rel, dtype=float)
    point = float((1.0 - np.exp(np.mean(log_rel))) * 100.0)
    weights = _resample_weights(series_idx, day_idx, B, seed, block)
    reps = _bootstrap_skill(log_rel, weights)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return point, float(lo), float(hi)


def bootstrap_skill_diff_ci(log_rel_a: np.ndarray, log_rel_b: np.ndarray,
                            series_idx: np.ndarray, day_idx: np.ndarray,
                            B: int = BOOTSTRAP_B, seed: int = 20261119,
                            block: int = BOOTSTRAP_DAY_BLOCK) -> tuple[float, float, float]:
    """(point, lo, hi) for the paired skill difference A - B, in
    percentage points, on the same resamples for both methods."""
    log_rel_a = np.asarray(log_rel_a, dtype=float)
    log_rel_b = np.asarray(log_rel_b, dtype=float)
    point = float((np.exp(np.mean(log_rel_b)) - np.exp(np.mean(log_rel_a))) * 100.0)
    weights = _resample_weights(series_idx, day_idx, B, seed, block)
    diffs = _bootstrap_skill(log_rel_a, weights) - _bootstrap_skill(log_rel_b, weights)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return point, float(lo), float(hi)

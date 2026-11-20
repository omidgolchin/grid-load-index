"""The cleaning rule fixed in PLAN.md.

Model inputs use the cleaned series: a flagged, missing or
non-positive hour is replaced by the cleaned value 168 hours
earlier, stepping back in whole weeks until a usable hour is
found. Hours with no usable hour a whole number of weeks earlier
stay NaN. The rule looks backwards only.

This is the same rule `scripts/extract_data.py` applied to build
the pinned extraction in `data/eval/`; it is kept here so the
harness and its tests exercise the rule directly.
"""

from __future__ import annotations

import numpy as np

WEEK = 168


def clean_series(reported: np.ndarray, flagged: np.ndarray) -> tuple[np.ndarray, int]:
    """Apply the weekly step-back cleaning rule.

    `reported` is the reported series (NaN where absent); `flagged`
    marks hours the source flagged. Returns (clean, n_filled).
    """
    reported = np.asarray(reported, dtype=float)
    flagged = np.asarray(flagged, dtype=bool)
    usable = (~np.isnan(reported)) & (~flagged) & (reported > 0)
    clean = np.where(usable, reported, np.nan)
    n_filled = 0
    for t in range(len(clean)):
        if np.isnan(clean[t]) and t >= WEEK and not np.isnan(clean[t - WEEK]):
            clean[t] = clean[t - WEEK]
            n_filled += 1
    return clean, n_filled


def is_usable(reported_value: float, flagged: bool) -> bool:
    """Whether a single reported hour is usable as a model input."""
    return not flagged and not np.isnan(reported_value) and reported_value > 0

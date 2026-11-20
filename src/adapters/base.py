"""Model adapters.

One interface for every method:

    forecast(context, target_index, quantiles) -> ForecastResult

- `context` is a pandas Series of cleaned values on a naive-UTC
  hourly index ending at the snapshot cutoff. It is all the
  information a method may use: nothing at or after the target
  span is passed in.
- `target_index` is the naive-UTC hourly index of the target
  span; its length is the exact number of hours to forecast
  (23/25 on transition days, 167/169 for transition weeks).
- `quantiles` is the list of quantile levels requested.

`ForecastResult.point` is the point forecast aligned to
`target_index`; `ForecastResult.quantiles` maps each provided
level to its aligned values, or is None when the method gives no
quantiles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np
import pandas as pd


@dataclass
class ForecastResult:
    point: np.ndarray
    quantiles: dict[float, np.ndarray] | None = None


def target_steps(context: pd.Series, target_index: pd.DatetimeIndex) -> tuple[int, int]:
    """(total steps to generate, steps to skip) for a target span.

    The target span starts after the snapshot cutoff (the
    day-ahead span is the next local day), so a method that
    generates forward from the context end must generate
    through the last target hour and keep only the target
    hours — the same alignment the statistical adapters use.
    Returns the number of hourly steps from the context end
    through the last target hour, and how many of those steps
    precede the target span.
    """
    steps = ((target_index - context.index[-1]) / pd.Timedelta(hours=1)).to_numpy(dtype=float)
    steps = np.rint(steps).astype(int)
    return int(steps[-1]), int(steps[0]) - 1


class Adapter(Protocol):
    name: str

    def forecast(
        self,
        context: pd.Series,
        target_index: pd.DatetimeIndex,
        quantiles: Sequence[float],
    ) -> ForecastResult:
        ...


def cycle_donor_forecast(context: pd.Series, target_index: pd.DatetimeIndex, period: int) -> np.ndarray:
    """Repeat-the-last-cycle forecast.

    Each target hour takes the context value at the most recent
    hour with the same cycle phase that is inside the context:
    step back by whole periods from the target hour until the
    donor is at or before the context end, then further back by
    whole periods while the donor value is not finite. This is
    the only reading of "the value one period earlier, repeated"
    that uses nothing published after the snapshot cutoff (the
    target span starts after the cutoff, so a literal one-period
    step back would land after the cutoff for the last hours of
    a span).
    """
    values = np.asarray(context.to_numpy(dtype=float))
    n = len(values)
    offsets = ((target_index - context.index[0]) / pd.Timedelta(hours=1)).to_numpy(dtype=float)
    offsets = np.rint(offsets).astype(int)
    out = np.full(len(target_index), np.nan)
    for i, off in enumerate(offsets):
        k = max(1, int(np.ceil((off - (n - 1)) / period)))
        donor = off - period * k
        while donor >= 0 and not np.isfinite(values[donor]):
            donor -= period
        if donor >= 0:
            out[i] = values[donor]
    return out

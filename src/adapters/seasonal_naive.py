"""Seasonal naive (168 h): the value one week earlier, repeated.

The reference for every relative score. Point forecasts only —
the method has no native intervals.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from ..spec import SEASONAL_PERIOD
from .base import ForecastResult, cycle_donor_forecast


class SeasonalNaiveAdapter:
    name = "seasonal_naive"
    period = SEASONAL_PERIOD

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        return ForecastResult(point=cycle_donor_forecast(context, target_index, self.period))

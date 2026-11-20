"""Naive (24 h): the value one day earlier, repeated.

Day-ahead horizon only. Point forecasts only.
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from ..spec import DAILY_PERIOD
from .base import ForecastResult, cycle_donor_forecast


class NaiveAdapter:
    name = "naive"
    period = DAILY_PERIOD

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        return ForecastResult(point=cycle_donor_forecast(context, target_index, self.period))

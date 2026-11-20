"""The operator's own day-ahead forecast, taken from the data.

The forecast value stored against an hour in the source table is
the operator's forecast for that hour, made before the target
day. This adapter ignores the context and returns the stored
values aligned to the target span (NaN where no forecast value
exists for an hour); it is labelled "operator forecast" wherever
results are shown. Day-ahead horizon only.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .base import ForecastResult


class OperatorAdapter:
    name = "operator"

    def __init__(self, forecast_by_time: pd.Series):
        self._forecast = forecast_by_time

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        point = self._forecast.reindex(target_index).to_numpy(dtype=float)
        return ForecastResult(point=point, quantiles=None)

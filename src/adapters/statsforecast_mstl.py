"""Statistical baselines: statsforecast AutoETS / AutoARIMA
behind MSTL seasonal decomposition (seasonal periods 24 and
168), at library defaults.

statsforecast's MSTL requires a non-seasonal trend forecaster.
The AutoETS variant therefore uses MSTL's own default trend
forecaster, AutoETS(model='ZZN'); the AutoARIMA variant uses
AutoARIMA() at its defaults (inside MSTL its season_length is 1,
as the library requires). One fit on the snapshot context
forecasts every step up to the end of the target span; the rows
for the target hours are taken by step number.

Intervals: levels [20, 40, 60, 80] give quantiles 0.1-0.9; the
point forecast is recorded as the 0.5 quantile.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .base import ForecastResult

LEVEL_TO_QUANTILES = {20: (0.4, 0.6), 40: (0.3, 0.7), 60: (0.2, 0.8), 80: (0.1, 0.9)}


class StatsForecastMSTLAdapter:
    def __init__(self, trend: str):
        if trend not in ("ets", "arima"):
            raise ValueError(f"unknown trend forecaster: {trend}")
        self.trend = trend
        self.name = {"ets": "autoets", "arima": "autoarima"}[trend]

    def _model(self):
        from statsforecast.models import MSTL, AutoARIMA

        if self.trend == "ets":
            return MSTL(season_length=[24, 168])  # default trend forecaster: AutoETS(model='ZZN')
        return MSTL(season_length=[24, 168], trend_forecaster=AutoARIMA())

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        from statsforecast import StatsForecast

        values = context.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("context contains non-finite values")
        df = pd.DataFrame({"unique_id": "s", "ds": context.index, "y": values})
        steps = int(round((target_index[-1] - context.index[-1]) / pd.Timedelta(hours=1)))
        sf = StatsForecast(models=[self._model()], freq="1h", n_jobs=1)
        out = sf.forecast(df=df, h=steps, level=sorted(LEVEL_TO_QUANTILES))
        # Rows come back in chronological step order (step 1 first).
        step_numbers = ((target_index - context.index[-1]) / pd.Timedelta(hours=1)).to_numpy(dtype=float)
        rows = out.iloc[np.rint(step_numbers).astype(int) - 1]
        point = rows["MSTL"].to_numpy(dtype=float)
        provided: dict[float, np.ndarray] = {0.5: point}
        for level, (lo_q, hi_q) in LEVEL_TO_QUANTILES.items():
            provided[lo_q] = rows[f"MSTL-lo-{level}"].to_numpy(dtype=float)
            provided[hi_q] = rows[f"MSTL-hi-{level}"].to_numpy(dtype=float)
        wanted = {q: provided[q] for q in quantiles if q in provided}
        return ForecastResult(point=point, quantiles=wanted or None)

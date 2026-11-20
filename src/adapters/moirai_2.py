"""Moirai 2.0 — Salesforce.

Checkpoint: Salesforce/moirai-2.0-R-small (CC BY-NC 4.0,
research-only release; this index is a non-commercial research
evaluation — DECISIONS.md #11), via the uni2ts library.
Moirai 2.0 was released in November 2025, after the
retrospective window starts, so it is flagged "released
during window" (DECISIONS.md #12): scored, but excluded from
the headline ranking.

Moirai 2.0 predicts quantiles directly; the point forecast
recorded is the predictive median (the 0.5 quantile). The
snapshot context is passed in full (context_length = 2,048);
the length actually passed is recorded on every call.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "Salesforce/moirai-2.0-R-small"
CONTEXT_LENGTH = 2048


class Moirai2Adapter:
    name = "moirai_2"

    def __init__(self, device: str | None = None):
        from uni2ts.model.moirai2 import Moirai2Forecast, Moirai2Module

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.module = Moirai2Module.from_pretrained(CHECKPOINT)
        self.module = self.module.to(self.device)
        self._forecast_cls = Moirai2Forecast
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        from gluonts.dataset.common import ListDataset

        values = context.to_numpy(dtype=np.float32)
        self.effective_context_len = int(len(values))
        total, skip = target_steps(context, target_index)
        model = self._forecast_cls(
            module=self.module,
            prediction_length=total,
            context_length=CONTEXT_LENGTH,
            target_dim=1,
            feat_dynamic_real_dim=0,
            past_feat_dynamic_real_dim=0,
        )
        predictor = model.create_predictor(batch_size=32)
        dataset = ListDataset(
            [{"start": pd.Period(context.index[0], freq="h"), "target": values}],
            freq="h")
        fc = next(iter(predictor.predict(dataset)))
        qmap = {float(level): np.asarray(fc.quantile(float(level)), dtype=float)[skip:]
                for level in quantiles}
        q = np.sort(np.column_stack([qmap[float(l)] for l in quantiles]), axis=1)
        qmap = {float(level): q[:, j] for j, level in enumerate(quantiles)}
        point = qmap[0.5] if 0.5 in qmap else np.asarray(fc.mean, dtype=float)[skip:]
        return ForecastResult(point=point, quantiles=qmap)

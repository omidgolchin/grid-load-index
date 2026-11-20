"""Moirai-MoE — Salesforce.

Checkpoint: Salesforce/moirai-moe-1.0-R-small (CC BY-NC 4.0,
research-only release; this index is a non-commercial research
evaluation — DECISIONS.md #11), via the uni2ts library.
The small checkpoint supports a single patch size, 16, which
the adapter passes explicitly (the forecast module does not
resolve "auto" for this checkpoint). Moirai-MoE forecasts by
sampling (the library default of 100 samples); quantiles are
the empirical quantiles of the samples
and the point forecast recorded is the predictive median (the
0.5 quantile). The snapshot context is passed in full
(context_length = 2,048); the length actually passed is
recorded on every call.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "Salesforce/moirai-moe-1.0-R-small"
CONTEXT_LENGTH = 2048
NUM_SAMPLES = 100


class MoiraiMoEAdapter:
    name = "moirai_moe"

    def __init__(self, device: str | None = None):
        from uni2ts.model.moirai_moe import MoiraiMoEForecast, MoiraiMoEModule

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.module = MoiraiMoEModule.from_pretrained(CHECKPOINT)
        self.module = self.module.to(self.device)
        self._forecast_cls = MoiraiMoEForecast
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
            patch_size=16,
            num_samples=NUM_SAMPLES,
            target_dim=1,
            feat_dynamic_real_dim=0,
            past_feat_dynamic_real_dim=0,
        )
        predictor = model.create_predictor(batch_size=32)
        dataset = ListDataset(
            [{"start": pd.Period(context.index[0], freq="h"), "target": values}],
            freq="h")
        fc = next(iter(predictor.predict(dataset)))
        samples = np.asarray(fc.samples, dtype=float)[:, skip:]
        qmap = {float(level): np.quantile(samples, level, axis=0) for level in quantiles}
        point = qmap[0.5] if 0.5 in qmap else np.median(samples, axis=0)
        return ForecastResult(point=point, quantiles=qmap)

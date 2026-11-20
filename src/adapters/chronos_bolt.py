"""Chronos-Bolt (base) — Amazon.

Checkpoint: amazon/chronos-bolt-base (Apache-2.0), via the
chronos-forecasting library. Bolt predicts quantiles directly;
the point forecast recorded is the predictive median (the 0.5
quantile), the convention used for every model that gives
quantiles. The model's context length is 2,048 (model card), so
the snapshot context is passed in full; the length actually
passed is recorded on every call.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "amazon/chronos-bolt-base"


class ChronosBoltAdapter:
    name = "chronos_bolt"

    def __init__(self, device: str | None = None):
        from chronos import BaseChronosPipeline

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.pipeline = BaseChronosPipeline.from_pretrained(
            CHECKPOINT, device_map=self.device, torch_dtype=dtype)
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(len(values))
        ctx = torch.tensor(values[None, :], dtype=torch.float32)
        total, skip = target_steps(context, target_index)
        with torch.no_grad():
            q_tensor, _mean = self.pipeline.predict_quantiles(
                ctx, prediction_length=total,
                quantile_levels=list(quantiles))
        q = np.sort(q_tensor[0].to(dtype=torch.float32).numpy(), axis=1)[skip:]
        qmap = {float(level): q[:, j] for j, level in enumerate(quantiles)}
        point = qmap[0.5] if 0.5 in qmap else np.median(q, axis=1)
        return ForecastResult(point=point, quantiles=qmap)

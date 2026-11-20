"""Toto — Datadog.

Checkpoint: Datadog/Toto-Open-Base-1.0 (Apache-2.0), via the
toto-ts library (0.2.x). In this version the checkpoint loads
through the Toto wrapper (Toto.from_pretrained(...).model is
the backbone) and TotoForecaster.forecast takes a
MaskedTimeseries and returns a Forecast whose samples give
empirical quantiles; the point forecast recorded is the
predictive median. 256 samples are drawn (the library
recommends at least 128 for reliable quantiles). The snapshot
context is passed in full; the length actually passed is
recorded on every call.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "Datadog/Toto-Open-Base-1.0"
NUM_SAMPLES = 256


class TotoAdapter:
    name = "toto"

    def __init__(self, device: str | None = None):
        from toto.inference.forecaster import TotoForecaster
        from toto.model.toto import Toto

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        wrapper = Toto.from_pretrained(CHECKPOINT)
        backbone = wrapper.model.to(self.device)
        backbone.eval()
        self.forecaster = TotoForecaster(backbone)
        # The library requires num_samples divisible by
        # samples_per_batch; 256 samples in batches of 32.
        self.samples_per_batch = 32
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        from toto.data.util.dataset import MaskedTimeseries

        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(len(values))
        length = len(values)
        dev = self.device
        inputs = MaskedTimeseries(
            series=torch.tensor(values, dtype=torch.float32, device=dev).reshape(1, 1, length),
            padding_mask=torch.ones(1, 1, length, dtype=torch.bool, device=dev),
            id_mask=torch.zeros(1, 1, length, dtype=torch.long, device=dev),
            timestamp_seconds=torch.tensor(
                (context.index.view("int64") // 1_000_000_000).astype("int64"),
                dtype=torch.long, device=dev).reshape(1, 1, length),
            time_interval_seconds=torch.tensor([[3600]], dtype=torch.long, device=dev),
        )
        total, skip = target_steps(context, target_index)
        fc = self.forecaster.forecast(
            inputs, prediction_length=total,
            num_samples=NUM_SAMPLES, samples_per_batch=self.samples_per_batch)
        qmap: dict[float, np.ndarray] = {}
        for level in quantiles:
            arr = fc.quantile(float(level)).detach().cpu().numpy()
            qmap[float(level)] = np.asarray(arr, dtype=float).reshape(-1)[skip:]
        q = np.sort(np.column_stack([qmap[float(l)] for l in quantiles]), axis=1)
        qmap = {float(level): q[:, j] for j, level in enumerate(quantiles)}
        point = qmap[0.5] if 0.5 in qmap else np.median(q, axis=1)
        return ForecastResult(point=point, quantiles=qmap)

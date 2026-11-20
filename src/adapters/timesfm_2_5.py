"""TimesFM 2.5 — Google.

Checkpoint: google/timesfm-2.5-200m-pytorch (Apache-2.0), via
the timesfm library (2.x, torch backend). The model is compiled
with max_context = 2,048 so the snapshot context is used in
full (the library takes the last max_context values of the
input; the input here is exactly 2,048 long, and the length
actually passed is recorded on every call). The quantile head
is the library's continuous quantile head with its built-in
quantile-crossing fix. The point forecast recorded is the
predictive median (the 0.5 quantile).
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "google/timesfm-2.5-200m-pytorch"
MAX_CONTEXT = 2048


class TimesFM25Adapter:
    name = "timesfm_2_5"

    def __init__(self, device: str | None = None):
        import timesfm

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(CHECKPOINT)
        self.model.compile(timesfm.ForecastConfig(
            max_context=MAX_CONTEXT,
            max_horizon=256,
            normalize_inputs=True,
            use_continuous_quantile_head=True,
            force_flip_invariance=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
        ))
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(min(len(values), MAX_CONTEXT))
        total, skip = target_steps(context, target_index)
        _point_out, q_out = self.model.forecast(
            horizon=total, inputs=[values])
        # q_out: (batch, horizon, 10); column 0 is the mean and
        # columns 1..9 are the quantiles 0.1..0.9.
        q = np.asarray(q_out, dtype=float)[0][skip:, 1:10]
        levels = [round(0.1 * i, 1) for i in range(1, 10)]
        qmap = {float(level): q[:, j] for j, level in enumerate(levels)
                if float(level) in [float(x) for x in quantiles]}
        point = qmap[0.5] if 0.5 in qmap else np.median(q, axis=1)
        return ForecastResult(point=point, quantiles=qmap)

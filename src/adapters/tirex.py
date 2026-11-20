"""TiRex — NX-AI.

Checkpoint: NX-AI/TiRex (NXAI Community License), via the
tirex-ts library (pinned at 1.1.1 in MODELS.md). TiRex
predicts quantiles directly; the point forecast recorded is
the predictive median (the 0.5 quantile). The snapshot context
is passed in full (the model is built for long contexts); the
length actually passed is recorded on every call.

Run note (DECISIONS.md #13): TiRex's optional custom CUDA
kernels need compute capability 8.0 or later; on a T4 (7.5)
the model runs through its standard PyTorch path.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from .base import ForecastResult, target_steps

CHECKPOINT = "NX-AI/TiRex"


class TiRexAdapter:
    name = "tirex"

    def __init__(self, device: str | None = None):
        import torch
        from tirex import load_model

        dev = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = load_model(CHECKPOINT, device=dev)
        # The library truncates the context to the model's own
        # maximum (config value, read by the library itself);
        # the effective length recorded per call is the smaller
        # of the two.
        self.max_context = int(getattr(self.model, "max_context_length", 0)) or None
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(
            min(len(values), self.max_context) if self.max_context else len(values))
        total, skip = target_steps(context, target_index)
        q_tensor, _mean = self.model.forecast(
            context=values, prediction_length=total,
            output_type="numpy", quantile_levels=list(quantiles))
        q = _quantile_matrix(q_tensor, total, len(quantiles))[skip:]
        q = np.sort(q, axis=1)
        qmap = {float(level): q[:, j] for j, level in enumerate(quantiles)}
        point = qmap[0.5] if 0.5 in qmap else np.median(q, axis=1)
        return ForecastResult(point=point, quantiles=qmap)


def _quantile_matrix(q_tensor, horizon: int, n_levels: int) -> np.ndarray:
    """Normalise TiRex's quantile output to (horizon, n_levels)."""
    q = np.asarray(q_tensor, dtype=float)
    q = np.squeeze(q)
    if q.shape == (horizon, n_levels):
        return q
    if q.shape == (n_levels, horizon):
        return q.T
    raise ValueError(f"unexpected TiRex quantile shape {q.shape}")

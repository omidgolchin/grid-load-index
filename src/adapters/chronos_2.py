"""Chronos-2 — Amazon.

Checkpoint: amazon/chronos-2 (Apache-2.0), via the
chronos-forecasting library (>= 2.0). Chronos-2 predicts
quantiles directly; the point forecast recorded is the
predictive median (the 0.5 quantile). The model's maximum
context is 8,192, so the index's 2,048 hours are passed in
full; the length actually passed is recorded on every call.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "amazon/chronos-2"


class Chronos2Adapter:
    name = "chronos_2"

    def __init__(self, device: str | None = None):
        from chronos import Chronos2Pipeline

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.pipeline = Chronos2Pipeline.from_pretrained(
            CHECKPOINT, device_map=self.device)
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(len(values))
        total, skip = target_steps(context, target_index)
        out = self.pipeline.predict_quantiles(
            [values], prediction_length=total,
            quantile_levels=list(quantiles))
        qmap = {level: arr[skip:] for level, arr in _quantile_map(out, quantiles).items()}
        q = np.sort(np.column_stack([qmap[float(l)] for l in quantiles]), axis=1)
        qmap = {float(level): q[:, j] for j, level in enumerate(quantiles)}
        point = qmap[0.5] if 0.5 in qmap else np.median(q, axis=1)
        return ForecastResult(point=point, quantiles=qmap)


def _quantile_map(out, quantiles) -> dict[float, np.ndarray]:
    """Parse predict_quantiles' return into {level: array}.

    chronos-forecasting 2.3 returns a tuple whose first element
    is a list of quantile tensors, one per input series, each of
    shape (batch, horizon, n_levels) or (horizon, n_levels) with
    columns in the requested level order. A DataFrame return
    (older/newer shapes of the API) is handled by matching
    column names to levels.
    """
    first = out[0] if isinstance(out, tuple) else out
    item = first[0] if isinstance(first, (list, tuple)) else first
    if hasattr(item, "columns"):  # DataFrame
        qmap: dict[float, np.ndarray] = {}
        for level in quantiles:
            col = next(c for c in item.columns
                       if _as_float(c) is not None
                       and abs(_as_float(c) - level) < 1e-9)
            qmap[float(level)] = item[col].to_numpy(dtype=float)
        return qmap
    arr = item.detach().cpu().numpy() if hasattr(item, "detach") else np.asarray(item)
    arr = np.asarray(arr, dtype=float)
    if arr.ndim == 3:
        arr = arr[0]
    if arr.ndim != 2 or arr.shape[1] != len(quantiles):
        raise ValueError(f"unexpected Chronos-2 quantile shape {arr.shape}")
    return {float(level): arr[:, j] for j, level in enumerate(quantiles)}


def _as_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

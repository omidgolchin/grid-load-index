"""Granite TTM r2 — IBM.

Checkpoint: ibm-granite/granite-timeseries-ttm-r2
(Apache-2.0), via granite-tsfm (its vendored
TinyTimeMixerForPrediction; current transformers releases no
longer ship the model). Sampling is driven by the checkpoint
configuration's num_parallel_samples (100). Two properties
of the checkpoint shape this adapter, both recorded in
MODELS.md:

- Its context length is 512 in the default revision, below
  the index's 2,048, so the model sees the last 512 hours of
  the snapshot context; the effective length is recorded on
  every call. The checkpoint also publishes longer-context
  revisions (1,024 and 1,536 hours, same 96-hour head); the
  adapter takes the revision and context length as arguments
  so a run can use one (see DEVIATIONS.md).
- Its forecast head emits 96 hours. The week-ahead span is
  167–169 hours, so the adapter forecasts the first 96 hours
  from the snapshot context and the remaining hours from a
  context extended with the model's own first-block forecast
  (its point path for the sampled paths' conditioning, and
  each sampled path for the point). No value after the
  snapshot cutoff is used — the extension is the model's own
  output, the same information an autoregressive model
  consumes internally. See DECISIONS.md.

The checkpoint's configuration names a Student-t
distribution output, but it also trains with an mse loss,
and the library builds the distribution head only for an
nll loss — so as released, the checkpoint is a point
forecaster and provides no quantiles (DECISIONS.md #38).
The model runs on CPU.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "ibm-granite/granite-timeseries-ttm-r2"
CONTEXT_LENGTH = 512
HEAD_LENGTH = 96


class TTMAdapter:
    name = "ttm"

    def __init__(self, device: str | None = None, revision: str | None = None,
                 context_length: int = CONTEXT_LENGTH):
        try:
            from tsfm_public.models.tinytimemixer.modeling_tinytimemixer import (
                TinyTimeMixerForPrediction,
            )
        except ImportError:  # older transformers that still ship the model
            from transformers import TinyTimeMixerForPrediction

        self.device = device or "cpu"
        self.context_length = int(context_length)
        self.model = TinyTimeMixerForPrediction.from_pretrained(
            CHECKPOINT, revision=revision)
        self.model = self.model.to(self.device)
        self.model.eval()
        self.effective_context_len: int | None = None

    def _block_point(self, values: np.ndarray) -> np.ndarray:
        """Point forecast for one block: (HEAD_LENGTH,)."""
        x = torch.tensor(values[-self.context_length:], dtype=torch.float32,
                         device=self.device).view(1, -1, 1)
        with torch.no_grad():
            out = self.model(past_values=x)
        pred = out.prediction_outputs.detach().cpu().numpy()
        if pred.ndim == 4:  # (batch, n_samples, horizon, channels)
            return np.median(pred[0, :, :, 0], axis=0)
        if pred.ndim == 3:  # (batch, horizon, channels)
            return pred[0, :, 0]
        raise ValueError(f"unexpected TTM output shape {pred.shape}")

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(min(len(values), self.context_length))
        total, skip = target_steps(context, target_index)
        point = self._block_point(values)
        if total > HEAD_LENGTH:
            extended = np.concatenate([values, point])
            rest = self._block_point(extended)
            point = np.concatenate([point, rest])
        # The released checkpoint is a point forecaster (its
        # configuration trains with an mse loss, so the library
        # builds no distribution head despite the
        # distribution_output field); it provides no quantiles.
        return ForecastResult(point=point[skip:total], quantiles=None)

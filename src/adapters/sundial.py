"""Sundial — THUML.

Checkpoint: thuml/sundial-base-128m (Apache-2.0), via
transformers with the model's own code (trust_remote_code).
Sundial generates sample paths; quantiles are the empirical
quantiles of the samples and the point forecast recorded is
the predictive median (the 0.5 quantile). The number of
samples is the model code's documented default (20). The
model's context limit is 2,880, so the snapshot context is
passed in full; the length actually passed is recorded on
every call.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "thuml/sundial-base-128m"
NUM_SAMPLES = 20


class SundialAdapter:
    name = "sundial"

    def __init__(self, device: str | None = None):
        from transformers import AutoModelForCausalLM

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModelForCausalLM.from_pretrained(
            CHECKPOINT, trust_remote_code=True, torch_dtype=torch.float32)
        self.model = self.model.to(self.device)
        self.model.eval()
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(len(values))
        seq = torch.tensor(values[None, :], dtype=torch.float32, device=self.device)
        total, skip = target_steps(context, target_index)
        with torch.no_grad():
            out = self.model.generate(seq, max_new_tokens=total,
                                      num_samples=NUM_SAMPLES)
        samples = _samples_of(out, total)[:, skip:]
        qmap = {float(level): np.quantile(samples, level, axis=0) for level in quantiles}
        point = qmap[0.5] if 0.5 in qmap else np.median(samples, axis=0)
        return ForecastResult(point=point, quantiles=qmap)


def _samples_of(out, horizon: int) -> np.ndarray:
    """Sundial's generate output as an array (n_samples, horizon)."""
    if hasattr(out, "detach"):
        out = out.detach().cpu().numpy()
    samples = np.asarray(out, dtype=float)
    samples = np.squeeze(samples)
    if samples.ndim == 1:
        samples = samples[None, :]
    if samples.ndim == 3:  # (n_samples, horizon, 1) or similar trailing channel
        samples = samples[:, :, 0]
    assert samples.ndim == 2 and samples.shape[-1] == horizon, \
        f"unexpected Sundial output shape {samples.shape}"
    return samples

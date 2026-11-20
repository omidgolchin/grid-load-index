"""Time-MoE — Time-MoE project.

Checkpoint: Maple728/TimeMoE-50M (Apache-2.0), via
transformers with the model's own code (trust_remote_code).
Time-MoE is an autoregressive point forecaster: it gives no
quantiles, so it contributes point metrics only (PLAN.md).
Following the model repository's documented usage, the
context is normalised by its own mean and standard deviation,
the model generates greedily, and the generated values are
mapped back with the same mean and standard deviation. The
model's maximum sequence length is 4,096 (context + horizon),
so the index's 2,048 hours are passed in full; the length
actually passed is recorded on every call.

The model's code targets transformers 4.40.1 (the version
named in the model repository); the adapter runs in an
environment with that version pinned.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .base import ForecastResult, target_steps

CHECKPOINT = "Maple728/TimeMoE-50M"


def _patch_generation_mixin() -> None:
    """Restore the cache-format keyword the model's generation
    mixin passes, on transformers versions that removed it.

    The model's own generation code (written against
    transformers 4.40.1) calls
    GenerationMixin._extract_past_from_model_output with a
    standardize_cache_format keyword that transformers removed
    in 4.43. Where the installed transformers still accepts the
    keyword this does nothing; where it does not, a wrapper
    accepts and ignores it (the returned cache is passed
    straight back to the model's own forward, which consumes
    the legacy format it produced).
    """
    import inspect

    from transformers.generation.utils import GenerationMixin

    fn = GenerationMixin._extract_past_from_model_output
    if "standardize_cache_format" in inspect.signature(fn).parameters:
        return

    def wrapper(self, outputs, standardize_cache_format=False):
        if standardize_cache_format:
            return fn(self, outputs)
        # The un-standardised behaviour the model's code was
        # written against: hand back the cache exactly as the
        # model's forward produced it (the legacy tuple format
        # its prepare_inputs_for_generation reads).
        past = getattr(outputs, "past_key_values", None)
        if past is None and isinstance(outputs, dict):
            past = outputs.get("past_key_values")
        return past if past is not None else fn(self, outputs)

    GenerationMixin._extract_past_from_model_output = wrapper


class TimeMoEAdapter:
    name = "time_moe"

    def __init__(self, device: str | None = None):
        from transformers import AutoModelForCausalLM

        _patch_generation_mixin()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModelForCausalLM.from_pretrained(
            CHECKPOINT, device_map=self.device, trust_remote_code=True,
            torch_dtype=torch.float32)
        self.model.eval()
        self.effective_context_len: int | None = None

    def forecast(self, context: pd.Series, target_index: pd.DatetimeIndex,
                 quantiles: Sequence[float]) -> ForecastResult:
        values = context.to_numpy(dtype=float)
        self.effective_context_len = int(len(values))
        seq = torch.tensor(values[None, :], dtype=torch.float32, device=self.device)
        mean = seq.mean(dim=-1, keepdim=True)
        std = seq.std(dim=-1, keepdim=True)
        normed = (seq - mean) / std
        total, skip = target_steps(context, target_index)
        with torch.no_grad():
            out = self.model.generate(normed, max_new_tokens=total)
        generated = out[:, -total:][:, skip:].to(dtype=torch.float32)
        point = (generated * std + mean)[0].cpu().numpy()
        return ForecastResult(point=point, quantiles=None)

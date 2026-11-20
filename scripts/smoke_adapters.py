"""Smoke-test foundation-model adapters on a synthetic context.

Builds one synthetic 2,048-hour context (daily + weekly cycles
plus noise, fixed seed), asks each named adapter for a forecast
over a synthetic target span, and checks: the point forecast
has the span's length and is finite; every provided quantile
has the span's length, is finite, and the quantiles do not
cross (level order at every hour); and the adapter's recorded
effective context length. Prints one PASS/FAIL line per adapter
with its per-call seconds.

Usage (with the python of the environment that holds the
adapter's library):
  .venv-fm/bin/python scripts/smoke_adapters.py chronos_bolt toto
  .venv-fm/bin/python scripts/smoke_adapters.py ttm --horizon 168
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import spec  # noqa: E402
from scripts.run_foundation import make_adapter  # noqa: E402


def synthetic_context() -> pd.Series:
    rng = np.random.default_rng(20261119)
    hours = np.arange(spec.CONTEXT_HOURS)
    values = (1000.0
              + 200.0 * np.sin(2 * np.pi * hours / 24)
              + 120.0 * np.sin(2 * np.pi * hours / 168)
              + rng.normal(0, 15, len(hours)))
    index = pd.date_range(end=pd.Timestamp("2025-11-03 13:00"), periods=len(hours), freq="1h")
    return pd.Series(values, index=index)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("methods", nargs="+")
    ap.add_argument("--horizon", type=int, default=24)
    args = ap.parse_args()
    context = synthetic_context()
    target_index = pd.date_range(start=context.index[-1] + pd.Timedelta(hours=11),
                                 periods=args.horizon, freq="1h")
    for method in args.methods:
        t0 = time.time()
        try:
            adapter = make_adapter(method)
            load_s = time.time() - t0
            t1 = time.time()
            result = adapter.forecast(context, target_index, spec.QUANTILES)
            call_s = time.time() - t1
            problems = []
            if len(result.point) != args.horizon or not np.isfinite(result.point).all():
                problems.append(f"point shape/finite: {result.point.shape}")
            if result.quantiles:
                q = np.column_stack([result.quantiles[q] for q in sorted(result.quantiles)])
                if q.shape != (args.horizon, len(result.quantiles)):
                    problems.append(f"quantile shape {q.shape}")
                if not np.isfinite(q).all():
                    problems.append("non-finite quantiles")
                if (np.diff(q, axis=1) < -1e-6).any():
                    problems.append("quantiles cross")
            status = "PASS" if not problems else "FAIL " + "; ".join(problems)
            print(f"{method}: {status}; load {load_s:.1f}s; call {call_s:.2f}s; "
                  f"effective_context={adapter.effective_context_len}; "
                  f"quantiles={'yes' if result.quantiles else 'no'}", flush=True)
        except Exception as exc:
            print(f"{method}: FAIL {type(exc).__name__}: {exc}", flush=True)


if __name__ == "__main__":
    main()

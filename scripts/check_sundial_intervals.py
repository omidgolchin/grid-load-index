"""Check Sundial's intervals against the model's own quick-start.

Review item 4 (Claude's review of the v1 build, 2026-11-20):
Sundial's scored 80% coverage is 0.32, far below the nominal
0.80. Before that number is published, verify on 3 windows
that the adapter's sampling matches the official Sundial
quick-start generate call on identical contexts:

  1. adapter path — src.adapters.sundial.SundialAdapter.forecast;
  2. quick-start path — the model card / repository README's
     own example: AutoModelForCausalLM.from_pretrained(...,
     trust_remote_code=True), then model.generate(seq,
     max_new_tokens=<steps>, num_samples=20).

Both paths are seeded identically (torch and numpy), so if
the adapter is a faithful wrapper the two sample sets agree
closely; the comparison reports the largest absolute
difference per quantile level and the mean interval widths.
A third comparison ties the check to the shipped scores: the
stored forecast quantiles for the same windows (a different
random draw, so compared in distribution — mean width ratio
and per-hour width correlation).

Run with the Sundial environment (transformers 4.40.1):

  .venv-sundial2/bin/python scripts/check_sundial_intervals.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import snapshots, spec  # noqa: E402
from src.adapters.base import target_steps  # noqa: E402
from src.adapters.sundial import NUM_SAMPLES, SundialAdapter, _samples_of  # noqa: E402

SEED = 20261120
WINDOWS = [("AECI", "2025-11-03"), ("PJM", "2026-03-09"), ("ERCO", "2026-07-06")]


def quickstart_samples(model, context: pd.Series, total: int) -> np.ndarray:
    """The official quick-start generate call, verbatim in shape."""
    seq = torch.tensor(context.to_numpy(dtype=float)[None, :],
                       dtype=torch.float32)
    with torch.no_grad():
        out = model.generate(seq, max_new_tokens=total, num_samples=NUM_SAMPLES)
    return _samples_of(out, total)


def main() -> None:
    snaps = snapshots.load_snapshots()
    targets = snapshots.load_targets()
    stored = pd.read_parquet(spec.FORECAST_DIR / "sundial.parquet").set_index(
        ["series", "issue_date", "horizon", "timestamp_utc"])
    adapter = SundialAdapter()
    print(f"windows: {WINDOWS}; seed {SEED}; num_samples {NUM_SAMPLES}")
    for series, issue_date in WINDOWS:
        snap = snaps[(snaps["series"] == series)
                     & (snaps["issue_date"] == issue_date)].iloc[0]
        context = snapshots.context_series(snap)
        tgt = targets[(targets["series"] == series)
                      & (targets["issue_date"] == issue_date)
                      & (targets["horizon"] == spec.HORIZON_WEEK)].iloc[0]
        week_index = pd.DatetimeIndex(tgt["timestamps_utc"])
        total, skip = target_steps(context, week_index)

        torch.manual_seed(SEED)
        np.random.seed(SEED)
        res = adapter.forecast(context, week_index, spec.QUANTILES)

        torch.manual_seed(SEED)
        np.random.seed(SEED)
        samples = quickstart_samples(adapter.model, context, total)[:, skip:]
        qs = {float(q): np.quantile(samples, q, axis=0) for q in spec.QUANTILES}

        diffs = {q: float(np.max(np.abs(res.quantiles[q] - qs[q]))) for q in spec.QUANTILES}
        width_adapter = res.quantiles[0.9] - res.quantiles[0.1]
        width_quick = qs[0.9] - qs[0.1]

        sub = stored.loc[(series, issue_date, spec.HORIZON_WEEK)].reindex(week_index)
        width_stored = (sub["q0.9"] - sub["q0.1"]).to_numpy(dtype=float)
        ratio = float(np.mean(width_quick) / np.mean(width_stored))
        corr = float(np.corrcoef(width_quick, width_stored)[0, 1])

        print(f"\n{series} {issue_date} (week span, {len(week_index)} h, skip {skip})")
        print(f"  max |adapter - quick-start| by level: "
              + ", ".join(f"q{q}: {diffs[q]:.4f}" for q in (0.1, 0.5, 0.9)))
        print(f"  mean width [q0.1, q0.9]: adapter {np.mean(width_adapter):.1f} MW, "
              f"quick-start {np.mean(width_quick):.1f} MW, stored {np.mean(width_stored):.1f} MW")
        print(f"  sample spread (mean per-hour std of quick-start samples): "
              f"{float(np.mean(np.std(samples, axis=0))):.1f} MW")
        print(f"  quick-start vs stored widths: mean ratio {ratio:.3f}, correlation {corr:.3f}")


if __name__ == "__main__":
    main()

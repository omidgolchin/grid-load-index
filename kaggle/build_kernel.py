"""Build a self-contained Kaggle kernel for one foundation model.

The kernel script is assembled from the repo's own code — the
adapter base module and the model's adapter file, with the
relative import between them inlined — plus a runner that
mirrors scripts/run_foundation.py: one adapter call per
snapshot on the week span, the day-ahead result is its first
local day, per-series part files as checkpoints, failures and
per-snapshot timings written next to the parts.

Modes:
  probe — 24 snapshots (6 series x 4 issue days, spread over
          the window), for timing only;
  full  — every snapshot, checkpointed per series.

Usage:
  .venv/bin/python kaggle/build_kernel.py chronos_bolt probe
  .venv/bin/python kaggle/build_kernel.py chronos_bolt full
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_foundation import METHODS  # noqa: E402

ADAPTER_CLASS = {m: METHODS[m][1] for m in METHODS}
ADAPTER_MODULE = {m: METHODS[m][0].rsplit(".", 1)[1] for m in METHODS}

# Pip installs run inside the kernel, before anything else:
# one "pip install" argument string per command, run in order.
# Versions are the ones verified for this stage (see MODELS.md
# and the run ledger in SPEND.md).
#
# uni2ts note: uni2ts 2.0.0 pins numpy ~=1.26 and scipy ~=1.11,
# which have no wheels for the kernel image's Python 3.13 and
# fail as source builds. The Moirai adapters therefore install
# uni2ts with --no-deps and add the runtime dependencies it
# needs at versions with 3.13 wheels; the model code itself is
# the pinned release from the repository. gluonts is pinned to
# 0.14.4, the version the adapters are verified against:
# gluonts 0.16's forecast generator expects distribution-style
# network outputs and breaks Moirai 2's sample forecasts.
UNI2TS_INSTALLS = [
    "install -q --no-deps git+https://github.com/SalesforceAIResearch/uni2ts.git",
    "install -q --no-deps gluonts==0.14.4",
    "install -q lightning hydra-core einops jaxtyping orjson python-dotenv multiprocess toolz",
]
PIP_INSTALLS = {
    "chronos_bolt": ["install -q chronos-forecasting>=2"],
    "chronos_2": ["install -q chronos-forecasting>=2"],
    "timesfm_2_5": ["install -q timesfm[torch]"],
    "moirai_2": UNI2TS_INSTALLS,
    "tirex": ["install -q tirex-ts==1.1.1"],
    "toto": ["install -q toto-ts", "install -q torchvision==0.22.0"],
    # Sundial's model code uses DynamicCache.seen_tokens,
    # removed in transformers 4.47; 4.46.3 is the last line
    # with it and its dependencies have 3.13 wheels.
    "sundial": ["install -q transformers==4.46.3 accelerate"],
    "ttm": ["install -q granite-tsfm"],
    "moirai_moe": UNI2TS_INSTALLS,
    # Time-MoE's model code targets transformers 4.40.1, whose
    # tokenizers pin (>=0.19,<0.20) has no wheels for the kernel
    # image's Python 3.13, and 4.40.1 rejects newer tokenizers
    # at import. The kernel therefore uses transformers 4.47.1,
    # the first release line whose dependencies all have 3.13
    # wheels; the adapter uses only the stable
    # AutoModelForCausalLM + generate surface, verified locally
    # against 4.40.1.
    "time_moe": ["install -q transformers==4.47.1 accelerate"],
}

PROBE_SERIES_IDX = [0, 10, 20, 30, 40, 48]
PROBE_ISSUE_IDX = [0, 17, 34, 50]

RUNNER = '''
# ---------------- runner (mirrors scripts/run_foundation.py) ----------------
import time
import traceback

import numpy as np
import pandas as pd

QUANTILES = tuple(round(0.1 * i, 1) for i in range(1, 10))
QUANTILE_COLUMNS = [f"q{q:.1f}" for q in QUANTILES]
_found = sorted(Path("/kaggle/input").rglob("snapshots.parquet"))
assert _found, "snapshots.parquet not found under /kaggle/input"
INPUT_DIR = _found[0].parent
print(f"dataset mounted at {INPUT_DIR}", flush=True)
WORK = Path("/kaggle/working")
PARTS = WORK / "parts"
PARTS.mkdir(parents=True, exist_ok=True)

snaps = pd.read_parquet(INPUT_DIR / "snapshots.parquet")
targets = pd.read_parquet(INPUT_DIR / "targets_lite.parquet")
tgt = {(r["series"], r["issue_date"], r["horizon"]): r for _, r in targets.iterrows()}

series_list = sorted(snaps["series"].unique())
if MODE == "probe":
    series_list = [series_list[i] for i in PROBE_SERIES_IDX]

adapter = ADAPTER_CLS()
print(f"adapter loaded: {METHOD}; device={getattr(adapter, 'device', 'n/a')}", flush=True)


def rows_from_result(series, issue_date, horizon, target_index, point, quantiles):
    rows = []
    quantiles = quantiles or {}
    for i, ts in enumerate(target_index):
        row = {"method": METHOD, "series": series, "issue_date": issue_date,
               "horizon": horizon, "timestamp_utc": ts, "point": float(point[i])}
        for q in QUANTILES:
            arr = quantiles.get(q)
            row[f"q{q:.1f}"] = float(arr[i]) if arr is not None else np.nan
        rows.append(row)
    return rows


total_windows = 0
total_failures = 0
t_start = time.time()
for series in series_list:
    part_path = PARTS / f"{METHOD}__{series}.parquet"
    if part_path.exists() and MODE == "full":
        print(f"skip {series} (part exists)", flush=True)
        continue
    sub = snaps[snaps["series"] == series].sort_values("issue_date")
    if MODE == "probe":
        keep = set(sub["issue_date"].tolist()[i] for i in PROBE_ISSUE_IDX)
        sub = sub[sub["issue_date"].isin(keep)]
    rows, failures, timings = [], [], []
    for _, snap in sub.iterrows():
        issue_date = snap["issue_date"]
        index = pd.date_range(end=snap["context_end_utc"], periods=2048, freq="1h")
        context = pd.Series(np.asarray(snap["context"], dtype=float), index=index, name=series)
        week_index = pd.DatetimeIndex(tgt[(series, issue_date, "week")]["timestamps_utc"])
        day_index = pd.DatetimeIndex(tgt[(series, issue_date, "day")]["timestamps_utc"])
        assert (week_index[: len(day_index)] == day_index).all()
        t_call = time.time()
        failed = False
        try:
            result = adapter.forecast(context, week_index, QUANTILES)
            if not np.isfinite(result.point).all():
                raise ValueError("non-finite point forecast")
            rows += rows_from_result(series, issue_date, "week", week_index,
                                     result.point, result.quantiles)
            day_q = None
            if result.quantiles:
                day_q = {q: a[: len(day_index)] for q, a in result.quantiles.items()}
            rows += rows_from_result(series, issue_date, "day", day_index,
                                     result.point[: len(day_index)], day_q)
            total_windows += 2
        except Exception as exc:
            failed = True
            total_failures += 2
            for horizon in ("day", "week"):
                failures.append({"method": METHOD, "series": series,
                                 "issue_date": issue_date, "horizon": horizon,
                                 "error": f"{type(exc).__name__}: {exc}"})
            traceback.print_exc()
        timings.append({"method": METHOD, "series": series, "issue_date": issue_date,
                        "seconds": round(time.time() - t_call, 3),
                        "effective_context": getattr(adapter, "effective_context_len", None),
                        "failed": failed})
    frame = pd.DataFrame(rows, columns=["method", "series", "issue_date", "horizon",
                                        "timestamp_utc", "point"] + QUANTILE_COLUMNS)
    frame.to_parquet(part_path, index=False)
    if failures:
        pd.DataFrame(failures).to_csv(PARTS / f"{METHOD}__{series}.failures.csv", index=False)
    pd.DataFrame(timings).to_csv(PARTS / f"{METHOD}__{series}.timings.csv", index=False)
    print(f"{series}: {len(frame)} rows, {len(failures)} failed windows, "
          f"elapsed {time.time() - t_start:.0f}s", flush=True)

summary = {"method": METHOD, "mode": MODE, "windows": total_windows,
           "failed_windows": total_failures, "seconds": round(time.time() - t_start, 1),
           "effective_context": getattr(adapter, "effective_context_len", None)}
(WORK / "run_summary.json").write_text(json.dumps(summary, indent=1))
print("RUN SUMMARY", summary, flush=True)
'''


def _strip(text: str) -> str:
    """Drop the lines that cannot survive inlining: the relative
    import of the base module and the __future__ import (the
    assembled script carries one __future__ import at its top)."""
    lines = [ln for ln in text.splitlines()
             if not ln.startswith("from .base import")
             and not ln.startswith("from __future__")]
    return "\n".join(lines)


def adapter_source(method: str) -> str:
    path = ROOT / "src" / "adapters" / f"{ADAPTER_MODULE[method]}.py"
    return _strip(path.read_text())


def base_source() -> str:
    return _strip((ROOT / "src" / "adapters" / "base.py").read_text())


def build(method: str, mode: str) -> Path:
    out_dir = ROOT / "kaggle" / f"{method}_{mode}"
    out_dir.mkdir(parents=True, exist_ok=True)
    installs = PIP_INSTALLS[method]
    install_block = ""
    if installs:
        import shlex
        lines = ["import subprocess, sys"]
        for cmd in installs:
            args = ", ".join(f'"{a}"' for a in shlex.split(cmd))
            lines.append(f"subprocess.run([sys.executable, '-m', 'pip', {args}], check=True)")
        install_block = "\n".join(lines) + "\n"
    header = (
        f"# Grid Load Forecasting Index — foundation-model run: {method} ({mode})\n"
        "# Assembled by kaggle/build_kernel.py from src/adapters/. Do not edit here.\n"
        "from __future__ import annotations\n\n"
        "import json\n"
        "from pathlib import Path\n\n"
        f"METHOD = \"{method}\"\nMODE = \"{mode}\"\n"
        f"PROBE_SERIES_IDX = {PROBE_SERIES_IDX}\nPROBE_ISSUE_IDX = {PROBE_ISSUE_IDX}\n\n"
        + install_block + "\n")
    script = (header + base_source() + "\n\n" + adapter_source(method)
              + f"\n\nADAPTER_CLS = {ADAPTER_CLASS[method]}\n" + RUNNER)
    code_file = out_dir / "kernel.py"
    code_file.write_text(script)
    title = f"GLI {method.replace('_', ' ')} {mode}"
    meta = {
        "id": f"omidgolchin/gli-{method.replace('_', '-')}-{mode}",
        "title": title,
        "code_file": "kernel.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": True,
        "dataset_sources": ["omidgolchin/grid-load-index-data"],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
        "machine_shape": "NvidiaTeslaT4",
    }
    (out_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    print(f"wrote {code_file} ({len(script)} bytes) and metadata in {out_dir}")
    return out_dir


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])

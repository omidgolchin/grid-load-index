"""Finalise the private Kaggle dataset (brief Step 8): version 2,
refreshed as version 3 after the 2026-11-20 review round.

Version 1 (scripts/kaggle_dataset.py) carried only the run
inputs — snapshot contexts and target timestamps. Version 2
added the rest of the Step 8 record:

- the pinned retrospective data snapshot: the per-series
  evaluation extractions stacked into one file (reported demand,
  imputation flags, operator forecasts, cleaned demand);
- every method's forecasts, one parquet per method, as merged
  in results/forecasts/ and registered in its MANIFEST;
- the scores: results/scores/summary.csv,
  window_scores.parquet and (version 3) paired.csv;
- the manifests (forecast, snapshot, extraction, qualifying
  series).

Version 3 is the post-review refresh proposed in
REPORT_INDEX_2.md: the regenerated score files (summary.csv
with beats_snaive and avg_win_rate, the new paired.csv,
window_scores.parquet), Moirai 2.0 unflagged, and Granite
TTM's forecasts from the 1,536-hour-context run replacing
the 512-hour run. Every file uploads anew: the v3 blob state
lives in upload_state_v3.json, separate from the version 2
state (upload_state_v2.json, kept for the record), so no
version 2 blob token is reused for changed content.

Privacy is a dataset-level property set at creation (version 1
was created private); after the version posts, this script reads
the dataset back and fails unless isPrivate is true.

Usage:
  python3 scripts/kaggle_dataset_step8.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STAGE_DIR = ROOT / "data" / "kaggle_dataset" / "step8"
OWNER, SLUG = "omidgolchin", "grid-load-index-data"

spec = importlib.util.spec_from_file_location(
    "kaggle_dataset", Path(__file__).with_name("kaggle_dataset.py"))
kd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kd)


def stage_files() -> list[Path]:
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []

    def stage(name: str, src: Path) -> Path:
        out = STAGE_DIR / name
        if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            out.write_bytes(src.read_bytes())
        files.append(out)
        return out

    # Run inputs (as in version 1).
    stage("snapshots.parquet", ROOT / "data" / "snapshots" / "snapshots.parquet")
    targets_src = ROOT / "data" / "snapshots" / "targets.parquet"
    targets_out = STAGE_DIR / "targets_lite.parquet"
    if not targets_out.exists() or targets_out.stat().st_mtime < targets_src.stat().st_mtime:
        targets = pd.read_parquet(
            targets_src, columns=["series", "issue_date", "horizon", "timestamps_utc"])
        targets.to_parquet(targets_out, index=False)
    files.append(targets_out)

    # The pinned retrospective snapshot: all qualifying series'
    # evaluation extractions in one frame.
    eval_out = STAGE_DIR / "eval_series.parquet"
    eval_srcs = sorted((ROOT / "data" / "eval").glob("*.parquet"))
    newest = max(p.stat().st_mtime for p in eval_srcs)
    if not eval_out.exists() or eval_out.stat().st_mtime < newest:
        frames = []
        for path in eval_srcs:
            frame = pd.read_parquet(path)
            frame.insert(0, "series", path.stem)
            frames.append(frame)
        pd.concat(frames, ignore_index=True).to_parquet(eval_out, index=False)
    files.append(eval_out)

    # Forecasts, one file per method, plus their manifest.
    for path in sorted((ROOT / "results" / "forecasts").glob("*.parquet")):
        stage(path.name, path)
    stage("forecasts_manifest.csv", ROOT / "results" / "forecasts" / "MANIFEST.csv")

    # Scores.
    stage("scores_summary.csv", ROOT / "results" / "scores" / "summary.csv")
    stage("scores_paired.csv", ROOT / "results" / "scores" / "paired.csv")
    stage("window_scores.parquet", ROOT / "results" / "scores" / "window_scores.parquet")

    # Data manifests.
    for name in ("snapshot_manifest.csv", "extraction_manifest.csv",
                 "qualifying_series.csv"):
        stage(name, ROOT / "data" / "manifests" / name)
    return files


STATE_PATH = STAGE_DIR / "upload_state_v3.json"


def upload_with_retry(path: Path, attempts: int = 5) -> str:
    """Upload one blob, retrying transient connection failures with
    a fresh blob token each time (the signed URL may not survive a
    dropped connection)."""
    delay = 10
    for attempt in range(1, attempts + 1):
        try:
            return kd.upload_blob(path)
        except Exception as exc:  # connection-level failures are transient here
            if attempt == attempts:
                raise
            print(f"  {path.name}: attempt {attempt} failed ({type(exc).__name__}); "
                  f"retrying in {delay}s", flush=True)
            time.sleep(delay)
            delay *= 2
    raise AssertionError("unreachable")


def main() -> None:
    files = stage_files()
    total_mb = sum(p.stat().st_size for p in files) / 1e6
    print(f"staging {len(files)} files, {total_mb:.0f} MB", flush=True)
    state: dict[str, str] = {}
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
    tokens = []
    for path in files:
        if path.name in state:
            print(f"reusing uploaded blob for {path.name}", flush=True)
            token = state[path.name]
        else:
            token = upload_with_retry(path)
            state[path.name] = token
            STATE_PATH.write_text(json.dumps(state, indent=1))
            print(f"uploaded {path.name} ({path.stat().st_size / 1e6:.1f} MB)", flush=True)
        tokens.append({"token": token, "description": path.name})
    payload = {
        "versionNotes": (
            "Version 3 (post-review refresh, 2026-11-20): scores "
            "regenerated after the review round — scores_summary.csv "
            "uses beats_snaive and adds avg_win_rate, scores_paired.csv "
            "is new (paired bootstrap differences), window_scores.parquet "
            "regenerated; Moirai 2.0 is no longer flagged as released "
            "during the window (its weights were public 2025-08-06); "
            "Granite TTM's forecasts are the 1,536-hour-context run "
            "(day skill +26.3, week +15.9), replacing the 512-hour run "
            "of version 2. Run inputs, the pinned snapshot, the other "
            "methods' forecasts and the manifests are unchanged from "
            "version 2 but re-uploaded so no blob is shared between "
            "versions."),
        "subtitle": "Snapshots, forecasts and scores for the Grid Load Forecasting Index",
        "description": (
            "Data for the Grid Load Forecasting Index (release v2026.11): a "
            "versioned leaderboard of zero-shot time-series foundation models "
            "on hourly EIA Form 930 demand across 49 US balancing authorities, "
            "against statistical baselines and each operator's own day-ahead "
            "forecast. Contents: snapshot contexts and target timestamps "
            "(the run inputs), the pinned retrospective data snapshot "
            "(eval_series.parquet), one forecast parquet per method, the "
            "aggregate and per-window scores, and the manifests. Built from "
            "EIA Form 930 via the PUDL stable release v2026.11.0 (EIA data: "
            "US-government public domain; PUDL: CC-BY-4.0)."),
        "files": tokens,
        "categoryIds": [],
    }
    result = kd.post_json(f"/datasets/create/version/{OWNER}/{SLUG}", payload)
    print("create/version:", json.dumps(result)[:600], flush=True)
    time.sleep(5)
    view = kd.get(f"/datasets/view/{OWNER}/{SLUG}")
    print(f"version: {view.get('currentVersionNumber')}, "
          f"isPrivate: {view.get('isPrivate')}, bytes: {view.get('totalBytes')}")
    if view.get("isPrivate") is not True:
        raise SystemExit("PRIVACY CHECK FAILED: dataset is not private")
    print("privacy verified: isPrivate = true")


if __name__ == "__main__":
    main()

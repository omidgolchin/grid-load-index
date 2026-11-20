# TTM 1,536-context re-run — state

Re-run of Granite TTM r2 with the checkpoint's 1,536-hour
context revision (`1536-96-r2`), replacing the 512-context
default revision as the scored version (review item 5;
DEVIATIONS.md). Local CPU, $0, no GPU.

- **Launch command (exact):**
  `cd ~/workspace/grid-load-index && .venv-ttm/bin/python scripts/run_foundation.py --method ttm --parts-dir results/forecasts/parts_ttm1536 --state-file results/ttm1536_runner_state.md --adapter-revision 1536-96-r2 --adapter-context 1536 >> results/ttm1536_run.log 2>&1`
- **Log:** `results/ttm1536_run.log`
- **Runner's own state file:** `results/ttm1536_runner_state.md`
  (rewritten by the runner as series complete).
- **Parts:** `results/forecasts/parts_ttm1536/ttm__<SERIES>.parquet`,
  one per series (49), each with a `ttm__<SERIES>.timings.csv`
  whose `effective_context` column must read 1536. Rerunning
  the launch command skips finished series (checkpointed).
- **Merge command (after the run):**
  `.venv-ttm/bin/python scripts/run_foundation.py --method ttm --merge --parts-dir results/forecasts/parts_ttm1536`
  → writes `results/forecasts/ttm.parquet`.
- **Completion is recognised by:** the runner state file
  reading "Status: complete" with 4,998 windows and 0 failed,
  49 part files present, and the log's last line
  "complete in …s; failed windows: 0".
- **The 512-context version is preserved** at
  `results/forecasts/parts/ttm_ctx512_archive.parquet`
  (the previously merged `results/forecasts/ttm.parquet`);
  both versions' scores are reported in DEVIATIONS.md.
- **Timed subset (before launch):** AECI × 3 issue days in a
  throwaway parts dir: 0.213 s for the first snapshot
  (warm-up), then 0.024 s and 0.011 s; effective context
  recorded as 1536 on every call. The 512-context full run
  took 76 s end to end, so the full 1,536 run is expected in
  minutes — far inside the review's 8-hour cap.
- **Status:** run complete 2026-11-20 16:49 UTC — 4,998
  windows, 0 failed, 479,765 rows, 450 s elapsed; effective
  context recorded as 1536 on all 2,499 calls. Merged into
  `results/forecasts/ttm.parquet` and re-scored (see
  DEVIATIONS.md for both versions' scores).

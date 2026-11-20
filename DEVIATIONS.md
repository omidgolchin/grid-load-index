# Deviations

Changes made after scoring that alter a ranking input or a
scored artefact. Each entry reports both versions, so the
original v1 numbers stay recoverable. Decisions behind them
are in DECISIONS.md; the review round that produced both
entries is recorded in REPORT_INDEX_2.md.

## 1. Moirai 2.0 release date corrected (2026-11-20)

The v1 build recorded Moirai 2.0 as released in November 2025
and flagged it "released during window", excluding it from
the retrospective headline ranking. That date is the model's
arXiv paper (2511.11698). Its weights were public on Hugging
Face on 2025-08-06 — the repository's commit history shows
"initial commit" and "Push model using huggingface_hub" that
day, and Salesforce announced the model on 2025-08-08 — three
months before the window start of 2025-11-03. The date of
record is now the first public weights for every model
(DECISIONS #48); Moirai 2.0's flag is removed and it enters
the headline ranking.

Both headline versions:

- **As first reported (flagged).** Headline-eligible leaders:
  Chronos-2 at both horizons (day +37.4, week +23.5). Moirai
  2.0 shown flagged, day +37.2, week +24.2.
- **Corrected (unflagged).** No model is flagged. Day-ahead,
  Chronos-2 (+37.4) and Moirai 2.0 (+37.2) form the top
  group — the paired difference is −0.2 points [−2.2, +1.9],
  so they cannot be told apart — and both beat every other
  foundation model and baseline paired; only the operator
  forecast beats them. Week-ahead, Moirai 2.0 (+24.2) and
  Chronos-2 (+23.5) form the top group (paired difference
  −0.6 [−2.9, +1.2]); Moirai 2.0 beats every other method
  paired.

## 2. Granite TTM re-run at the 1,536-hour revision (2026-11-20)

The v1 run used the checkpoint's default revision, whose
context is 512 hours. TTM r2 publishes one revision per
context length (512, 1,024, 1,536); the brief's context rule
— 2,048 hours or the model's maximum — points at the 1,536
revision. TTM was re-run on local CPU with the `1536-96-r2`
revision (450 s, 4,998 windows, 0 failed, effective context
1,536 on every call; DECISIONS #52). The 1,536-hour version
is the scored one.

Both versions (skill %, 95% interval):

| Version | Day-ahead | Week-ahead |
|---|---|---|
| 512-hour revision (v1 as first scored) | +25.1 [20.3, 30.1] | +17.0 [14.5, 19.5] |
| 1,536-hour revision (scored) | +26.3 [22.4, 30.1] | +15.9 [13.3, 18.3] |

The longer context helps day-ahead (+1.1 points) and hurts
week-ahead (−1.1 points); the model's rank is unchanged at
both horizons. The 512-hour forecasts are archived at
`results/forecasts/parts/ttm_ctx512_archive.parquet`.

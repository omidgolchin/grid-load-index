# Plan — Grid Load Forecasting Index, retrospective track (v1)

Fixed on 2026-11-19, before any model is scored on the evaluation
window. Changes after this point go in DEVIATIONS.md, and results
show both versions.

## Question

On hourly electricity demand across US balancing authorities, how
good are time-series foundation models with no training on this data,
compared with simple baselines and with each grid operator's own
day-ahead forecast?

## Data

- Source: EIA Form 930 hourly demand by balancing authority, from
  the PUDL stable release v2026.11.0, file
  `out_eia930__hourly_operations.parquet`, pinned by SHA-256 in
  DATA_SOURCES.md.
- Extracted dataset: one parquet per series under `data/eval/`,
  rebuilt by `scripts/extract_data.py`, covering 2019-01-01 00:00
  UTC to 2026-11-01 07:00 UTC (68,672 hours per series). Hashes in
  `data/manifests/extraction_manifest.csv`.

## Series

49 balancing authorities qualify under the screen in SCREEN.md
(continuous reporting since 2019-01-01, less than 5% missing or
flagged hours, demand-reporting, no subregions):

AECI, AVA, AZPS, BANC, BPAT, CHPD, CISO, CPLE, CPLW, DOPD, DUK, EPE,
ERCO, FMPP, FPC, FPL, GCPD, GVL, HST, IID, IPCO, ISNE, JEA, LDWP,
LGEE, MISO, NEVP, NWMT, NYIS, PACE, PACW, PGE, PJM, PNM, PSCO, SC,
SCEG, SCL, SOCO, SPA, SRP, SWPP, TAL, TEC, TEPC, TIDC, TPWR, TVA,
WALC.

Each series' timezone is the `report_timezone` PUDL records for that
BA (the timezone the BA reports in), listed in SCREEN.md.

## Cleaning rule

Fixed before scoring; looks backwards only.

- **Model inputs** (the context every method sees) use the cleaned
  series: a flagged, missing or non-positive hour is replaced by the
  cleaned value 168 hours earlier, stepping back in whole weeks
  until a usable hour is found. (This is the same value a direct
  search for the most recent usable hour on the same weekly lattice
  would find.)
- **Scoring** uses reported, unflagged values only. A target hour
  whose reported value is missing or flagged is dropped from scoring
  for every method alike.
- "Flagged" means PUDL's `demand_imputed_pudl_mwh_imputation_code`
  is non-null for that hour (see SCREEN.md).

## Issue time and snapshot

- Forecasts are issued **daily at 15:00 UTC**.
- A forecast uses only data published by then: the snapshot drops
  the last 2 hours for EIA's publication lag, so the last context
  hour is 13:00 UTC on the issue date.
- All methods see the same snapshot: the 2,048 cleaned hours ending
  at the snapshot time (or the model's maximum context, if smaller;
  the effective length actually passed is recorded at run time).
- The forecast covers whole local calendar days in the BA's own
  timezone, starting with the next local day after the issue
  instant.

## Horizons

- **Day-ahead:** the next local day (24 hours, except on DST
  transition days — see below).
- **Week-ahead:** the next 7 local days (168 hours, except as
  below).

## Retrospective window

- Issue days are weekly, on Mondays: **2025-11-03 to 2026-10-19,
  51 issue days**.
- The last issue day is set by the data: it is the latest Monday for
  which every qualifying series has reported data covering the full
  168-hour week-ahead target. The pinned file ends 2026-11-01 07:00
  UTC; the 2026-10-19 issue's targets end 2026-10-27 (local), and
  the next Monday's targets would run past the end of the file for
  every series.
- Both horizons are scored at every issue day.

## Daylight-saving transition days

Local calendar days are taken as they occur. A spring-forward day
has 23 hours and a fall-back day has 25 hours; forecasts are made
for exactly the hours in the local days targeted (so a day-ahead
forecast has 23 or 25 values on those days, and a week containing a
transition has 167 or 169), and every actual hour is scored. No hour
is dropped, duplicated or normalised away. Adapters are asked for
the exact number of hours in the target span.

## Methods

### Foundation models

Zero-shot, univariate, no fine-tuning. The model list, checkpoints,
licences and versions are fixed in MODELS.md (10 models). Quantiles
0.1–0.9 (step 0.1) are collected from every model that provides
them; a model without native quantiles contributes point metrics
only, and its quantile-loss and coverage entries are reported as
not available.

### Baselines (all fixed before scoring)

- **Seasonal naive (168 h):** the value 168 hours earlier, repeated.
  The reference for every relative score.
- **Naive (24 h):** the value 24 hours earlier. Day-ahead only.
- **AutoETS** and **AutoARIMA** from the `statsforecast` library,
  with MSTL seasonal decomposition (seasonal periods 24 and 168),
  at library defaults, fit on the same 2,048-hour context. The
  library version is pinned at run time and recorded with the
  results.
- **Operator forecast:** the EIA-930 day-ahead demand forecast
  (`demand_forecast_mwh`), day-ahead horizon only. What is known
  about its timing: EIA collects each BA's day-ahead demand forecast
  with its hourly reporting; the forecast value stored against an
  hour is the BA's forecast for that hour, made before the target
  day. EIA and PUDL do not publish a per-BA submission hour, so it
  is not aligned to the 15:00 UTC issue time; it is the operator's
  own published day-ahead product, scored on the same target hours.
  It is scored over the target hours where a forecast value exists.
  The "beats operator" share (below) counts a BA-day only when the
  operator forecast is present for all of that local day's target
  hours.

Baselines use their native prediction intervals where the library
provides them.

## Scores

Per series, per issue day, per horizon (a "window" below), following
fev-bench (Shchur et al. 2025, arXiv:2509.26468) where it applies:

- **MASE:** mean absolute error over the window's scored hours,
  divided by the seasonal-naive in-sample error over the context
  (the mean absolute 168-hour difference of the cleaned context).
- **Scaled quantile loss (SQL):** mean pinball loss over quantiles
  0.1–0.9 and the window's scored hours, divided by the same
  in-sample scale.
- **80% coverage:** the share of scored hours whose reported value
  falls inside the forecast [q0.1, q0.9] interval.
- **Daily peak-hour error:** for each local day in the target, the
  absolute error at the hour of that day's highest reported value
  (over the day's scored hours), averaged over the days in the
  window.

### Headline index value

Per model and horizon: the **skill score**, 1 − the geometric mean
of the model's relative MASE against seasonal naive across all
series × issue-day windows, with each relative MASE clipped to
[0.01, 100]. Reported as a percentage.

### Also reported

- **Win rate:** the share of series × issue-day windows in which
  the model's MASE is below seasonal naive's.
- **Beats operator** (day-ahead only): the share of BA-days in
  which the model's MAE over the day's scored hours is below the
  operator forecast's MAE over the same hours, over BA-days where
  the operator forecast covers the full local day.

### Intervals and claims

95% paired bootstrap, B = 1000, resampling series (with
replacement) and blocks of 4 consecutive issue days. A claim that
one method beats another is made only where the interval for the
paired difference excludes the reference value.

### Failures

A failed run (a model × series × issue day × horizon cell that
errors or returns unusable output) takes the seasonal-naive score
for that cell, as fev-bench does, and is flagged in the results
table.

## Contamination rule

- MODELS.md records, for every model: the public release date; the
  training-data description and cutoff as published; and whether
  EIA-930, PJM, ERCOT or other US load data appears in its
  documented training data.
- A model released after the retrospective window starts
  (2025-11-03) is still scored, is marked "released during
  window", and is excluded from the retrospective headline
  ranking.
- The live track ranks all models: its data did not exist when any
  of them was trained.

## Live track (built under this plan, started on publication)

A day-ahead forecast every day and a week-ahead forecast every
Monday, issued at 15:00 UTC from the EIA API v2 snapshot, committed
before the target day starts. Live forecasts are scored against
values as published 7 days after the target day. The workflow is
committed disabled; it is switched on when the index is published.

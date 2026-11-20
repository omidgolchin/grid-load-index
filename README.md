# Grid Load Forecasting Index

**On hourly electricity demand across US balancing authorities, how
good are time-series foundation models with no training on this
data?**

The index answers that question as a versioned leaderboard. Ten
foundation models were selected to run zero-shot on the same
forecast tasks as simple baselines and as each grid operator's
own day-ahead forecast — first on a retrospective backtest over
49 balancing authorities, and then on a live track whose
forecasts are committed before the demand they predict exists.
Nine of the ten carry scores in this release; Time-MoE is
listed unscored (see below).

Current release: **v2026.11** (retrospective window 3 November
2025 – 19 October 2026). Time-MoE is not scored in v1: its
Kaggle run failed in its environment and the local re-run was
stopped at 2 of 49 series (DECISIONS.md #45). Its row is marked
unscored in the tables below.

## The two tracks

**Retrospective.** Every Monday in the window, at 15:00 UTC,
each method forecasts from the 2,048 hours of demand published
by 13:00 UTC that day (a 2-hour publication lag, the way EIA-930
data actually arrives): the next local day (day-ahead, 24 h) and
the next 7 local days (week-ahead, 168 h), in each balancing
authority's own timezone. 51 issue days × 49 authorities.

**Live.** Once the index is published, a workflow issues the
same forecasts daily (week-ahead on Mondays) and commits each
forecast file before its target day begins. The commit time is
the proof of when the forecast was made, so no model can have
seen the answer. Live forecasts are scored against the demand
values as published seven days after the target day. The live
track is built and dry-run tested; it starts on publication.

## Results — release v2026.11

Skill is the headline score: 1 − the geometric mean of the
per-window error ratio against seasonal naive, as a percentage
(see "How to read the scores"). Intervals are 95% paired
bootstrap intervals. Windows scored: 2,494 day-ahead and 2,497
week-ahead (7 windows with no reported actuals are data gaps,
excluded for every method).

### Day-ahead (24 h)

| Model | Skill % | 95% interval | Beats seasonal naive | Coverage (80%) | Beats operator |
|---|---|---|---|---|---|
| Operator forecast | 51.4 | [37.6, 61.7] | 74.5% | — | — |
| Chronos-2 | 37.4 | [33.2, 41.3] | 76.3% | 71.9% | 38.3% |
| Moirai 2.0 | 37.2 | [33.3, 41.0] | 77.8% | 74.3% | 37.0% |
| Toto | 34.5 | [30.0, 38.8] | 74.0% | 72.9% | 37.0% |
| TiRex | 33.7 | [29.7, 37.9] | 74.7% | 74.9% | 35.9% |
| Chronos-Bolt (base) | 33.0 | [28.8, 36.9] | 74.2% | 73.1% | 36.0% |
| TimesFM 2.5 | 32.0 | [27.4, 37.2] | 74.3% | 75.1% | 35.4% |
| Moirai-MoE | 31.2 | [26.4, 35.7] | 73.9% | 73.0% | 34.0% |
| Sundial | 31.0 | [26.9, 35.1] | 73.7% | 32.1% | 34.6% |
| AutoARIMA | 27.4 | [22.3, 31.8] | 68.2% | 71.6% | 34.7% |
| Granite TTM r2 | 26.3 | [22.4, 30.1] | 70.5% | — | 32.0% |
| AutoETS | 24.3 | [18.3, 29.3] | 65.5% | 74.9% | 33.3% |
| Naive | 8.5 | [−3.4, 18.2] | 52.4% | — | 25.4% |
| Seasonal naive | 0.0 | reference | 0.0% | — | 25.0% |
| Time-MoE | _not scored in v1_ | | | | |

### Week-ahead (168 h)

| Model | Skill % | 95% interval | Beats seasonal naive | Coverage (80%) |
|---|---|---|---|---|
| Moirai 2.0 | 24.2 | [21.4, 27.1] | 81.8% | 61.0% |
| Chronos-2 | 23.5 | [20.7, 26.5] | 81.4% | 72.6% |
| TimesFM 2.5 | 20.2 | [17.1, 23.5] | 77.1% | 72.9% |
| TiRex | 20.2 | [17.6, 22.6] | 77.7% | 75.4% |
| Toto | 19.4 | [16.6, 22.2] | 74.6% | 73.1% |
| Chronos-Bolt (base) | 19.3 | [16.8, 21.5] | 76.6% | 59.8% |
| Moirai-MoE | 18.1 | [14.7, 21.4] | 74.5% | 72.6% |
| Sundial | 18.1 | [15.5, 20.8] | 73.2% | 32.5% |
| Granite TTM r2 | 15.9 | [13.3, 18.3] | 74.4% | — |
| AutoARIMA | 12.7 | [9.1, 16.3] | 67.9% | 79.0% |
| AutoETS | 9.1 | [4.5, 13.6] | 63.2% | 86.3% |
| Seasonal naive | 0.0 | reference | 0.0% | — |
| Time-MoE | _not scored in v1_ | | | |

No model in this release is marked "released during window":
release dates were re-checked against the first public
weights in November 2026, and Moirai 2.0's weights — first
dated by its November 2025 paper — were public on Hugging
Face on 2025-08-06, before the window (DEVIATIONS.md). The operator forecast exists for the day-ahead horizon
only; it failed to cover 5 windows, which took the reference
score under the failure rule. Granite TTM r2 and the naive
baselines publish no intervals, so they have no coverage score.
Time-MoE is listed without a score in v1 (DECISIONS.md #45):
its Kaggle run degenerated to a constant forecast under the
transformers version available there, the pinned environment
cannot be reproduced on Kaggle, and the local CPU re-run was
stopped at 2 of 49 series; its two completed series parts are
kept for a possible later release.

The interactive leaderboard — sortable, with a
per-balancing-authority view — is generated from these score
files by `scripts/build_site.py` into `docs/`.

## How to read the scores

- **Skill %** — how much lower a method's error is than
  seasonal naive (the demand at the same hour last week),
  combined across all authorities and issue days. 0% means no
  better than that simple guess; negative means worse.
- **95% interval** — the range the skill plausibly falls in,
  from a paired bootstrap (B = 1000) resampling authorities and
  blocks of 4 issue days. Whether one method beats another is
  judged on **paired differences** (`results/scores/paired.csv`;
  the leaderboard page shows them under "Which differences are
  real"): "beats" only where the paired interval excludes 0,
  otherwise the two are level. On that rule the top group at
  both horizons is Chronos-2 and Moirai 2.0 together, and the
  operator forecast beats every method.
- **Beats seasonal naive** — the share of individual windows
  in which the method's error was lower than seasonal naive's.
  (fev-bench's "win rate" is a different quantity — the average
  win rate against all other models; it is in the score files
  as `avg_win_rate`.)
- **Coverage (80%)** — how often the actual demand fell inside
  the method's own 80% interval. Near 80% means the intervals
  are honest; much lower means overconfident. Sundial's
  intervals are the empirical ranges of 20 generated samples,
  exactly as the model ships them; its low coverage was
  checked against the model's own quick-start code and is a
  property of the model, not of this harness.
- **Beats operator** — the share of days on which the method's
  day-ahead error was lower than the operator's own published
  day-ahead forecast (paired over the days the operator forecast
  covers in full).
- Per-window detail (MASE, scaled quantile loss, peak-hour
  error) is in `results/scores/`; the scoring follows fev-bench
  (Shchur et al. 2025) wherever it applies.

## Protocol, in brief

The full protocol is fixed in `PLAN.md`, before any model was
scored; `MODELS.md` records each model's checkpoint, licence,
release date and training-data notes; `DATA_SOURCES.md` records
the data and its licences.

- **Series.** Every US balancing authority with continuous
  hourly reporting since 2019-01-01 and under 5% missing or
  flagged hours: 49 series. Exclusions and reasons are in
  `SCREEN.md`.
- **Cleaning.** Model inputs replace a flagged, missing or
  non-positive hour with the value 168 hours earlier, looking
  backwards only. Scoring uses reported, unflagged values only.
- **Context.** 2,048 hours for every model, or the model's
  maximum if smaller; the effective length actually passed is
  recorded per run.
- **Baselines.** Seasonal naive (the reference), naive,
  statsforecast AutoETS and AutoARIMA with MSTL seasonality at
  library defaults, and the operator's day-ahead forecast —
  all fixed before scoring, none tuned.
- **Failures.** A failed run takes the seasonal-naive score for
  that window and is flagged, as fev-bench does.
- **Contamination.** A model released after the window starts
  is marked "released during window" and excluded from the
  retrospective headline ranking. The live track ranks all
  models, because its data did not exist when they were
  trained.

## Limits

- One domain, one country: hourly demand for US balancing
  authorities. Rankings here say nothing about other series.
- One context length (2,048 h) and one issue time (15:00 UTC);
  both are operational choices, not optima.
- Zero-shot only, univariate: no covariates (weather is the
  obvious one), no fine-tuning, no ensembling.
- The operator comparison is a real-world bar, not a matched
  comparison. The operator forecast's own issue time is not
  published and may be later than this index's 15:00 UTC on
  the day before, so it may rest on fresher data. Operators
  forecast with weather forecasts and local knowledge; the
  foundation models here see only past load. And the
  retrospective track scores against revised history (the
  PUDL release), while the operator forecast was made in real
  time against the values then published. "Beats operator"
  therefore measures whether a model clears the operational
  bar, not which forecaster does better on equal terms.
- Retrospective scores for models released before the window
  can still reflect training-data overlap that model cards do
  not disclose; `MODELS.md` records what each card says. The
  live track is the contamination-proof part of the index.

## Related work

- **GIFT-Eval** (Aksu et al. 2024,
  [arXiv:2410.10393](https://arxiv.org/abs/2410.10393)) — a
  static, multi-domain benchmark: 23 datasets across 7 domains.
- **fev-bench** (Shchur et al. 2025,
  [arXiv:2509.26468](https://arxiv.org/abs/2509.26468)) — a
  static, multi-domain benchmark of 100 tasks across 7 domains,
  with the aggregation this index follows.
- **TIME** (Qiao et al. 2026,
  [arXiv:2602.12147](https://arxiv.org/abs/2602.12147)) — a
  static benchmark built from 50 fresh datasets to avoid
  leakage.
- **Impermanent** (Garza et al. 2026,
  [arXiv:2603.08707](https://arxiv.org/abs/2603.08707)) — a
  live benchmark, on GitHub activity series rather than energy.
- **Simeone (2026)**
  ([arXiv:2602.10848](https://arxiv.org/abs/2602.10848)),
  **Za'ter & Hodge (2026)**
  ([arXiv:2604.22077](https://arxiv.org/abs/2604.22077)) and
  **Meyer et al. (2024)**
  ([arXiv:2410.09487](https://arxiv.org/abs/2410.09487)) —
  one-off static energy studies: ERCOT load, the ERCOT PERFORM
  dataset, and household load respectively.

What this index adds: it is **live**, so contamination is
impossible by construction; it covers **one domain broadly** —
every qualifying US balancing authority, not a sample of series;
and it carries **the operator's own day-ahead forecast** as a
reference, the number a model would have to beat to be useful
in operations. (All references verified against arXiv on
2026-11-20.)

## Reproduce

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/extract_data.py      # pinned PUDL extraction
.venv/bin/python scripts/build_snapshots.py   # contexts and targets
.venv/bin/python scripts/run_baselines.py     # baseline forecasts
.venv/bin/python scripts/score_forecasts.py   # scores -> results/scores/
.venv/bin/python scripts/build_site.py        # leaderboard -> docs/
.venv/bin/python -m pytest tests/             # scorer, cleaning, no-look-ahead, contamination
```

The foundation models run one adapter per model
(`scripts/run_foundation.py --method <name>`), each in its own
environment; the Kaggle dataset and notebook (below) carry the
same inputs, forecasts and scores. A private Kaggle dataset,
`grid-load-index-data`, holds the run inputs, the pinned
snapshot, the forecasts and the scores (version 2), and a
private notebook, `grid-load-index-leaderboard-rebuild`,
rebuilds the leaderboard tables from it and checks them
against the shipped summary (DECISIONS.md #47).

**Adding a model** means adding one adapter file under
`src/adapters/` implementing
`forecast(context, target_index, quantiles) -> point, quantiles`,
recording the model in `MODELS.md`, and running the one command
above. The scorer is independent of electricity; nothing else
changes.

## Repository layout

- `PLAN.md`, `MODELS.md`, `SCREEN.md`, `DATA_SOURCES.md` — the
  fixed protocol, model record, series screen and data record.
- `DECISIONS.md`, `SPEND.md` — every decision taken under the
  brief's decision rules, and the compute ledger.
- `src/` — task spec, cleaning, snapshots, scoring,
  contamination flagging, the EIA API client, and one adapter
  per model in `src/adapters/`.
- `scripts/` — extraction, snapshot building, runners, scoring,
  the site builder, the live-track runner and the Kaggle
  dataset/notebook builders.
- `results/` — forecasts (with `MANIFEST.csv`) and scores.
- `docs/` — the generated leaderboard page and screenshots.
- `live/` — the live track's method map; its forecasts,
  snapshots and targets land here once the track is enabled.
- `tests/` — scorer checks against hand-computed cases, the
  cleaning rule, no-look-ahead, contamination flagging, and the
  EIA API path against a recorded-shape response fixture.

## Maintenance and retirement

The index is maintained by Omid Golchin. While the live track
runs, its output is checked weekly; a missed issue day is
recorded in the live manifest, not backfilled — a backfilled
forecast would break the track's one guarantee. Model versions
are pinned per release; a new checkpoint enters as a new entry,
never as a silent replacement. Releases are tagged by month
(`v2026.11`).

If maintenance stops, the repository and the leaderboard remain
as the final release, the live panel records the last issue
date, and the results stay reproducible from the pinned data
and the Kaggle dataset.

## Citation and licence

> Golchin, O. (2026). *Grid Load Forecasting Index* (release
> v2026.11). https://github.com/omidgolchin/grid-load-index

Code: MIT Licence (see `LICENSE`). Data: EIA Form 930 is
US-government public domain; the PUDL release that carries it
is CC-BY-4.0 (see `DATA_SOURCES.md`). Model checkpoints keep
their own licences, recorded in `MODELS.md`.

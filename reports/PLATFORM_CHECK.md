# Platform check (Step 0)

Access date for every source below: 2026-11-19.

## 1. Kaggle Benchmarks model catalog

The official Kaggle CLI (version 2.2.5, installed into a scratch
virtual environment) was authenticated with the account's KGAT API
token, passed through the `KAGGLE_API_TOKEN` environment variable.
The CLI could not use it: before running any command it validates the
token by calling the token-introspection endpoint on
`api.kaggle.com`, which returned HTTP 404 for this credential, so the
CLI discarded the token and reported that authentication is required.
`kaggle b t models` therefore cannot run as a CLI command with this
account's credential. (The credential is a surrogate that is
substituted on requests to `www.kaggle.com`; the introspection call
goes to a different host.)

The models command is backed by the Benchmarks API's
`ListBenchmarkModels` call on `www.kaggle.com`. Calling that endpoint
directly with the same credential returned the full catalog in one
page: **38 models**.

- Anthropic: claude-haiku-4-5, claude-haiku-5-5, claude-opus-4-5,
  claude-opus-4-6, claude-opus-4-7, claude-opus-4-8, claude-opus-5,
  claude-opus-5-5, claude-sonnet-4-6, claude-sonnet-5,
  claude-sonnet-5-5
- Google: gemini-3-flash-preview, gemini-3.1-flash-lite-preview,
  gemini-3.1-pro-preview, gemini-3.5-flash-lite, gemini-3.6-flash,
  gemini-3.8-flash, gemini-4-argon, gemini-4-neon, gemma-4-26b,
  gemma-4-31b-it
- OpenAI: gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5.5, gpt-5.6-luna,
  gpt-5.6-sol, gpt-5.6-terra, gpt-6-astra, gpt-6-luna, gpt-6-sol,
  gpt-6.1-sol, gpt-6.2-astra, gpt-6.2-sol, gpt-oss-120b
- xAI: grok-4.5, grok-4.6, grok-4.7

Every entry is a hosted large language model served through Kaggle's
model proxy. There are no non-LLM entries. The SDK docs and cookbook
name only a handful of these as examples and direct readers to the
models command for the full list; the subset exposed for local
development (`LLMS_AVAILABLE`) is smaller still.

Sources: Kaggle Benchmarks API (`ListBenchmarkModels`, accessed
2026-11-19); Kaggle CLI 2.2.5 and its benchmarks documentation
(github.com/Kaggle/kaggle-cli, `docs/benchmarks.md`).

## 2. What a benchmark task can evaluate

Checked in the kaggle-benchmarks SDK source and documentation
(github.com/Kaggle/kaggle-benchmarks: `user_guide.md`, `cookbook.md`,
`local_development.md`, `quick_start.md`, and
`src/kaggle_benchmarks/`).

- **Custom models: no.** `load_model()` in
  `src/kaggle_benchmarks/kaggle/models.py` always constructs a
  `ModelProxy` — an OpenAI-compatible client pointed at Kaggle's
  model proxy with a proxy API key — and every entry in `kbench.llms`
  is built the same way from the served-model catalog. No code path
  wraps a custom model class, a local Hugging Face model, or an
  arbitrary Python callable as an evaluable model.
  `local_development.md` states that local development is for
  Kaggle's internal team only and still requires a model proxy key.
  Leaderboard rows are model versions from server-side runs (CLI
  documentation, leaderboard section).
- **Float scores: yes.** Task results are typed `Result[float]`
  (`src/kaggle_benchmarks/results.py`); the user guide lists "int or
  float" as a numerical score.
- **(score, ci) tuples: yes.** The user guide's task return types
  document `tuple[float, float]` as "a metric with its confidence
  interval"; the `MetricWithCI` result class formats it as
  `value(±ci)`, and the guide states the return type determines how
  the result is rendered on the leaderboard.
- **Lower-is-better: no documented support.** The term and its
  equivalents appear nowhere in the user guide, cookbook, quick
  start, CLI documentation, or SDK source (searched 2026-11-19).
- **Per-user model quota:** model proxy usage is metered as a spend
  quota in USD, shown by `kaggle b quota` with one row per refill
  period. The CLI documentation's example shows totals of $5.00 per
  day and $100.00 per month. This is separate from the notebook
  GPU/TPU quota shown by the top-level `kaggle quota`.
- **Privacy:** a task stays private until `kaggle b t publish` is
  run. Publishing also publishes the backing notebook by default
  (`--no-publish-backing-notebook` opts out), and unpublishing is
  not supported (CLI documentation, publish section).

## 3. Existing forecasting or time-series benchmarks

Checked the Kaggle Benchmarks listing page (kaggle.com/benchmarks;
category sections shown: Featured, Community, Agentic, Coding,
Science), BenchLM.ai's mirror of the published boards (53 boards:
45 current and 8 archived, from 13 publishing organizations), and
web searches on forecasting, time-series, energy, and prediction
terms.

**None found.** As of 2026-11-19 there is no forecasting or
time-series benchmark on Kaggle Benchmarks. Every published board
evaluates language models on factuality, coding, document, game,
arena, or exam-style tasks. The closest prediction-flavoured board
is Human Behavior Bench (Rehearsals and Google DeepMind), which
scores how well models predict survey-response distributions for US
cohorts — 1,199 tasks, 11 models on the mirrored board — but it is
not a time-series benchmark and uses a single survey dataset.

Caveat: Kaggle exposes no public API for searching the benchmark
catalog; the check covered the site's own listing pages and a
complete third-party mirror of the published boards.

## 4. Decision

The project brief's rule: mirror the index on Kaggle Benchmarks only
if non-LLM models can appear on a Kaggle Benchmarks leaderboard;
otherwise the index lives on GitHub plus a Kaggle dataset and
notebook.

Section 2 settles the premise: non-LLM models cannot appear on a
Kaggle Benchmarks leaderboard.

**Outcome: the index lives on GitHub (harness, results, and the
leaderboard page), with a Kaggle dataset and a reproduction
notebook. Kaggle Benchmarks is used only for the optional Phase 2
LLM track.**

## 5. Data feasibility: PUDL EIA-930

Probe target: balancing-authority-level hourly EIA-930 demand and
the operator day-ahead demand forecast, in the PUDL stable release.

- **Table:** `out_eia930__hourly_operations`, PUDL stable release
  **v2026.11.0** (2026-11-10), public S3 bucket
  `pudl.catalyst.coop`. 6,297,866 rows. The reported-values twin is
  `core_eia930__hourly_operations`.
- **Columns:** `demand_reported_mwh`, `demand_adjusted_mwh`,
  `demand_imputed_pudl_mwh` with its imputation code,
  `demand_imputed_eia_mwh`, and `demand_forecast_mwh` (field
  description: "Day ahead demand forecast"). BA-level hourly demand
  and the operator day-ahead forecast are in the same table.
- **Coverage:** timestamps run 2015-07-01 05:00 UTC to 2026-11-01
  07:00 UTC. The stable release reaches past the backtest end of
  2026-10-31, so the nightly build is not needed.
- **Series count:** 70 BA codes appear in the full table; 61 have
  data in Nov 2025–Oct 2026 and 59 report in Oct 2026. In Oct 2026,
  52 BAs have at least 95% day-ahead-forecast coverage (the median
  BA is at 100%) and 53 BAs have complete PUDL-imputed demand. Six
  small BAs (AVRN, DEAA, GRID, GWA, SEPA, YAD) report no day-ahead
  forecast. A qualifying pool of roughly 50 BA series is available
  before the Step 1 screen — inside the expected 40–60 range.
- **Verdict: feasible.** BA-level hourly demand and the operator
  day-ahead forecast are obtainable from the PUDL stable release;
  the brief's stop condition 2 is not triggered. The fallback
  sources (EIA API v2, EIA-930 six-month bulk CSVs) are not needed.

Sources: PUDL EIA-930 documentation
(docs.catalyst.coop/pudl/en/stable/data_sources/eia930.html,
release 2026.11.0); direct read of the v2026.11.0
`out_eia930__hourly_operations.parquet` file, 2026-11-19. The same
bucket and stable release supplied the subregion demand table used
by the S04 load-forecasting project.

# Decisions

Choices made while building the index, each with its reason.
Numbering is permanent; later decisions are appended.

1. **Repo layout.** Documents at the repo root; stage scripts in
   `scripts/`; data under `data/` with manifests in
   `data/manifests/`. Keeps the plan, screen and model records one
   click from the README while code and data stay separate.
2. **Pinned source.** PUDL stable release v2026.11.0, not the
   nightly build. The stable release reaches 2026-11-01, past the
   coverage the retrospective window needs, and a pinned release
   cannot change under the results.
3. **"Flagged" operationalization.** An hour is flagged when
   PUDL's `demand_imputed_pudl_mwh_imputation_code` is non-null;
   missing when there is no row or the reported demand is null.
   This is the only flag the published table carries, and it marks
   exactly the hours PUDL replaced or questioned.
4. **Screen span and denominator.** The screen is computed over
   the full hourly grid 2019-01-01 00:00 UTC to 2026-11-01 07:00
   UTC (68,672 hours) for every BA, so a BA that started late or
   stopped early scores its absent hours as missing and fails the
   5% rule on the same basis as everyone else.
5. **BA timezone.** Each series uses PUDL's `report_timezone` for
   that BA from `core_eia__codes_balancing_authorities` — the
   timezone the BA reports in — rather than a geographic guess.
   This is what "the BA's own timezone" means for EIA-930 data.
6. **DST rule.** Local days are taken as they occur: 23-hour and
   25-hour transition days are forecast and scored hour for hour,
   with no dropped or duplicated hours. Normalising them away
   would change the target operators actually face.
7. **Last issue day.** Computed per series from the pinned file:
   the latest Monday whose full 168-hour target is covered for
   every qualifying series is 2026-10-19, giving 51 weekly issue
   days from 2025-11-03. A single common window keeps every
   model's scores paired on identical cells.
8. **Cleaning donor.** A bad hour takes the cleaned value 168
   hours earlier, stepping back weekly; using the cleaned series
   as the donor finds the same value as searching the reported
   series for the most recent usable hour on the weekly lattice,
   and cannot leak a flagged value into the inputs.
9. **Operator-forecast scoring.** The operator forecast is scored
   on the target hours where a forecast value exists, and a
   BA-day counts toward "beats operator" only when the operator
   forecast covers the full local day. Counting partial days would
   let missing operator hours choose the comparison.
10. **TabPFN-TS dropped.** Its current checkpoints are gated
    behind a licence-acceptance step and the licence grants
    internal evaluation only, not publication of results; see
    MODELS.md. Ten models remain, above the minimum of eight.
11. **Moirai 2.0 and Moirai-MoE kept under CC BY-NC 4.0.** The
    cards mark the releases research-only, and this index is a
    non-commercial research evaluation, which the licence allows;
    the licence is recorded in MODELS.md so the limit travels with
    the results.
12. **Moirai 2.0 flagged "released during window".** Its paper
    (arXiv:2511.11698) and release are November 2025, after the
    window start of 2025-11-03, so the contamination rule excludes
    it from the retrospective headline ranking while still scoring
    it.
13. **TiRex kept.** The NXAI Community License grants royalty-free
    research use (its commercial threshold does not bind a
    non-commercial evaluation), and the model runs on a T4 through
    its standard PyTorch path — its optional CUDA kernels need
    compute capability 8.0+, which the T4 (7.5) lacks; the adapter
    stage verifies this.
14. **Time-MoE checkpoint.** `Maple728/TimeMoE-50M`, the base
    benchmarked variant; the 200M variant would add GPU time
    without changing the comparison's design. Both optional MoE
    candidates (Moirai-MoE, Time-MoE) fit the rule and the size
    cap, so both are included.
15. **Data policy.** Large files stay out of git: the pinned
    source files and the extracted per-series parquets are
    gitignored; manifests with hashes are committed, and one
    command (`scripts/extract_data.py`, after
    `scripts/screen_series.py`) rebuilds the extraction from the
    pinned source.
16. **Git author.** Commits use the repository's configured author
    (Omid Golchin, noreply address), as the project brief
    requires; the configuration was verified, not changed.
17. **Project environment.** A repo-local virtual environment at
    `.venv` (gitignored) with pandas and pyarrow for the data
    stage; model adapters get their own environments on Kaggle at
    run stage, so no model's dependencies can break another's.
18. **Cycle-baseline donor rule.** The naive baselines take, for
    each target hour, the context value at the most recent hour
    with the same cycle phase at or before the snapshot cutoff —
    stepping back by whole periods (168 h / 24 h) until the donor
    is inside the context. A literal one-period step back would
    use hours published after the cutoff for the last hours of a
    span, because the target starts the next local day, hours
    after the 13:00 UTC cutoff.
19. **Snapshot storage.** Contexts are stored once per
    (series, issue day), shared by both horizons, in
    `data/snapshots/snapshots.parquet`; targets (timestamps,
    local-day labels, reported values, scored mask, operator
    values) in `targets.parquet`. Both are gitignored; counts
    and hashes are committed in
    `data/manifests/snapshot_manifest.csv`.
20. **Statistical-baseline configuration.** statsforecast's MSTL
    requires a non-seasonal trend forecaster, so the AutoETS
    variant uses MSTL's own default trend forecaster
    (AutoETS, model 'ZZN') and the AutoARIMA variant uses
    AutoARIMA() at its defaults (its season_length is 1 inside
    MSTL, as the library requires). One fit per (series, issue
    day) forecasts the whole week span; the day-ahead result is
    its first local day. Levels [20, 40, 60, 80] give quantiles
    0.1–0.9, and the point forecast is recorded as the 0.5
    quantile.
21. **statsforecast pinned at 2.1.1** in the repo environment
    and in requirements.txt, and recorded in the forecast
    manifest with the results.
22. **Release-date precision in the contamination registry.**
    Release dates are kept at the precision MODELS.md publishes
    (exact day or month). A month-precision release in a month
    after the window-start month is during the window, in an
    earlier month it is not, and in the window-start month the
    determination recorded in MODELS.md applies (Moirai 2.0:
    flagged, per #12).
23. **Bootstrap statistic.** The paired bootstrap recomputes the
    skill score (or the paired skill difference) on each
    resample from window weights: a window's weight is its
    series draw count times its issue-day draw count, with issue
    days drawn as blocks of 4 consecutive days. B = 1000,
    percentile interval.
24. **Non-finite context values.** A context hour that is still
    missing after cleaning makes the cycle baselines step back
    to the nearest finite donor on the same lattice; a
    statistical adapter fails that window instead of fitting on
    invented values, and the failure rule applies at scoring.
    (In the built snapshots, no context contains such an hour.)
25. **Windows with no scored hours.** A window whose target
    hours are all missing or flagged in the source (7 of 4,998
    windows: SCEG once, SWPP six times) has no score for any
    method, so it is excluded from every method's aggregation
    as a data gap — it is not a method failure and does not
    take the reference score. An operator window with no
    forecast value at any scored hour is a failed window and
    does take the reference score (5 such windows).
26. **Point forecast from quantile models.** Where a model
    provides quantiles, the recorded point forecast is the
    predictive median (the 0.5 quantile), the same convention
    the baselines use (their point is recorded as q0.5).
    Point-only models contribute their point output and take
    part in point metrics only (PLAN.md).
27. **Quantile ordering.** Adapters sort the quantile levels
    at each timestep so the recorded quantiles never cross;
    sample-based models' empirical quantiles are ordered by
    construction, and TimesFM uses its own crossing fix.
28. **TiRex effective context is 2,016 hours.** The tirex-ts
    library truncates the context to the checkpoint
    configuration's maximum (2,016), not the index's 2,048.
    The truncated length is what the run records as the
    effective context (verified in the adapter smoke test).
29. **TTM week horizon by block extension.** Granite TTM r2
    has a 512-hour context and a 96-hour prediction head, so
    it cannot emit a 167–169-hour week in one call. The
    adapter forecasts hours 1–96 from the snapshot context,
    then the remaining hours from a context extended with the
    model's own first-block median path; week samples are the
    first block's samples concatenated with second-block
    samples drawn on the extended context, so second-block
    uncertainty is conditioned on the median path (a
    documented approximation). No post-cutoff information is
    used. The rejected alternative was failing every TTM week
    window.
30. **Moirai-MoE patch size 16.** The small checkpoint
    supports a single patch size (16); the forecast module
    does not resolve "auto" for it, so the adapter passes 16
    explicitly.
31. **Kaggle environment for the Moirai models.** The kernel
    image runs Python 3.13, for which uni2ts 2.0.0's pinned
    numpy (~1.26) and scipy (~1.11) have no wheels, and
    gluonts 0.14's pandas cap (<2.2) cannot build either. The
    kernels therefore install uni2ts --no-deps, gluonts
    0.14.4 --no-deps, and the remaining runtime dependencies
    at current versions. gluonts is held at 0.14.4 because
    0.16+'s quantile forecast generator expects
    distribution-style network outputs and fails on Moirai
    2's forecasts (probe-verified both ways).
32. **Toto through the toto-ts 0.2 API.** The checkpoint
    loads as Toto.from_pretrained(...).model (the backbone);
    forecasts take a MaskedTimeseries and return sample-based
    quantiles from 256 samples in batches of 32 (the library
    requires the sample count divisible by the batch size and
    recommends at least 128 samples).
33. **Run dataset contents.** The private Kaggle dataset
    (omidgolchin/grid-load-index-data) carries the snapshot
    contexts, snapshot ids and target timestamps only — no
    reported values: model runs see contexts, and scoring
    happens locally against the held actuals.
34. **Time-MoE environment.** The model's code targets
    transformers 4.40.1, whose tokenizers pin (>=0.19,<0.20)
    has no wheels for the kernel image's Python 3.13 and
    which rejects newer tokenizers at import. The kernel
    therefore uses transformers 4.47.1, and the adapter
    carries a small compatibility wrapper: it restores the
    standardize_cache_format keyword the model's generation
    mixin passes (removed in transformers 4.43), returning
    the model's own legacy-format cache unstandardised, as
    the 4.40-era mixin did. The wrapper is a no-op where the
    keyword still exists (verified locally against 4.40.1;
    probe-verified on 4.47.1).
35. **Sundial runs locally on CPU.** Sundial's generation
    mixin targets transformers 4.40: it overrides
    _greedy_search, which transformers >= 4.43 no longer
    dispatches to (greedy decoding moved into _sample), and
    its cache code uses DynamicCache.seen_tokens, removed in
    4.47. The 4.40-era tokenizers pin has no wheels for the
    Kaggle image's Python 3.13, so Sundial cannot run in a
    kernel. It runs locally on CPU in a transformers 4.40.1
    environment instead (~3.4 s per snapshot on real data,
    ~2.4 h for the full run), at no GPU cost — the same
    treatment the brief gives the other CPU-feasible model
    (TTM).
36. **Target-span alignment (adapter contract).** The
    target span starts after the snapshot cutoff — the
    day-ahead span is the next local day, 15–21 hours after
    the context end depending on the balancing authority.
    An adapter must therefore generate forward from the
    context end through the last target hour and keep only
    the target hours (base.target_steps), as the statistical
    adapters do. The first foundation adapters generated only
    the span's length from the context end, which shifted
    every forecast by the gap; scoring the first two full
    runs exposed it (skill about -115% and -123% against
    seasonal naive, where the baselines score sanely). All
    ten adapters were corrected to generate through the last
    target hour and slice; the affected full runs (Moirai
    2.0, Chronos-2 completed; Moirai-MoE and TiRex in flight)
    are discarded and re-run.
37. **Toto environment and inputs.** toto-ts 0.2.0 pins
    torch 2.7.0, which orphans the kernel image's torchvision
    (its nms operator disappears); the kernel therefore also
    installs torchvision 0.22.0, the release paired with
    torch 2.7.0. Separately, the adapter originally passed a
    scalar id_mask; the library expects the mask to span the
    full time axis (its own build_id_mask makes a
    [variates, time_steps] tensor), and with the scalar the
    model's patch embedding received an empty axis and every
    window failed. The adapter now passes a zero mask over
    the whole context, verified on a real snapshot locally
    before re-probing.
38. **TTM provides no quantiles.** The r2 checkpoint's
    configuration names a Student-t distribution output, but
    it also sets the training loss to mse, and granite-tsfm
    builds the distribution head only for an nll loss; the
    checkpoint carries no distribution-head weights. An
    earlier merged run took quantiles from the point output
    and so recorded degenerate intervals (q0.1 = q0.9
    everywhere, coverage 0); it was discarded. The adapter
    now returns the point forecast only, and the scorer
    treats TTM like the other point-only methods. This
    corrects the sampling assumption recorded with #29; the
    block-extension mechanics of #29 are unchanged.
39. **Time-MoE runs locally on CPU.** The Kaggle kernel ran
    transformers 4.47.1 with the adapter's cache-format
    patch (DECISIONS #34); under that patch the model's
    generation degenerated to a constant value for every
    step (skill about -74% against seasonal naive, where
    every other model scores between +17% and +37%), while
    the same adapter under the model's pinned transformers
    4.40.1 produces a normal varying forecast. That Kaggle
    run was discarded. A corrected Kaggle re-run would take
    the week's total past the 20 GPU-hour cap, so Time-MoE
    runs locally on CPU in the pinned 4.40.1 environment,
    like Sundial and TTM: about 21 s per snapshot, roughly
    15 hours for the full set, checkpointed per series.
40. **Leaderboard page build.** The page is generated by
    `scripts/build_site.py` from the score files
    (results/scores/summary.csv + window_scores.parquet) into
    docs/index.html, with the template in site/ and the kit
    stylesheets vendored alongside it. One command rebuilds the
    page, so the final pass after the last model lands is a
    re-run, not an edit. A registered model with no scores yet
    (Time-MoE, still running) appears as a "run in progress"
    row rather than being silently absent. The MASE column and
    the per-BA view are aggregated from the per-window scores,
    which carry the failure rule already applied. The kit
    header's kicker reads "forecasting benchmarks" rather than
    the tools' "learning tools": this page is a benchmark, and
    the kicker names the series the page belongs to. The kit
    footer's sibling-tool links are dropped while the index is
    private.
41. **Live track: method set, environments, disabled form.**
    The live method set is the CPU-feasible one: seasonal
    naive, naive, AutoETS, AutoARIMA, Granite TTM and Sundial.
    The GPU foundation models are not in it — a GitHub Actions
    CPU runner cannot run them; adding them later through a
    GPU path does not change the track's rules. Each method
    runs in the environment its retrospective run used (the
    statistical baselines in the harness venv, TTM in
    .venv-ttm, Sundial in .venv-sundial2 at transformers
    4.40.1), because the environments pin incompatible
    libraries; scripts/live_forecast.py therefore runs each
    method as a worker subprocess with the interpreter named
    in live/methods.json, and the Actions workflow builds the
    same three environments from requirements.txt,
    requirements-live-ttm.txt and requirements-live-sundial.txt.
    The workflow (.github/workflows/live-track.yml) is
    committed disabled in the brief's default form: no schedule
    trigger (the cron line is present but commented), manual
    dispatch only, and it also cannot run usefully until the
    EIA_API_KEY secret exists. The runner stores, per issue
    day, the forecasts, the cleaned context snapshot each
    forecast was made from, and the target hours with the
    operator forecast as published at issue time. The EIA API
    path (src/eia_api.py) is tested against a response fixture
    written to the API v2 documentation's schema
    (tests/fixtures/eia_region_data_response.json); no key
    exists yet, so when the key is added the fixture should be
    re-recorded from the live API and the tests re-run.
    Observed cost: the AutoARIMA worker is the slow part
    (MSTL fits are serial, as in the retrospective runner's
    per-part work); a full issue day takes on the order of an
    hour of CPU across methods, inside a daily Actions budget,
    and the worker can be pooled later without changing any
    output if minutes become a problem.
42. **Phase 2 (LLM track on Kaggle Benchmarks): no-go for v1.**
    The brief allows Phase 2 only if Phase 1 is complete and
    Step 0 allows it. Neither holds yet. Phase 1 is not
    complete: Time-MoE's run is still in progress and the
    final scoring pass and hand-back are outstanding. And
    Step 0 recorded that Kaggle Benchmarks meters model use
    as a per-user USD spend quota (documentation example:
    $5/day, $100/month) with no verified free allowance; the
    project's spend rule is $0, and whether that quota is an
    included allowance or a charge is unverified — under the
    decision rules, unverified spend is treated as spend.
    A third, practical obstacle: the official Kaggle CLI
    cannot authenticate with the connector's API token
    (Step 0), so creating and running a task would depend on
    undocumented API paths. Revisit after the v1 hand-back if
    wanted; the unblocks are a verified no-charge quota and a
    working CLI or supported API path for task management.
43. **README references verified before citation.** Every
    related-work reference the brief names was checked against
    arXiv on 2026-11-20 before being cited in the README:
    GIFT-Eval (Aksu et al., arXiv:2410.10393, static,
    multi-domain), fev-bench (Shchur et al., arXiv:2509.26468,
    static, multi-domain; this index follows its scoring),
    TIME (Qiao et al., arXiv:2602.12147, static, fresh
    datasets), Impermanent (Garza et al., arXiv:2603.08707,
    live, on GitHub activity), Simeone 2026
    (arXiv:2602.10848, ERCOT load, one-off), Za'ter & Hodge
    2026 (arXiv:2604.22077, ERCOT PERFORM, one-off) and Meyer
    et al. 2024 (arXiv:2410.09487, household load, one-off).
    Titles, authors and the one-line characterisations in the
    README's related-work section are as the arXiv records
    give them.
44. **Step 8 record and live dry run — completion notes.**
    The Kaggle dataset's Step 8 version is staged
    (scripts/kaggle_dataset_step8.py: 23 files, 355 MB — the
    run inputs, the pinned retrospective snapshot, all 14
    methods' forecasts, both score files and the manifests)
    but its upload is blocked by the environment, not by the
    dataset: PUT requests to Kaggle's signed storage URLs
    through this machine's egress proxy currently never
    complete (a 100 KB test PUT timed out at 100 s; the upload
    attempts time out at 600 s), while API reads and posts to
    www.kaggle.com work and the version 1 upload succeeded on
    2026-11-19. The dataset therefore still stands at version
    1, verified private (isPrivate = true, read back
    2026-11-20). The upload is one resumable command
    (scripts/kaggle_dataset_step8.py; per-file state in
    data/kaggle_dataset/step8/upload_state.json) and the
    rebuild notebook (scripts/build_notebook.py) is built and
    verified locally — its aggregation reproduces
    scores_summary.csv on all 26 method-horizon rows — but it
    is pushed only after the dataset version lands, so its
    first run runs against the data it documents. The live
    dry run (issue day Monday 2026-10-26, PUDL source) completed
    end to end: 49/49 series usable, all six live methods
    produced forecasts (9,451 rows each for the two-horizon
    methods — the fall-back week's 25-hour days included —
    1,176 for day-only naive), with the context snapshot and
    operator-at-issue targets stored under live/dryrun/. It ran
    in passes under heavy CPU contention with the Time-MoE run:
    the first Sundial worker accumulated several times its
    retrospective CPU per window because the numerical
    libraries spin-wait on a thread per core, so workers now
    run with the thread count capped at 2 (OMP/MKL/OpenBLAS),
    and the runner now also restricts naive to the day-ahead
    horizon, matching the retrospective method horizons.
45. **Time-MoE unscored in v1; v1 ships with nine models.**
    Time-MoE carries no score in release v2026.11. Its Kaggle
    run degenerated to a constant forecast under the
    transformers version available there (DECISIONS #39), and
    the pinned transformers 4.40.1 environment the adapter
    needs cannot be reproduced on Kaggle (DECISIONS #34).
    The local CPU re-run in that pinned environment stalled
    at 2 of 49 series after repeated silent deaths and two
    machine reboots on 2026-11-20, with a projected 28–44
    hours remaining at the observed pace. On 2026-11-20 the
    decision was taken to ship v1 with the nine scored
    foundation models and to mark Time-MoE unscored, with
    the reason stated wherever its row appears. Its two
    completed series parts (AECI and AVA, in
    results/forecasts/parts/) are kept, so the model can be
    added in a later release without repeating them.
46. **Step 8 retry (2026-11-20): partial progress, then
    stopped.** The resumable upload was re-run for the final
    pass. Four of the 23 staged blobs uploaded and their
    tokens were saved (snapshots.parquet, targets_lite.parquet,
    eval_series.parquet, autoarima.parquet — the last a 41 MB
    file, so the storage path itself works). The run then
    stalled on the fifth file: its storage PUT awaits a user
    permission approval for the storage host, which only the
    account holder can grant. The attempt was stopped rather
    than looped. The dataset therefore still stands at
    version 1 (isPrivate = true, re-verified by API read
    after the retry; 4,096,665 bytes), and the rebuild
    notebook remains unpushed, as it is pushed only after the
    dataset version lands. One resumable command finishes
    Step 8 once the approval is granted:
    scripts/kaggle_dataset_step8.py, with per-file state in
    data/kaggle_dataset/step8/upload_state.json.
47. **Step 8 completed (2026-11-20).** The storage-host
    permission was approved by the account holder and the
    resumable upload was re-run to completion: the remaining
    19 blobs uploaded and the dataset version posted. The
    dataset `omidgolchin/grid-load-index-data` now stands at
    version 2 (354,729,055 bytes; isPrivate = true, verified
    by API read after posting). The rebuild notebook was
    then pushed; Kaggle derived its slug from its title, so
    it stands as `omidgolchin/grid-load-index-leaderboard-rebuild`.
    Its pulled-back metadata records isPrivate = true, and
    its first run completed with no failure message. Step 8
    is complete; #44 and #46 record the earlier blocked
    states.
48. **Release dates re-based on first public weights
    (2026-11-20 review round).** The date of record for every
    model is now the first public weights — the checkpoint's
    Hugging Face repository creation / first commit, accessed
    2026-11-20 — not the paper date. Moirai 2.0's weights were
    public on 2025-08-06 (announced 2025-08-08); the November
    2025 date used at first is its arXiv paper (2511.11698),
    so its released-during-window flag is removed and it
    enters the headline ranking. This supersedes the date
    basis of #12; the flag rule itself is unchanged. The
    other dates corrected to the same basis: Chronos-Bolt
    2024-11-25, Chronos-2 2025-10-30, TimesFM 2.5 2025-09-02
    (was 2025-09-15), TiRex 2025-05-26 (was June 2025), Toto
    2025-04-30 (was May 2025), Sundial 2025-05-13 (was
    February 2025, its paper), Granite TTM r2 2024-10-08 (was
    January 2025, the r2 revision), Moirai-MoE 2024-11-01
    (was October 2024), Time-MoE 2024-09-21 (was October
    2024). No other model's flag changes: with the corrected
    dates, no v1 model was released during the window. The
    change is post-scoring, so DEVIATIONS.md entry 1 reports
    both headline versions.
49. **Paired differences for every comparative claim
    (2026-11-20 review round).** `scripts/paired_diffs.py`
    computes paired skill differences on the same bootstrap
    resamples (`bootstrap_skill_diff_ci`) and writes
    `results/scores/paired.csv`: each method against the
    top-scoring foundation model of the horizon, each
    foundation model against AutoARIMA, and each method
    against the operator forecast (day-ahead only, on the
    2,489 windows the operator covers). "Beats" is claimed
    only where the paired interval excludes 0; otherwise the
    methods are level. Applied in README.md, reports/REPORT_INDEX.md
    and the leaderboard page, which gains a "Which
    differences are real" view. Outcome: the top group at
    both horizons is Chronos-2 and Moirai 2.0 together
    (day −0.2 points [−2.2, +1.9]; week −0.6 [−2.9, +1.2]);
    the operator beats every method paired.
50. **"Win rate" renamed; fev-bench average win rate added
    (2026-11-20 review round).** The column that counted
    windows beating seasonal naive is `beats_snaive` in
    summary.csv, the page and the rebuild notebook (the old
    name collided with fev-bench's term). fev-bench's win
    rate — for each other method, the share of windows with
    the lower MASE, averaged over methods — is computed in
    `scripts/score_forecasts.py` and shipped as `avg_win_rate`.
51. **Sundial interval check (2026-11-20 review round).**
    `scripts/check_sundial_intervals.py` runs the model's
    official quick-start generate call next to the adapter on
    identical contexts (3 windows, week horizon, same seed,
    the transformers 4.40.1 environment of #35). The
    adapter's quantiles were identical to the quick-start's
    at q0.1, q0.5 and q0.9 (max difference 0.0000 MW on all
    three windows); the stored run's interval widths sit
    within sampling variation of a fresh draw (mean width
    ratios 1.02, 1.11, 1.20). The adapter is a faithful
    wrapper; coverage 0.32 stands, and Sundial's intervals
    are recorded as the empirical ranges of 20 samples, as
    shipped. No adapter change, no re-run.
52. **Granite TTM scored at its 1,536-hour revision
    (2026-11-20 review round).** The v1 run used the
    checkpoint's 512-hour default revision; TTM r2 also
    publishes 1,024- and 1,536-hour revisions, and the
    brief's context rule (2,048 hours or the model's
    maximum) points at the longest. The 1,536 revision
    (`1536-96-r2`) was re-run on local CPU: 450 s, 4,998
    windows, 0 failed, effective context 1,536 recorded on
    every call; state in `results/ttm1536_state.md`. Scores:
    512-hour — day +25.1, week +17.0; 1,536-hour — day +26.3,
    week +15.9. The 1,536-hour version is the scored one;
    both are reported in DEVIATIONS.md entry 2 and the
    512-hour forecasts are archived at
    `results/forecasts/parts/ttm_ctx512_archive.parquet`.
53. **Alignment tests added (2026-11-20 review round).**
    `tests/test_alignment.py` pins the #36 defect class: unit
    tests for `target_steps` (a context ending 13:00 UTC;
    next-local-day targets in America/New_York and
    Australia/Sydney; the 25-hour fall-back day and the
    23-hour spring-forward day) and a stub-adapter test whose
    model returns its step numbers, checking the sliced
    output matches the target hours. Full suite: 46 passed
    (was 39).
54. **Credential-helper location read from the environment
    (2026-11-20 review round).** `scripts/kaggle_dataset.py`
    no longer hard-codes the build environment's helper
    directory; it reads `CREDENTIAL_HELPER_DIR` and stops
    with instructions when it is unset. Also: `.venv-chronos` (519 files) was tracked in git
    despite being listed in .gitignore; it is untracked, the
    files stay on disk.
55. **Kaggle dataset refreshed to version 3 (2026-11-20,
    on approval).** The refresh proposed in
    reports/REPORT_INDEX_2.md was carried out the same day.
    `scripts/kaggle_dataset_step8.py` was extended
    minimally: it also stages `results/scores/paired.csv`
    (as scores_paired.csv), its version notes describe the
    refresh, and its blob state moved to
    upload_state_v3.json — the version 2 state was preserved
    as upload_state_v2.json, so every file uploaded anew and
    no version 2 blob token was reused. Before uploading,
    each staged file was hash-checked against its repo
    source (all direct copies matched; the staged
    ttm.parquet is the merged 1,536-hour file, not the
    archived 512-hour one). Dataset
    `omidgolchin/grid-load-index-data` now stands at
    version 3: 354,734,093 bytes (version 2: 354,729,055),
    isPrivate = true verified by API read after posting.
    Changed versus version 2: scores_summary.csv
    (beats_snaive, avg_win_rate), scores_paired.csv (new),
    window_scores.parquet (regenerated) and ttm.parquet
    (1,536-hour forecasts); the other 20 files are
    byte-identical content, re-uploaded. The rebuild
    notebook was re-pushed: Kaggle had derived its slug
    from the title at creation, so the metadata id in
    `scripts/build_notebook.py` now names the live kernel,
    `omidgolchin/grid-load-index-leaderboard-rebuild` (the
    first push attempt with the old id was refused with a
    title conflict and created nothing). The account holds
    exactly one rebuild kernel; it is at version 2,
    isPrivate = true on pull-back, and its run completed
    with no failure message — its built-in check therefore
    passed against the version 3 files. Spend: $0.

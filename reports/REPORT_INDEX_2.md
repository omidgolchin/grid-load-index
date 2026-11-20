# Grid Load Forecasting Index — review-round hand-back

Round: the 2026-11-20 review of the v1 build, items 1–8,
applied in full on
2026-11-20. Everything stayed private: no pushes, no Kaggle
uploads, $0 spent, Kaggle GPU 0 h in this round. Decisions
taken are DECISIONS #48–#54; post-scoring changes are logged
in the new `DEVIATIONS.md`. REPORT_INDEX.md, README.md and
the leaderboard page now carry the corrected numbers and
wording throughout.

## Item 1 — Moirai 2.0 release date (claim-changing)

Moirai 2.0's weights were public on Hugging Face on
**2025-08-06** ("initial commit" and "Push model using
huggingface_hub" in the `Salesforce/moirai-2.0-R-small`
commit history; Salesforce announced the model 2025-08-08).
The November 2025 date the v1 build used is the arXiv paper
(2511.11698). The flag is removed; Moirai 2.0 enters the
headline ranking. Every model's date was re-checked on the
same basis — first public weights, Hugging Face repository
creation / commit history, accessed 2026-11-20:

| Model | Date used before | Corrected date | Source |
|---|---|---|---|
| Chronos-Bolt (base) | Dec 2024 | 2024-11-25 | HF repository created |
| Chronos-2 | Oct 2025 | 2025-10-30 | HF repository created |
| TimesFM 2.5 | 2025-09-15 | 2025-09-02 | HF repository created (the September 15 date was the release notes) |
| Moirai 2.0 | Nov 2025 | **2025-08-06** | HF commit history; announcement 2025-08-08 |
| TiRex | Jun 2025 | 2025-05-26 | HF repository created |
| Toto | May 2025 | 2025-04-30 | HF repository created |
| Sundial | Feb 2025 | 2025-05-13 | HF repository created (February 2025 was the paper) |
| Granite TTM r2 | Jan 2025 | 2024-10-08 | HF repository created (January 2025 was the r2 revision) |
| Moirai-MoE | Oct 2024 | 2024-11-01 | HF repository created |
| Time-MoE | Oct 2024 | 2024-09-21 | HF repository created |

Only Moirai 2.0's flag changes: with the corrected dates,
**no v1 model was released during the window**. MODELS.md,
the contamination registry (`src/contamination.py`) and its
tests carry the new dates. DEVIATIONS.md entry 1 reports
both headline versions: flagged — eligible leaders Chronos-2
at both horizons (day +37.4, week +23.5), Moirai 2.0 shown at
+37.2 / +24.2; unflagged — Moirai 2.0 ranked, in the top
group at both horizons (item 2).

## Item 2 — Paired intervals (claim-changing)

`scripts/paired_diffs.py` computes paired skill differences
on the same bootstrap resamples (`bootstrap_skill_diff_ci`,
B = 1000) and writes `results/scores/paired.csv` (53 rows):
(a) every method against the top-scoring foundation model of
the horizon — Chronos-2 day-ahead, Moirai 2.0 week-ahead,
recomputed after item 1; (b) every foundation model against
AutoARIMA; (c) every method against the operator forecast,
day-ahead only, on the 2,489 windows the operator covers.
The leaderboard page gained a "Which differences are real"
view presenting all three families per horizon.

Headline outcomes — **the single-leader claims did not
survive; both horizons have a top group of two:**

Day-ahead, against the top model (Chronos-2):

| Method | Difference | 95% interval | Reading |
|---|---|---|---|
| Operator forecast | +14.0 | [+1.7, +23.3] | operator beats Chronos-2 |
| Moirai 2.0 | −0.2 | [−2.2, +1.9] | **level** |
| Toto | −2.8 | [−5.1, −0.8] | Chronos-2 beats |
| TiRex | −3.6 | [−6.1, −1.5] | Chronos-2 beats |
| Chronos-Bolt | −4.3 | [−6.3, −2.5] | Chronos-2 beats |
| TimesFM 2.5 | −5.3 | [−7.9, −2.5] | Chronos-2 beats |
| Moirai-MoE | −6.2 | [−8.1, −4.6] | Chronos-2 beats |
| Sundial | −6.3 | [−9.4, −3.6] | Chronos-2 beats |
| AutoARIMA | −9.9 | [−13.3, −7.0] | Chronos-2 beats |
| Granite TTM | −11.1 | [−14.1, −8.5] | Chronos-2 beats |
| AutoETS | −13.1 | [−17.1, −9.3] | Chronos-2 beats |
| Naive | −28.8 | [−37.7, −21.5] | Chronos-2 beats |

Week-ahead, against the top model (Moirai 2.0): Chronos-2 is
level (−0.6 [−2.9, +1.2]); Moirai 2.0 beats every other
method (TimesFM 2.5 −4.0 [−5.9, −2.1] down to AutoETS −15.1
[−20.2, −10.7]).

Against AutoARIMA: day-ahead, seven foundation models beat
it (Chronos-2 +9.9 [+7.0, +13.3], Moirai 2.0 +9.8, Toto +7.1,
TiRex +6.3, Chronos-Bolt +5.6, TimesFM 2.5 +4.6, Moirai-MoE
+3.7); **Sundial (+3.6 [−0.8, +8.3]) and Granite TTM (−1.2
[−5.3, +2.5]) are level with it**. Week-ahead, all nine beat
it (Granite TTM smallest at +3.2 [+0.2, +6.4]).

Against the operator (day-ahead, operator's windows): **the
operator beats every method** — the closest are Chronos-2
(−14.1 [−23.4, −1.7]) and Moirai 2.0 (−14.3 [−23.5, −1.9]);
the widest is seasonal naive (−51.4). The v1 claim "no
foundation model beats the operator forecast" survives and
is now paired-tested.

Rewritten comparative sentences (quoted from the updated
documents):

- REPORT_INDEX.md: "No foundation model beats the operator
  forecast. Paired on the 2,489 windows the operator covers,
  the operator beats every method — the closest, Chronos-2,
  by 14.1 points with an interval of [−23.4, −1.7] — and the
  highest beats-operator share for any model is Chronos-2's
  38.3%."
- REPORT_INDEX.md: "At the top of the model ranking,
  Chronos-2 and Moirai 2.0 cannot be told apart day-ahead
  (paired difference −0.2 points [−2.2, +1.9]); Chronos-2
  beats every other foundation model paired."
- REPORT_INDEX.md: "Week-ahead, Moirai 2.0 and Chronos-2
  likewise form the top group (paired difference −0.6 points
  [−2.9, +1.2]); Moirai 2.0 beats every other method paired.
  Against AutoARIMA, all nine foundation models win
  week-ahead; day-ahead, seven win and Sundial and Granite
  TTM are level with it."
- REPORT_INDEX.md: "Released-during-window flags: none."
- README.md: "Whether one method beats another is judged on
  paired differences … 'beats' only where the paired
  interval excludes 0, otherwise the two are level. On that
  rule the top group at both horizons is Chronos-2 and
  Moirai 2.0 together, and the operator forecast beats every
  method."
- Leaderboard page: "A difference counts as real only where
  its interval excludes 0; otherwise the two cannot be told
  apart." The page's "How to read this" no longer suggests
  comparing the marginal intervals.

## Item 3 — "Win rate" renamed

The column is now **"Beats seasonal naive"** (`beats_snaive`
in `results/scores/summary.csv`), renamed in REPORT_INDEX.md,
README.md, the page, the rebuild notebook and the code/tests
that read it. The optional extra was cheap, so it is in:
fev-bench's average win rate (mean over all other methods of
the share of windows with the lower MASE) is computed in
`scripts/score_forecasts.py` and shipped as `avg_win_rate`
(e.g. day-ahead: operator 0.661, Chronos-2 0.601, Moirai 2.0
0.593; week-ahead: Moirai 2.0 0.633, Chronos-2 0.631).

## Item 4 — Sundial interval check

`scripts/check_sundial_intervals.py` ran the official
Sundial quick-start generate call next to the adapter on
identical contexts (AECI 2025-11-03, PJM 2026-03-09, ERCO
2026-07-06; week horizon; same seed; the transformers
4.40.1 local environment of DECISIONS #35). **They match
exactly**: with the same seed, the adapter's quantiles equal
the quick-start's at q0.1, q0.5 and q0.9 on all three windows
(max difference 0.0000 MW), and the stored run's interval
widths sit within sampling variation of a fresh draw (mean
width ratios 1.02, 1.11, 1.20). No adapter change, no
re-run; coverage 0.32 stands. Wherever Sundial coverage is
stated (README, page), it now says the intervals are from
20 samples, as shipped.

## Item 5 — Granite TTM context

The v1 run used the checkpoint's 512-hour default revision.
The 1,536-hour revision (`1536-96-r2`) was re-run on local
CPU: a timed subset put the full run at minutes, and the run
itself took **450 s** (4,998 windows, 0 failed, effective
context 1,536 recorded on every call) — far inside the
8-hour cap, so the 1,536 version is the scored one. Run
state was kept in `results/ttm1536_state.md` throughout.
Both versions (DEVIATIONS.md entry 2): 512-hour — day +25.1
[20.3, 30.1], week +17.0 [14.5, 19.5]; 1,536-hour — day
**+26.3** [22.4, 30.1], week **+15.9** [13.3, 18.3]. The
longer context helps day-ahead and hurts week-ahead; the
model's rank is unchanged. The 512-hour forecasts are
archived at `results/forecasts/parts/ttm_ctx512_archive.parquet`.

## Item 6 — Alignment tests

`tests/test_alignment.py` adds: unit tests for
`target_steps` — a context ending 13:00 UTC, next-local-day
targets in America/New_York and Australia/Sydney, the
25-hour fall-back day and the 23-hour spring-forward day —
and a stub-adapter test (the stub returns its step numbers;
the sliced output must match the target hours, on plain and
DST days). **Full suite: 46 passed** (was 39; the round also
updated the contamination registry test and added an
average-win-rate case).

## Item 7 — Operator caveats (README limits)

Added in plain words: the operator's own issue time is not
published and may be later than 15:00 UTC the day before, so
it may rest on fresher data; operators forecast with weather
forecasts and local knowledge while the foundation models
see only past load; the retrospective track uses revised
history (PUDL) while the operator forecast was made in real
time; so "beats operator" measures a real-world bar, not a
matched comparison.

## Item 8 — Repo hygiene

`scripts/kaggle_dataset.py` read a hard-coded path for the
credential helper; it now reads
`CREDENTIAL_HELPER_DIR` from the environment and stops with
instructions when unset (the step-8 script imports it as a
module, so one fix covers both). Also found and fixed: `.venv-chronos`
(519 files) was tracked in git despite being in .gitignore;
it is untracked, files kept on disk. The TTM re-run's parts
directory and runner state were added to .gitignore.

## Follow-up (proposed above; completed 2026-11-20)

The private Kaggle dataset `omidgolchin/grid-load-index-data`
stood at **version 2 with the v1-build score files** when
this report was written: `win_rate` naming, the flagged
ranking and the 512-hour TTM scores; the pushed rebuild
notebook was likewise the v1 build. The **dataset v3
refresh** — regenerated score files (summary.csv with
`beats_snaive`/`avg_win_rate`, the new paired.csv, window
scores, the TTM 1,536 forecasts) plus the regenerated
notebook — was proposed here and, on approval, carried out
the same day (DECISIONS #55). The dataset now stands at
**version 3** (354,734,093 bytes, isPrivate = true verified
by API read), with every staged file hash-checked against
its repo source before upload and no version 2 blob token
reused. The rebuild notebook
(`omidgolchin/grid-load-index-leaderboard-rebuild`) is at
version 2, private on pull-back, and its run completed with
no failure message, so its built-in verification passed
against the version 3 files. Nothing else was uploaded.

## Verification

Scores regenerated (`scripts/score_forecasts.py`), paired
tables computed, site rebuilt; full test suite **46 passed**;
page checked headless at 1280 px and 390 px — the paired
view renders, no errors, no overflow — and both leaderboard
screenshots refreshed. Spend this round: $0; Kaggle GPU 0 h;
local CPU ≈ 13 minutes (TTM re-run 450 s, Sundial check
≈ 5 min, scoring/bootstrap runs). `SPEND.md` and
`results/FOUNDATION_STATE.md` updated.

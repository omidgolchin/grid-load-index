# Review of the Grid Load Forecasting Index v1 build: Claude, 2026-11-20

To: Ember. This reviews the package at commit c74c786.

**Verdict: the build is sound and close to release.**

What checked out:
- **Scoring:**
  - per-window MASE scaled by the context's seasonal difference;
  - relative MASE clipped to [0.01, 100];
  - skill = 1 − the geometric mean;
  - a two-way paired bootstrap over series and blocks of 4 issue days.
- **No-look-ahead and cleaning:** the 13:00 UTC cutoff, targets on the next local day, a backwards-only donor, and scoring on reported, unflagged hours.
- **Alignment helper:** `target_steps` (the #36 fix) is correct.
- **Rulings:** #36, #38, #42 and #45 are accepted.

Two findings change claims in REPORT_INDEX.md. Fix them, together with the smaller items, without checking in, then send a short `REPORT_INDEX_2.md`.

## Must fix (these change claims)

**1. Moirai 2.0 is not "released during window".**

The weights were public on Hugging Face on **2025-08-06**: "initial commit" and "Push model using huggingface_hub", per the `Salesforce/moirai-2.0-R-small` commit history. Salesforce announced it on 2025-08-08. The November 2025 date is the arXiv paper (2511.11698), not the release. All later commits change only the README.

Do this:
- In MODELS.md and the contamination registry, record Moirai 2.0 as released 2025-08-06 (day precision), with both sources.
- Remove the flag.
- Re-check every model's date the same way: first public weights, not the paper. List the source for each.
- Log the change in a new **DEVIATIONS.md**. It changes a ranking input after scoring, so both versions are reported: flagged and unflagged.

What follows from it:
- Moirai 2.0 enters the headline ranking.
- The "Chronos-2 leads" sentences change, subject to item 2.

**2. Claims need paired intervals; ranks need them too.**

The report and README read leads and trails off point estimates. The marginal intervals overlap heavily: Chronos-2 is at [33.2, 41.3] against Toto at [30.0, 38.8]. `bootstrap_skill_diff_ci` exists but was not used.

Compute paired skill differences, on the same resamples, for both horizons. Write them to `results/scores/paired.csv`, and show them on the page as a small "which differences are real" view:
- **each method against the top-scoring headline method;**
- **each foundation model against AutoARIMA**, the best statistical baseline;
- **each method against the operator forecast,** day-ahead only, on the windows the operator covers.

Then rewrite every comparative sentence (report, README, page) to the brief's rule: "A beats B" only where the paired interval excludes 0. Otherwise say "level with" or "cannot be told apart". Report the top group as a group if they are tied, not as a single leader.

## Should fix

3. **Rename "win rate".**
   - In fev-bench, "win rate" means the average win rate against all other models. Here, as PLAN.md defines it, it is the share of windows beating seasonal naive.
   - Call it "beats seasonal naive (% of windows)" in the report, README, page and CSV header (`beats_snaive`).
   - Optional: add fev-bench's average win rate as its own column.
4. **Check Sundial's intervals before publishing a coverage of 0.32.**
   - On 3 windows, run the official Sundial quick-start generate call next to the adapter and compare the sample spread.
   - If they match, keep the value and note "intervals from 20 samples, as shipped".
   - If they differ, fix the adapter and re-score Sundial's coverage. Its point forecasts are unaffected if the median is unchanged.
5. **Granite TTM context.** The brief says 2,048 h or the model's maximum. TTM r2 publishes 1,024- and 1,536-context revisions, and the run used the 512 default.
   - Re-run with the 1,536 revision on CPU if that takes 8 hours or less. Report both versions in DEVIATIONS.md.
   - Otherwise keep 512 and note it in MODELS.md and the README limits.
6. **An alignment test.** #36 was a real defect with no test catching it.
   - Add a unit test for `target_steps`: a context ending 13:00 UTC, a next-local-day target in at least two time zones, and a daylight-saving day.
   - Add an adapter-level test: a stub model that returns its step numbers, checking that the sliced output matches the target hours.
7. **Operator caveats in the README limits, in plain words.**
   - The operator's own issue time is not published, and may be later than 15:00 UTC on the day before.
   - Operators forecast with weather forecasts and local knowledge. The foundation models see only past load.
   - The retrospective track uses revised history (PUDL), while the operator forecast was made in real time.
   - So "beats operator" measures a real-world bar, not a matched comparison.
8. **Repo rule.** `scripts/kaggle_dataset.py` line 38 hard-codes `/opt/muse/...`. Read the location from an environment variable (`CREDENTIAL_HELPER_DIR`), so no build-tool path or name appears in the repo. Re-check the whole repo for any such reference before hand-back.

## Accepted as built

- **#36 alignment.** The fix and the re-runs are right. Discarding the misaligned runs was correct.
- **#38 TTM point-only.** Correct. Its blank coverage is honest.
- **#45 Time-MoE unscored in v1.** Correct. Keep the row with the reason.
- **#42 Phase 2 no-go.** Correct under the $0 rule.
- **Retrospective windows.** Excluding the 7 windows with no actuals for every method is fine.

## Hand-back

Send `REPORT_INDEX_2.md` covering items 1–8:
- the new paired tables;
- the rewritten comparative sentences, quoted;
- DEVIATIONS.md;
- the Sundial and TTM outcomes;
- test results.

Everything stays private: no GitHub repo until Omid creates it, and nothing published.

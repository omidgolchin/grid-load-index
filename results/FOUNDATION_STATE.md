# Foundation-model stage — state

Updated 2026-11-20 17:05 UTC. All runs private, $0.
Review round (2026-11-20): Granite TTM was re-run locally at
its 1,536-hour revision and re-scored (DECISIONS #52,
DEVIATIONS.md entry 2); Sundial's adapter was verified
against the model's official quick-start with no change
(DECISIONS #51). Kaggle GPU time in the review round: 0 h.
GPU budget: 20 h/week project cap (SPEND.md has the ledger).
Cumulative Kaggle GPU time: ≈ 17.2 h — inside the cap.
Nine of the ten models are complete and merged; Time-MoE is
unscored in v1 (DECISIONS #45): its Kaggle run degenerated
under the kernel environment (DECISIONS #39), and the local
CPU re-run was stopped at 2 of 49 series after repeated
silent deaths and machine reboots on 2026-11-20, with a
projected 28–44 hours remaining. Its two completed series
parts (AECI, AVA) are kept in results/forecasts/parts/ for a
possible later release.

## Alignment fix (DECISIONS #36)

The first full runs were generated with adapters that did not
bridge the gap between the snapshot cutoff and the target
span; those outputs were discarded and every affected model
was re-run with the corrected adapters. The fix is verified:
Moirai 2.0 with corrected adapters scores day skill +37.2%
and week +24.2% against seasonal naive (the misaligned run
scored about −123%).

## Per-model status

| Model | Smoke | Probe (T4) | Full run |
|---|---|---|---|
| chronos_bolt | PASS local | 0.356 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| chronos_2 | PASS local | 0.129 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| timesfm_2_5 | PASS local | 0.345 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| moirai_2 | PASS local | 0.131 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| moirai_moe | PASS local | 2.259 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| tirex | PASS local (ctx 2016) | 2.264 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| ttm | PASS local | n/a — local CPU per the brief | **complete, merged** — local CPU run, 4,998 windows, 0 failed; re-run at the 1,536-hour revision 2026-11-20 (450 s, 0 failed), the 512-hour forecasts archived |
| sundial | PASS local | n/a — cannot run on the kernel image (DECISIONS #35) | **complete, merged** — local CPU run, 4,998 windows, 0 failed |
| toto | PASS local (after the id_mask fix, DECISIONS #37) | 1.31 s/snap, 48/48 | **complete, merged** — 4,998 windows, 0 failed |
| time_moe | PASS local | 7.14 s/snap, 48/48, proj 4.96 h | Kaggle run discarded (DECISIONS #39); local re-run stopped at 2/49 series — **unscored in v1** (DECISIONS #45) |

## Effective context per model (verified in-run)

chronos_bolt 2048 · chronos_2 2048 · timesfm_2_5 2048 ·
moirai_2 2048 · moirai_moe 2048 · tirex 2016 (library cap,
DECISIONS #28) · toto 2048 · sundial 2048 · ttm 1536
(scored revision, DECISIONS #52; the first v1 run used the
512-hour default) · time_moe 2048.

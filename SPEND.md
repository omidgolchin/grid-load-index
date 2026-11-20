# Spend

Money spent on this project: **$0** (Kaggle free tier and local
CPU only, per the project brief).

## Kaggle GPU hours

Project cap from the brief: at most 20 GPU hours per week on
Kaggle's free tier (the account's own weekly quota is 30 hours;
the same account also ran the S04 study's kernels earlier in
the week of 2026-11-16, about 9.4 GPU hours).

Runtimes below are session wall-clock times from push to
completion as observed by polling (marked ~), except the
runner's own forecast-time totals, which are in the run
summaries under results/. Failed probe versions are included:
they consumed sessions too, mostly in package installation
before failing.

| Date (UTC) | Kernel | Model / purpose | Accelerator | Runtime | GPU hours |
|---|---|---|---|---|---|
| 2026-11-19 | omidgolchin/gli-moirai-2-probe (v1–v5) | Moirai 2.0 probe (24 snapshots); v1–v4 failed in environment setup, v5 complete 48/48 windows | NvidiaTeslaT4 | ~15 min total | ~0.25 |
| 2026-11-19 | omidgolchin/gli-moirai-moe-probe (v1–v4) | Moirai-MoE probe (24 snapshots); v1–v3 failed in environment setup, v4 complete 48/48 windows | NvidiaTeslaT4 | ~15 min total | ~0.25 |
| 2026-11-19 | omidgolchin/gli-chronos-bolt-probe (v1) | Chronos-Bolt probe (24 snapshots), complete 48/48 windows | NvidiaTeslaT4 | ~4 min | ~0.07 |
| 2026-11-19 | omidgolchin/gli-time-moe-probe (v1–v7) | Time-MoE probe (24 snapshots); v1–v6 failed (installer and transformers cache-API incompatibilities), v7 complete 48/48 windows | NvidiaTeslaT4 | ~30 min total | ~0.50 |
| 2026-11-19 | omidgolchin/gli-moirai-2-full (v1) | Moirai 2.0 full run: 4,998/4,998 windows, 0 failed — outputs later discarded (target-span alignment, DECISIONS #36) | NvidiaTeslaT4 | ~7 min | ~0.12 |
| 2026-11-19 | omidgolchin/gli-chronos-2-probe (v1) | Chronos-2 probe (24 snapshots), complete 48/48 windows | NvidiaTeslaT4 | ~6 min | ~0.10 |
| 2026-11-19 | omidgolchin/gli-tirex-probe (v1) | TiRex probe (24 snapshots), complete 48/48 windows | NvidiaTeslaT4 | ~9 min | ~0.15 |
| 2026-11-19 | omidgolchin/gli-chronos-2-full (v1) | Chronos-2 full run — outputs discarded (DECISIONS #36) | NvidiaTeslaT4 | ~18 min | ~0.30 |
| 2026-11-19 | omidgolchin/gli-moirai-moe-full (v1) | Moirai-MoE full run — outputs discarded (DECISIONS #36) | NvidiaTeslaT4 | ~102 min | ~1.70 |
| 2026-11-19 | omidgolchin/gli-tirex-full (v1) | TiRex full run — outputs discarded (DECISIONS #36) | NvidiaTeslaT4 | ~97 min | ~1.62 |
| 2026-11-19 | omidgolchin/gli-moirai-2-full (v2) | Moirai 2.0 full run with corrected adapters: 4,998/4,998 windows, 0 failed; merged and scored (alignment verified) | NvidiaTeslaT4 | ~6 min | ~0.10 |
| 2026-11-19 | omidgolchin/gli-chronos-2-full (v2) | Chronos-2 full run with corrected adapters: 4,998/4,998 windows, 0 failed; merged | NvidiaTeslaT4 | ~6 min | ~0.10 |
| 2026-11-19 | omidgolchin/gli-chronos-bolt-full (v1) | Chronos-Bolt full run with corrected adapters: 4,998/4,998 windows, 0 failed; merged | NvidiaTeslaT4 | ~19 min | ~0.32 |
| 2026-11-19 | omidgolchin/gli-tirex-full (v2) | TiRex full run with corrected adapters: 4,998/4,998 windows, 0 failed; merged | NvidiaTeslaT4 | ~103 min | ~1.72 |
| 2026-11-19 | omidgolchin/gli-moirai-moe-full (v2) | Moirai-MoE full run with corrected adapters: 4,998/4,998 windows, 0 failed; merged | NvidiaTeslaT4 | ~107 min | ~1.78 |
| 2026-11-19 | omidgolchin/gli-timesfm-2-5-probe (v1) | TimesFM 2.5 probe (24 snapshots), complete 48/48 windows, 0.345 s/snapshot | NvidiaTeslaT4 | ~6 min | ~0.10 |
| 2026-11-19 | omidgolchin/gli-timesfm-2-5-full (v1) | TimesFM 2.5 full run: 4,998/4,998 windows, 0 failed; merged | NvidiaTeslaT4 | ~12 min | ~0.20 |
| 2026-11-19/20 | omidgolchin/gli-toto-probe (v1–v3) | Toto probes: v1 failed on a torchvision/torch mismatch, v2 ran with every window failing on the adapter's scalar id_mask, v3 complete 48/48 windows at 1.31 s/snapshot (DECISIONS #37) | NvidiaTeslaT4 | ~46 min total | ~0.77 |
| 2026-11-20 | omidgolchin/gli-toto-full (v1) | Toto full run with corrected adapters: 4,998/4,998 windows, 0 failed; merged | NvidiaTeslaT4 | ~76 min | ~1.27 |
| 2026-11-19/20 | omidgolchin/gli-time-moe-full (v1) | Time-MoE full run — outputs discarded: generation degenerated to a constant under the kernel's transformers 4.47.1 cache patch (DECISIONS #39); local CPU re-run stopped at 2/49 series, unscored in v1 (DECISIONS #45) | NvidiaTeslaT4 | ~346 min | ~5.77 |

Running total for the week of 2026-11-16 (this project):
~17.2 GPU hours, of the 20 h cap (about 9.4 h of it produced
discarded runs: the pre-fix alignment runs and the Time-MoE
environment failure). Sundial, TTM and the Time-MoE local
re-run (stopped at 2 of 49 series; DECISIONS #45) ran locally
on CPU and consumed no GPU budget. The local CPU time used by
the Time-MoE re-run before it stopped was about 1.2 hours
(4,206 s of forecast time across the two completed series,
plus restarts).

## Local runs

Local CPU runs (adapter smoke tests, the TTM timing probe and
any local full runs) consume no GPU budget and are recorded in
the run state files and DECISIONS.md.

Review round (2026-11-20), local CPU only, Kaggle GPU 0 h:
the Granite TTM 1,536-hour re-run (450 s for 4,998 windows)
and the Sundial interval check (3 windows, about 5 minutes
including model load). Money: $0.

## Dataset

Private Kaggle dataset for the runs:
omidgolchin/grid-load-index-data (created 2026-11-19, privacy
verified through the API: isPrivate = true). Contents:
snapshot contexts, snapshot ids and target timestamps only —
no reported values (DECISIONS.md #33). This dataset is also
the starting point for the brief's Step 8 dataset.

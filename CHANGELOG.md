# Changelog

Releases of the index, tagged by month. Scores are never edited
in place: a correction or a new model produces a new release,
and the previous release's files stay in git history.

## v2026.11 — in preparation (not yet published)

- Retrospective track: 49 balancing authorities, weekly Monday
  issue days 2025-11-03 to 2026-10-19, day-ahead and week-ahead
  horizons, 2,048-hour context.
- Ten foundation models under evaluation (Chronos-Bolt,
  Chronos-2, TimesFM 2.5, Moirai 2.0, TiRex, Toto, Sundial,
  Granite TTM r2, Moirai-MoE, Time-MoE), five baselines
  (seasonal naive, naive, AutoETS, AutoARIMA, operator
  forecast). Nine of the ten foundation models are scored in
  this release; Time-MoE is listed unscored (DECISIONS.md #45).
- Moirai 2.0 flagged "released during window" and excluded from
  the retrospective headline ranking (contamination rule).
- Leaderboard page generated from the score files
  (scripts/build_site.py); private Kaggle dataset and rebuild
  notebook prepared (Step 8 record).
- Live track built and dry-run tested on PUDL data; the
  workflow is committed disabled and starts on publication.

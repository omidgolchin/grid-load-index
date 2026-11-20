# Data sources

Access date for all entries: 2026-11-19.

## Demand and operator forecast — EIA Form 930 via PUDL

- **Source as used:** Catalyst Cooperative PUDL parquet outputs,
  public S3 bucket `pudl.catalyst.coop`, versioned prefix
  `v2026.11.0/`.
- **Version (pinned):** stable PUDL release **v2026.11.0**
  (2026-11-10). PUDL's versioned data releases are archived on
  Zenodo under concept DOI 10.5281/zenodo.3653158.
- **Files:**
  - `out_eia930__hourly_operations.parquet` (99,439,486 bytes) —
    BA-level hourly operations: reported demand, PUDL's imputation
    flag for demand, and the operator day-ahead demand forecast
    (`demand_forecast_mwh`) in one table. 6,297,866 rows,
    2015-07-01 05:00 UTC to 2026-11-01 07:00 UTC.
    SHA-256:
    `66680cdc4e42bf3de67355cd6717dd778098a66ee0589821923f3b805c42c24f`
  - `core_eia__codes_balancing_authorities.parquet` — the BA code
    table: each BA's reporting timezone (`report_timezone`) and
    generation-only flag (`is_generation_only`), used by the
    series screen.
    SHA-256:
    `569c796a7bfa61340df433095c377bd98b31b83ee2b8d909b0ab26bdcc786168`
- **Why the stable release:** it reaches 2026-11-01, past the
  2026-10-31 coverage the retrospective window needs, so the
  nightly build is not used.
- **Licences:** the underlying EIA Form 930 data is a work of the
  US federal government and is in the public domain. PUDL's
  processed outputs are CC-BY-4.0 (Catalyst Cooperative).
- PUDL docs:
  https://docs.catalyst.coop/pudl/en/stable/data_sources/eia930.html

## Derived dataset (in this repo's working tree, not in git)

- `data/eval/<BA>.parquet` — one file per qualifying series
  (49 series), full hourly UTC grid 2019-01-01 00:00 to
  2026-11-01 07:00 (68,672 rows each): reported demand, the PUDL
  imputation code, the cleaned model-input series, and the
  operator day-ahead forecast. Built by
  `scripts/extract_data.py` from the pinned file above; per-file
  hashes and row counts in
  `data/manifests/extraction_manifest.csv`.
- The pinned source files themselves are kept out of git
  (`.gitignore`); their hashes above are the pin.

## Live track (not used in this stage)

- EIA API v2, `electricity/rto/region-data` route, for the live
  track's daily snapshots. Needs a free EIA API key, supplied as
  the `EIA_API_KEY` environment variable / repository secret; no
  key is stored in this repository.

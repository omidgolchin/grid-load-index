# Series screen

Access date: 2026-11-19. Source: the pinned PUDL file in
DATA_SOURCES.md (`out_eia930__hourly_operations`, stable release
v2026.11.0). Reproduce with `scripts/screen_series.py`; the readable output is `data/manifests/screen_results.csv`.

## Rules applied

A balancing authority (BA) is included if all of these hold:

1. It reports hourly demand. BAs that report no demand at all are
   excluded as generation-only.
2. Reporting is continuous from 2019-01-01 to the end of the pinned
   file (2026-11-01 07:00 UTC): the BA's rows start at 2019-01-01
   00:00 UTC and run to the end of the file.
3. Missing or flagged hours are less than 5% of the span.

Subregions are not included (v1 scope).

## How "missing" and "flagged" are read from the PUDL table

The span is the full hourly UTC grid from 2019-01-01 00:00 to
2026-11-01 07:00: 68,672 hours.

- **Missing:** no row for that hour, or `demand_reported_mwh` is null.
- **Flagged:** `demand_imputed_pudl_mwh_imputation_code` is non-null.
  PUDL attaches a code whenever it replaced or questioned the reported
  value. The codes present in the file are `missing_value`,
  `bad_year`, `anomalous_region`, `negative_or_zero`,
  `identical_run`, `double_delta`, `local_outlier_high`,
  `local_outlier_low`, `single_delta` and `global_outlier`.

The share is (missing or flagged hours) / 68,672. An hour that is both
reported and flagged counts once, as flagged.

Each BA's timezone is `report_timezone` from PUDL's
`core_eia__codes_balancing_authorities` table in the same release —
the timezone the BA reports in — and its generation-only flag comes
from the same table.

## Result

**49 series qualify; 21 BA codes are excluded.**

Qualifying: AECI, AVA, AZPS, BANC, BPAT, CHPD, CISO, CPLE, CPLW,
DOPD, DUK, EPE, ERCO, FMPP, FPC, FPL, GCPD, GVL, HST, IID, IPCO,
ISNE, JEA, LDWP, LGEE, MISO, NEVP, NWMT, NYIS, PACE, PACW, PGE, PJM,
PNM, PSCO, SC, SCEG, SCL, SOCO, SPA, SRP, SWPP, TAL, TEC, TEPC, TIDC,
TPWR, TVA, WALC.

The closest call is SWPP at 4.35% missing-or-flagged, inside the 5%
limit. The next BA, WAUW at 8.47%, is outside it.

## Full per-BA table

| BA | Timezone | Missing-or-flagged share | Forecast coverage | Verdict | Reason |
|---|---|---:|---:|---|---|
| AEC | America/Chicago | 66.13% | 33.83% | exclude | reporting ends 2021-09-01; missing-or-flagged share 66.1% of the span |
| AECI | America/Chicago | 0.07% | 100.00% | include |  |
| AVA | America/Los_Angeles | 0.12% | 99.97% | include |  |
| AVRN | America/Los_Angeles | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| AZPS | America/Phoenix | 0.19% | 99.93% | include |  |
| BANC | America/Los_Angeles | 2.18% | 99.46% | include |  |
| BHBA | America/Denver | 94.73% | 5.31% | exclude | reporting starts 2026-04-01, not 2019-01-01 |
| BPAT | America/Los_Angeles | 0.07% | 100.00% | include |  |
| CHPD | America/Los_Angeles | 0.44% | 99.90% | include |  |
| CISO | America/Los_Angeles | 0.37% | 99.83% | include |  |
| CPLE | America/New_York | 0.18% | 99.85% | include |  |
| CPLW | America/New_York | 0.23% | 99.89% | include |  |
| DEAA | America/Phoenix | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| DOPD | America/Los_Angeles | 2.82% | 99.37% | include |  |
| DUK | America/New_York | 0.11% | 99.92% | include |  |
| EEI | America/Chicago | 100.00% | 0.00% | exclude | reports no demand in the span (generation/interchange rows only) |
| EPE | America/Phoenix | 0.21% | 99.93% | include |  |
| ERCO | America/Chicago | 0.12% | 99.93% | include |  |
| FMPP | America/New_York | 0.60% | 99.67% | include |  |
| FPC | America/New_York | 0.12% | 99.92% | include |  |
| FPL | America/New_York | 1.26% | 99.73% | include |  |
| GCPD | America/Los_Angeles | 0.42% | 99.94% | include |  |
| GLHB | America/Chicago | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| GRID | America/Los_Angeles | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| GRIF | America/Phoenix | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| GRMA | America/Phoenix | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| GVL | America/New_York | 2.89% | 98.17% | include |  |
| GWA | America/Denver | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| HGMA | America/Phoenix | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| HST | America/New_York | 1.51% | 99.54% | include |  |
| IID | America/Los_Angeles | 1.08% | 99.62% | include |  |
| IPCO | America/Los_Angeles | 0.05% | 100.00% | include |  |
| ISNE | America/New_York | 0.05% | 100.00% | include |  |
| JEA | America/New_York | 0.49% | 95.39% | include |  |
| LDWP | America/Los_Angeles | 0.56% | 99.23% | include |  |
| LGEE | America/New_York | 0.44% | 99.88% | include |  |
| MISO | America/New_York | 0.15% | 99.86% | include |  |
| NEVP | America/Los_Angeles | 0.16% | 99.92% | include |  |
| NSB | America/New_York | 88.12% | 12.27% | exclude | reporting ends 2020-01-08; missing-or-flagged share 88.1% of the span |
| NWMT | America/Denver | 0.40% | 99.25% | include |  |
| NYIS | America/New_York | 0.06% | 100.00% | include |  |
| OVEC | America/New_York | 100.00% | 0.00% | exclude | reports no demand in the span (generation/interchange rows only) |
| PACE | America/Denver | 0.21% | 99.89% | include |  |
| PACW | America/Los_Angeles | 0.07% | 100.00% | include |  |
| PGE | America/Los_Angeles | 0.10% | 100.00% | include |  |
| PJM | America/New_York | 0.34% | 99.65% | include |  |
| PNM | America/Phoenix | 0.13% | 100.00% | include |  |
| PSCO | America/Denver | 0.17% | 98.81% | include |  |
| PSEI | America/Los_Angeles | 13.61% | 100.00% | exclude | missing-or-flagged share 13.6% of the span (>= 5%) |
| SC | America/New_York | 0.51% | 99.64% | include |  |
| SCEG | America/New_York | 0.82% | 98.70% | include |  |
| SCL | America/Los_Angeles | 0.12% | 99.57% | include |  |
| SEC | America/New_York | 29.76% | 99.56% | exclude | missing-or-flagged share 29.8% of the span (>= 5%) |
| SEPA | America/Chicago | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| SOCO | America/Chicago | 0.11% | 99.95% | include |  |
| SPA | America/Chicago | 1.09% | 98.37% | include |  |
| SRP | America/Phoenix | 0.52% | 92.52% | include |  |
| SWPP | America/Chicago | 4.35% | 99.16% | include |  |
| SWPW | America/Denver | 94.39% | 6.82% | exclude | reporting starts 2026-04-01, not 2019-01-01 |
| TAL | America/New_York | 1.19% | 100.00% | include |  |
| TEC | America/New_York | 0.16% | 99.89% | include |  |
| TEPC | America/Phoenix | 1.52% | 99.72% | include |  |
| TIDC | America/Los_Angeles | 0.72% | 99.83% | include |  |
| TPWR | America/Los_Angeles | 0.18% | 100.00% | include |  |
| TVA | America/Chicago | 0.08% | 99.90% | include |  |
| WACM | America/Phoenix | 8.49% | 92.07% | exclude | reporting ends 2026-04-01; missing-or-flagged share 8.5% of the span |
| WALC | America/Phoenix | 0.80% | 99.97% | include |  |
| WAUW | America/Denver | 8.47% | 92.52% | exclude | reporting ends 2026-04-01; missing-or-flagged share 8.5% of the span |
| WWA | America/Denver | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |
| YAD | America/New_York | 100.00% | 0.00% | exclude | generation-only balancing authority (PUDL flag); reports no demand |

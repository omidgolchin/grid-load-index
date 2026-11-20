"""Series screen for the Grid Load Forecasting Index (PLAN step 2).

Reads the pinned PUDL file and applies the series rules:
  - the balancing authority reports hourly demand (not generation-only);
  - reporting covers the full span from 2019-01-01 to the end of the
    pinned file, starting at the span start;
  - missing or flagged hours are less than 5% of the span.

An hour is "missing" if there is no row for it or its reported demand
is null. An hour is "flagged" if PUDL's imputation code for the demand
column is non-null (PUDL replaced or questioned the reported value).

Writes data/manifests/screen_results.csv with one row per BA code in
the pinned file, including the reason for every exclusion.

Usage: .venv/bin/python scripts/screen_series.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "source" / "out_eia930__hourly_operations.parquet"
CODES = ROOT / "data" / "source" / "core_eia__codes_balancing_authorities.parquet"
OUT = ROOT / "data" / "manifests" / "screen_results.csv"

SPAN_START = pd.Timestamp("2019-01-01 00:00")
MAX_MISSING_OR_FLAGGED = 0.05


def main() -> None:
    df = pd.read_parquet(
        SOURCE,
        columns=[
            "datetime_utc",
            "balancing_authority_code_eia",
            "demand_reported_mwh",
            "demand_imputed_pudl_mwh_imputation_code",
            "demand_forecast_mwh",
        ],
    )
    codes = pd.read_parquet(CODES).set_index("code")

    span_end = df["datetime_utc"].max()
    grid = pd.date_range(SPAN_START, span_end, freq="1h")
    n_hours = len(grid)

    rows = []
    for ba, g in sorted(df.groupby("balancing_authority_code_eia")):
        g = g[g["datetime_utc"] >= SPAN_START]
        dupes = int(g.duplicated(subset="datetime_utc").sum())
        gi = g.set_index("datetime_utc")
        reported = gi["demand_reported_mwh"].reindex(grid)
        code = gi["demand_imputed_pudl_mwh_imputation_code"].reindex(grid)
        forecast = gi["demand_forecast_mwh"].reindex(grid)

        n_demand = int(reported.notna().sum())
        n_flagged = int(code.notna().sum())
        n_missing = int(reported.isna().sum())
        share = float((reported.isna() | code.notna()).mean())
        first = g["datetime_utc"].min() if len(g) else None
        last = g["datetime_utc"].max() if len(g) else None
        gen_only = bool(codes.loc[ba, "is_generation_only"]) if ba in codes.index else None
        tz = codes.loc[ba, "report_timezone"] if ba in codes.index else None

        if n_demand == 0:
            verdict = "exclude"
            reason = (
                "generation-only balancing authority (PUDL flag); reports no demand"
                if gen_only
                else "reports no demand in the span (generation/interchange rows only)"
            )
        elif first is not None and first > SPAN_START:
            verdict = "exclude"
            reason = f"reporting starts {first:%Y-%m-%d}, not 2019-01-01"
        elif share >= MAX_MISSING_OR_FLAGGED:
            verdict = "exclude"
            if last is not None and last < span_end - pd.Timedelta(days=30):
                reason = (
                    f"reporting ends {last:%Y-%m-%d}; missing-or-flagged share "
                    f"{share:.1%} of the span"
                )
            else:
                reason = f"missing-or-flagged share {share:.1%} of the span (>= 5%)"
        else:
            verdict = "include"
            reason = ""

        rows.append(
            {
                "ba": ba,
                "timezone": tz,
                "is_generation_only_pudl": gen_only,
                "rows_in_span": int(len(g)),
                "duplicate_timestamps": dupes,
                "first_row_utc": first,
                "last_row_utc": last,
                "span_hours": n_hours,
                "demand_values": n_demand,
                "missing_hours": n_missing,
                "flagged_hours": n_flagged,
                "missing_or_flagged_share": round(share, 4),
                "forecast_coverage_share": round(float(forecast.notna().mean()), 4),
                "verdict": verdict,
                "exclusion_reason": reason,
            }
        )

    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    inc = out[out["verdict"] == "include"]
    print(f"span: {SPAN_START} to {span_end} UTC ({n_hours} hours)")
    print(f"BAs in pinned file: {len(out)}; included: {len(inc)}; excluded: {len(out) - len(inc)}")
    print("included:", ", ".join(inc["ba"]))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

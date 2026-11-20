"""Build the evaluation dataset for the Grid Load Forecasting Index.

For every balancing authority that passes the series screen, writes
one parquet file under data/eval/ with the full hourly UTC grid from
2019-01-01 to the end of the pinned PUDL file:

  datetime_utc          hour (UTC)
  demand_reported_mwh   demand as reported (NaN where absent)
  imputation_code       PUDL flag for the hour (NaN = unflagged)
  demand_clean_mwh      model-input series after the cleaning rule
  demand_forecast_mwh   operator day-ahead demand forecast

Cleaning rule (fixed in PLAN.md): a flagged, missing or non-positive
hour is replaced by the cleaned value 168 hours earlier, which steps
back in whole weeks until a usable hour is found; hours with no usable
hour a whole number of weeks earlier stay NaN.

Also writes data/manifests/extraction_manifest.csv (one row per
series, with the file hash) and data/manifests/qualifying_series.csv.

Usage: .venv/bin/python scripts/extract_data.py
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "source" / "out_eia930__hourly_operations.parquet"
SCREEN = ROOT / "data" / "manifests" / "screen_results.csv"
OUT_DIR = ROOT / "data" / "eval"
MANIFEST = ROOT / "data" / "manifests" / "extraction_manifest.csv"
QUALIFYING = ROOT / "data" / "manifests" / "qualifying_series.csv"

SPAN_START = pd.Timestamp("2019-01-01 00:00")
WEEK = 168


def clean_series(reported: np.ndarray, flagged: np.ndarray) -> tuple[np.ndarray, int]:
    """Apply the weekly step-back cleaning rule. Returns (clean, n_filled)."""
    usable = (~np.isnan(reported)) & (~flagged) & (reported > 0)
    clean = np.where(usable, reported, np.nan)
    n_filled = 0
    for t in range(len(clean)):
        if np.isnan(clean[t]) and t >= WEEK and not np.isnan(clean[t - WEEK]):
            clean[t] = clean[t - WEEK]
            n_filled += 1
    return clean, n_filled


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    screen = pd.read_csv(SCREEN)
    qualifying = screen[screen["verdict"] == "include"].copy()
    qualifying[["ba", "timezone"]].to_csv(QUALIFYING, index=False)

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
    span_end = df["datetime_utc"].max()
    grid = pd.date_range(SPAN_START, span_end, freq="1h")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, q in qualifying.iterrows():
        ba = q["ba"]
        g = df[df["balancing_authority_code_eia"] == ba].set_index("datetime_utc")
        out = pd.DataFrame({"datetime_utc": grid})
        out["demand_reported_mwh"] = g["demand_reported_mwh"].reindex(grid).to_numpy()
        out["imputation_code"] = (
            g["demand_imputed_pudl_mwh_imputation_code"].reindex(grid).astype("string").to_numpy()
        )
        out["demand_forecast_mwh"] = g["demand_forecast_mwh"].reindex(grid).to_numpy()

        flagged = out["imputation_code"].notna().to_numpy()
        clean, n_filled = clean_series(out["demand_reported_mwh"].to_numpy(dtype=float), flagged)
        out["demand_clean_mwh"] = clean

        path = OUT_DIR / f"{ba}.parquet"
        out.to_parquet(path, index=False)
        rows.append(
            {
                "ba": ba,
                "timezone": q["timezone"],
                "file": f"data/eval/{ba}.parquet",
                "rows": len(out),
                "first_utc": out["datetime_utc"].min(),
                "last_utc": out["datetime_utc"].max(),
                "reported_good_hours": int(
                    (
                        out["demand_reported_mwh"].notna()
                        & out["imputation_code"].isna()
                        & (out["demand_reported_mwh"] > 0)
                    ).sum()
                ),
                "filled_by_cleaning": n_filled,
                "still_missing_after_cleaning": int(out["demand_clean_mwh"].isna().sum()),
                "forecast_present_hours": int(out["demand_forecast_mwh"].notna().sum()),
                "file_bytes": path.stat().st_size,
                "sha256": sha256_of(path),
            }
        )
        print(ba, "done")

    manifest = pd.DataFrame(rows)
    manifest.to_csv(MANIFEST, index=False)
    print(f"series written: {len(manifest)}; total bytes: {manifest['file_bytes'].sum()}")
    print(f"wrote {MANIFEST} and {QUALIFYING}")


if __name__ == "__main__":
    main()

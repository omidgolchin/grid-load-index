"""EIA API v2 access for the live track.

The live track's data source is the EIA API v2 route
`electricity/rto/region-data` (EIA Form 930 hourly operating
data). It returns, per balancing authority ("respondent") and
hour ("period", UTC), rows typed by the `type` facet; the two
types the index uses are:

- "D"  — demand (the reported actual);
- "DF" — the operator's day-ahead demand forecast.

Response shape (API documentation, accessed 2026-11-20): a JSON
object whose `response.data` is a list of row objects with
`period`, `respondent`, `type` and `value` fields. Since API
v2.1.6 the data values are standardised as strings, so values
are coerced to float here. Results are paginated at 5,000 rows;
`fetch_region_data` walks the offsets.

The API key is passed in by the caller (the live runner reads it
from the EIA_API_KEY environment variable); nothing in this
module stores or logs it.

`parse_region_data` turns a response payload into the per-series
frames the rest of the harness uses: an hourly UTC grid with the
reported demand and the operator forecast. The route carries no
imputation flag, so parsed hours are unflagged by construction;
EIA's own revisions are handled by the live track's scoring
rule (score against values as published 7 days after the target
day), not by flags.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

API_BASE = "https://api.eia.gov/v2"
ROUTE = "electricity/rto/region-data"
TYPE_DEMAND = "D"
TYPE_FORECAST = "DF"
PAGE_LENGTH = 5000


def build_url(api_key: str, start: str, end: str,
              respondents: list[str], offset: int = 0) -> str:
    """The region-data query URL for one page.

    `start`/`end` use the API's hourly format "YYYY-MM-DDTHH".
    The key travels in the query string, as the API requires;
    callers must not log the returned URL.
    """
    params: list[tuple[str, str]] = [
        ("api_key", api_key),
        ("frequency", "hourly"),
        ("data[]", "value"),
        ("start", start),
        ("end", end),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
        ("offset", str(offset)),
        ("length", str(PAGE_LENGTH)),
    ]
    for respondent in respondents:
        params.append(("facets[respondent][]", respondent))
    for type_code in (TYPE_DEMAND, TYPE_FORECAST):
        params.append(("facets[type][]", type_code))
    return f"{API_BASE}/{ROUTE}/data/?" + urllib.parse.urlencode(params)


def fetch_region_data(api_key: str, start: str, end: str,
                      respondents: list[str]) -> dict:
    """Fetch all pages and merge them into one response payload.

    Returns a payload of the same shape as a single response,
    with `response.data` holding every row. Network errors
    propagate: a partial live snapshot must never be used.
    """
    rows: list[dict] = []
    total: int | None = None
    offset = 0
    while total is None or offset < total:
        url = build_url(api_key, start, end, respondents, offset=offset)
        with urllib.request.urlopen(url, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
        page = payload["response"]["data"]
        total = int(payload["response"]["total"])
        rows.extend(page)
        if not page:
            break
        offset += len(page)
    return {"response": {"total": total, "data": rows}}


def parse_region_data(payload: dict) -> dict[str, pd.DataFrame]:
    """Parse a region-data payload into per-series hourly frames.

    Returns {respondent: DataFrame} indexed by naive-UTC hour
    with columns `demand_reported_mwh` and `demand_forecast_mwh`
    (NaN where the route reported no row for that hour). Hours
    are the union of the demand and forecast periods present in
    the payload; callers reindex onto their own grid.
    """
    rows = payload["response"]["data"]
    frames: dict[str, pd.DataFrame] = {}
    if not rows:
        return frames
    raw = pd.DataFrame(rows)
    raw["period"] = pd.to_datetime(raw["period"], format="%Y-%m-%dT%H")
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce").astype(float)
    for respondent, group in raw.groupby("respondent"):
        demand = (group[group["type"] == TYPE_DEMAND]
                  .set_index("period")["value"].sort_index())
        forecast = (group[group["type"] == TYPE_FORECAST]
                    .set_index("period")["value"].sort_index())
        index = demand.index.union(forecast.index)
        frame = pd.DataFrame(index=index)
        frame["demand_reported_mwh"] = demand.reindex(index)
        frame["demand_forecast_mwh"] = forecast.reindex(index)
        frame.index.name = "datetime_utc"
        frames[str(respondent)] = frame
    return frames


def to_eval_frame(frame: pd.DataFrame, grid_start: pd.Timestamp,
                  grid_end: pd.Timestamp) -> pd.DataFrame:
    """Reindex a parsed frame onto a continuous hourly UTC grid,
    in the shape the harness's extraction uses: reported demand,
    a null imputation code (the route carries no flag), and the
    operator forecast. Hours outside the payload stay NaN, which
    the cleaning rule treats as missing."""
    grid = pd.date_range(grid_start, grid_end, freq="1h")
    out = frame.reindex(grid)
    out["imputation_code"] = np.nan
    out.index.name = "datetime_utc"
    return out[["demand_reported_mwh", "imputation_code", "demand_forecast_mwh"]]

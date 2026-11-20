"""Tests for the live track's EIA API path (src/eia_api.py).

The fixture in tests/fixtures/ follows the response schema in
EIA's API v2 documentation (accessed 2026-11-20): the
`response.data` row shape for electricity/rto/region-data, with
values as strings as standardised in API v2.1.6. No EIA_API_KEY
exists yet, so the fixture was written from the documentation
rather than recorded from a live call; when the key is added it
should be re-recorded from the live API and these tests re-run
against the recording (DECISIONS.md, live-track entry).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src import eia_api

FIXTURE = (Path(__file__).parent / "fixtures" / "eia_region_data_response.json")


def load_payload() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parse_splits_demand_and_forecast_by_respondent():
    frames = eia_api.parse_region_data(load_payload())
    assert sorted(frames) == ["ERCO", "PJM"]
    pjm = frames["PJM"]
    assert list(pjm.columns) == ["demand_reported_mwh", "demand_forecast_mwh"]
    assert len(pjm) == 4
    assert pjm.index[0] == pd.Timestamp("2026-10-26 09:00")
    assert pjm.loc["2026-10-26 11:00", "demand_reported_mwh"] == 88902.0
    assert pjm.loc["2026-10-26 11:00", "demand_forecast_mwh"] == 89330.0


def test_values_are_coerced_from_strings():
    frames = eia_api.parse_region_data(load_payload())
    assert frames["ERCO"]["demand_reported_mwh"].dtype == float
    assert frames["ERCO"].loc["2026-10-26 09:00", "demand_reported_mwh"] == 41208.0


def test_missing_forecast_hour_is_nan_not_dropped():
    frames = eia_api.parse_region_data(load_payload())
    erco = frames["ERCO"]
    # The payload has no ERCO forecast row for 12:00; the hour
    # stays on the grid with a NaN forecast.
    assert len(erco) == 4
    assert np.isnan(erco.loc["2026-10-26 12:00", "demand_forecast_mwh"])
    assert erco.loc["2026-10-26 12:00", "demand_reported_mwh"] == 44981.0


def test_to_eval_frame_reindexes_onto_the_grid():
    frames = eia_api.parse_region_data(load_payload())
    out = eia_api.to_eval_frame(frames["PJM"], pd.Timestamp("2026-10-26 08:00"),
                                pd.Timestamp("2026-10-26 13:00"))
    assert len(out) == 6
    assert list(out.columns) == ["demand_reported_mwh", "imputation_code",
                                 "demand_forecast_mwh"]
    assert out["imputation_code"].isna().all()
    assert np.isnan(out.loc["2026-10-26 08:00", "demand_reported_mwh"])
    assert out.loc["2026-10-26 09:00", "demand_reported_mwh"] == 81234.0


def test_build_url_shape():
    url = eia_api.build_url("KEY", "2026-10-01T00", "2026-10-26T13",
                            ["PJM", "ERCO"], offset=5000)
    assert url.startswith("https://api.eia.gov/v2/electricity/rto/region-data/data/?")
    assert "start=2026-10-01T00" in url and "end=2026-10-26T13" in url
    assert "offset=5000" in url and "length=5000" in url
    assert url.count("facets%5Brespondent%5D%5B%5D=") == 2
    assert url.count("facets%5Btype%5D%5B%5D=") == 2

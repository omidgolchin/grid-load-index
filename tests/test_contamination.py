"""Contamination flagging (PLAN.md): a model released after the
retrospective window starts (2025-11-03) is scored, marked
"released during window", and excluded from the headline ranking
input.
"""

from datetime import date

import pytest

from src.contamination import (
    MODEL_REGISTRY,
    ModelRecord,
    flag_models,
    headline_ranking_input,
    is_released_during_window,
)

START = date(2025, 11, 3)


def test_day_precision_dates():
    assert is_released_during_window("2025-12-01", START) is True
    assert is_released_during_window("2025-11-04", START) is True
    assert is_released_during_window("2025-11-03", START) is False  # on the start date: not after
    assert is_released_during_window("2025-09-15", START) is False


def test_month_precision_dates():
    assert is_released_during_window("2026-01", START) is True
    assert is_released_during_window("2025-12", START) is True
    assert is_released_during_window("2025-10", START) is False
    assert is_released_during_window("2024-10", START) is False


def test_window_month_needs_a_recorded_determination():
    with pytest.raises(ValueError):
        is_released_during_window("2025-11", START)
    assert is_released_during_window("2025-11", START, same_month_determination=True) is True
    assert is_released_during_window("2025-11", START, same_month_determination=False) is False


def test_flagged_models_are_excluded_from_headline_input():
    records = (
        ModelRecord("Old", "2024-05"),
        ModelRecord("New", "2026-02-01"),
        ModelRecord("Edge", "2025-11", same_month_determination=True),
    )
    flags = flag_models(records, START)
    assert flags == {"Old": False, "New": True, "Edge": True}
    assert headline_ranking_input(records, START) == ["Old"]


def test_the_v1_registry():
    flags = flag_models()
    # MODELS.md (dates re-based on first public weights,
    # 2026-11-20): no v1 model was released after the window
    # start. Moirai 2.0's weights were public on 2025-08-06;
    # the November 2025 date used at first was its paper
    # (DEVIATIONS.md).
    assert all(not v for v in flags.values())
    assert flags["Moirai 2.0"] is False
    eligible = headline_ranking_input()
    assert eligible == [r.name for r in MODEL_REGISTRY]
    assert len(eligible) == len(MODEL_REGISTRY) == 10

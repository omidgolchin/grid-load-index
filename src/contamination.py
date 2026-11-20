"""Contamination flagging (PLAN: contamination rule).

A model released after the retrospective window starts (2025-11-03)
is still scored, is marked "released during window", and is
excluded from the retrospective headline ranking.

Release dates are recorded at the precision MODELS.md publishes
them: an exact day where the record gives one, otherwise the month.
A month-precision release in a month after the window-start month
is during the window; in an earlier month it is not; in the
window-start month itself the determination already recorded in
MODELS.md applies.

Dates were re-based on 2026-11-20 on the first public weights
(Hugging Face repository creation / commit history), not the
paper date. Moirai 2.0's weights were public on 2025-08-06, so
it is not flagged; the November 2025 date used at first was its
paper. The correction is logged in DEVIATIONS.md. With the
corrected dates, no v1 model is released during the window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .spec import WINDOW_START


@dataclass(frozen=True)
class ModelRecord:
    name: str
    release: str  # "YYYY-MM-DD" (day precision) or "YYYY-MM" (month precision)
    same_month_determination: bool | None = None  # MODELS.md ruling if release month == window month


# The v1 model list, transcribed from MODELS.md. Release dates
# are the first-public-weights dates (Hugging Face repository
# creation, accessed 2026-11-20; DECISIONS.md #48).
MODEL_REGISTRY: tuple[ModelRecord, ...] = (
    ModelRecord("Chronos-Bolt (base)", "2024-11-25"),
    ModelRecord("Chronos-2", "2025-10-30"),
    ModelRecord("TimesFM 2.5", "2025-09-02"),
    ModelRecord("Moirai 2.0", "2025-08-06"),
    ModelRecord("TiRex", "2025-05-26"),
    ModelRecord("Toto", "2025-04-30"),
    ModelRecord("Sundial", "2025-05-13"),
    ModelRecord("Granite TTM r2", "2024-10-08"),
    ModelRecord("Moirai-MoE", "2024-11-01"),
    ModelRecord("Time-MoE", "2024-09-21"),
)


def is_released_during_window(release: str, window_start: date = WINDOW_START,
                              same_month_determination: bool | None = None) -> bool:
    """Whether a release date falls after the window start.

    Day precision ("YYYY-MM-DD"): released after `window_start`.
    Month precision ("YYYY-MM"): a later month is during the
    window, an earlier month is not, and the window's own month
    uses `same_month_determination` (the ruling recorded with the
    model's record); without a determination it raises, so the
    case is decided explicitly rather than silently.
    """
    parts = release.split("-")
    if len(parts) == 3:
        return date(int(parts[0]), int(parts[1]), int(parts[2])) > window_start
    if len(parts) == 2:
        ym = (int(parts[0]), int(parts[1]))
        start_ym = (window_start.year, window_start.month)
        if ym != start_ym:
            return ym > start_ym
        if same_month_determination is None:
            raise ValueError(
                f"release {release!r} is in the window-start month; "
                "a determination must be recorded with the model record"
            )
        return same_month_determination
    raise ValueError(f"unrecognised release date format: {release!r}")


def flag_models(records: tuple[ModelRecord, ...] = MODEL_REGISTRY,
                window_start: date = WINDOW_START) -> dict[str, bool]:
    """Map of model name -> released-during-window flag."""
    return {
        r.name: is_released_during_window(r.release, window_start, r.same_month_determination)
        for r in records
    }


def headline_ranking_input(records: tuple[ModelRecord, ...] = MODEL_REGISTRY,
                           window_start: date = WINDOW_START) -> list[str]:
    """Names eligible for the retrospective headline ranking.

    Models released during the window are scored but excluded
    here, per the contamination rule.
    """
    flags = flag_models(records, window_start)
    return [r.name for r in records if not flags[r.name]]

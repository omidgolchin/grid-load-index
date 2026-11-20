"""Build the leaderboard page (docs/index.html) from the scores.

One command rebuilds the page from the current score files:

    .venv/bin/python scripts/build_site.py

Inputs: results/scores/summary.csv (aggregate scores with
bootstrap intervals), results/scores/window_scores.parquet
(per-window scores; the source for the MASE column and the
per-BA view) and results/scores/paired.csv (paired skill
differences for the "which differences are real" view, when
present). The page template is site/template.html; the kit
stylesheets are vendored in site/ and copied into docs/ on every
build, so the page renders identically from a fresh checkout.

A foundation model in MODELS.md that has no scores appears
as a "not scored in v1" row with the reason from
UNSCORED_NOTES, so re-running this script after a scoring
pass is the whole update — no page edits.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import spec  # noqa: E402

ROOT = spec.ROOT
SITE_DIR = ROOT / "site"
DOCS_DIR = ROOT / "docs"
SCORES_DIR = ROOT / "results" / "scores"

# Method id -> (display name, kind). Display names match MODELS.md;
# kinds: "model" (foundation model), "baseline", "operator",
# "reference" (seasonal naive, the scale for every score).
METHODS: dict[str, tuple[str, str]] = {
    "operator": ("Operator forecast", "operator"),
    "chronos_2": ("Chronos-2", "model"),
    "moirai_2": ("Moirai 2.0", "model"),
    "tirex": ("TiRex", "model"),
    "chronos_bolt": ("Chronos-Bolt (base)", "model"),
    "timesfm_2_5": ("TimesFM 2.5", "model"),
    "moirai_moe": ("Moirai-MoE", "model"),
    "sundial": ("Sundial", "model"),
    "toto": ("Toto", "model"),
    "ttm": ("Granite TTM r2", "model"),
    "time_moe": ("Time-MoE", "model"),
    "autoarima": ("AutoARIMA", "baseline"),
    "autoets": ("AutoETS", "baseline"),
    "naive": ("Naive", "baseline"),
    "seasonal_naive": ("Seasonal naive", "reference"),
}

# Released after the retrospective window start (contamination
# rule; MODELS.md and src/contamination.py carry the record).
# Empty in this release: release dates were re-based on first
# public weights on 2026-11-20 and no v1 model was released
# during the window (DEVIATIONS.md).
RELEASED_DURING_WINDOW = set()

# Models with no scores in this release, and why (DECISIONS.md).
UNSCORED_NOTES = {
    "time_moe": ("Not scored in v1: the Kaggle run failed in its "
                 "environment and the local re-run was stopped at "
                 "2 of 49 series (DECISIONS #45)"),
}


def _num(value, ndigits):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    return round(float(value), ndigits)


def leaderboard_rows(summary: pd.DataFrame, window_scores: pd.DataFrame) -> dict:
    mean_mase = (window_scores.groupby(["method", "horizon"])["mase"]
                 .mean().rename("mean_mase").reset_index())
    merged = summary.merge(mean_mase, on=["method", "horizon"], how="left")
    out: dict[str, list[dict]] = {}
    for horizon in spec.HORIZONS:
        rows = []
        sub = merged[merged["horizon"] == horizon]
        scored = set(sub["method"])
        for _, r in sub.iterrows():
            name, kind = METHODS.get(r["method"], (r["method"], "model"))
            rows.append({
                "method": r["method"], "name": name, "kind": kind,
                "skill": _num(r["skill_pct"], 2),
                "ci_lo": _num(r["skill_ci_lo"], 2),
                "ci_hi": _num(r["skill_ci_hi"], 2),
                "beats_snaive": _num(r["beats_snaive"], 4),
                "mase": _num(r["mean_mase"], 4),
                "coverage": _num(r["mean_coverage80"], 4),
                "peak_error": _num(r["mean_peak_error"], 1),
                "beats_operator": _num(r["beats_operator"], 4),
                "windows": int(r["windows"]),
                "failed": int(r["failed_windows"]),
                "released_during_window": r["method"] in RELEASED_DURING_WINDOW,
                "pending": False,
            })
        # Foundation models registered in MODELS.md but not yet
        # scored for this horizon appear as pending rows.
        for method, (name, kind) in METHODS.items():
            if kind == "model" and method not in scored:
                rows.append({
                    "method": method, "name": name, "kind": kind,
                    "skill": None, "ci_lo": None, "ci_hi": None,
                    "beats_snaive": None, "mase": None, "coverage": None,
                    "peak_error": None, "beats_operator": None,
                    "windows": None, "failed": None,
                    "released_during_window": method in RELEASED_DURING_WINDOW,
                    "pending": True,
                    "note": UNSCORED_NOTES.get(method, "Not scored in v1"),
                })
        rows.sort(key=lambda r: (r["pending"], -(r["skill"] or 0)))
        out[horizon] = rows
    return out


def per_ba_tables(window_scores: pd.DataFrame) -> dict:
    grouped = (window_scores.groupby(["horizon", "series", "method"])
               .agg(mase=("mase", "mean"), mae=("mae", "mean"),
                    coverage=("coverage80", "mean"),
                    peak_error=("peak_error", "mean"),
                    windows=("mase", "size"),
                    failed=("failed", "sum"))
               .reset_index())
    out: dict[str, dict[str, list[dict]]] = {}
    for horizon in spec.HORIZONS:
        out[horizon] = {}
        sub = grouped[grouped["horizon"] == horizon]
        for series, g in sub.groupby("series"):
            rows = []
            for _, r in g.iterrows():
                name, kind = METHODS.get(r["method"], (r["method"], "model"))
                rows.append({
                    "method": r["method"], "name": name, "kind": kind,
                    "mase": _num(r["mase"], 4), "mae": _num(r["mae"], 1),
                    "coverage": _num(r["coverage"], 4),
                    "peak_error": _num(r["peak_error"], 1),
                    "windows": int(r["windows"]), "failed": int(r["failed"]),
                })
            rows.sort(key=lambda r: (r["mase"] is None, r["mase"] or 0))
            out[horizon][series] = rows
    return out


def paired_tables() -> dict:
    """The 'which differences are real' view: paired skill
    differences from results/scores/paired.csv (written by
    scripts/paired_diffs.py), grouped by horizon and family."""
    path = SCORES_DIR / "paired.csv"
    out: dict[str, dict[str, list[dict]]] = {}
    if not path.exists():
        return out
    paired = pd.read_csv(path)
    for horizon in spec.HORIZONS:
        out[horizon] = {}
        sub_h = paired[paired["horizon"] == horizon]
        for family, sub in sub_h.groupby("family"):
            rows = []
            for _, r in sub.iterrows():
                name = METHODS.get(r["method"], (r["method"], "model"))[0]
                reference = METHODS.get(r["reference"], (r["reference"], "model"))[0]
                rows.append({
                    "method": name, "reference": reference,
                    "diff": _num(r["diff_pct"], 2),
                    "ci_lo": _num(r["ci_lo"], 2), "ci_hi": _num(r["ci_hi"], 2),
                    "verdict": r["verdict"],
                })
            rows.sort(key=lambda x: -(x["diff"] or 0))
            out[horizon][family] = rows
    return out


def main() -> None:
    summary = pd.read_csv(SCORES_DIR / "summary.csv")
    window_scores = pd.read_parquet(SCORES_DIR / "window_scores.parquet")
    series = sorted(window_scores["series"].unique().tolist())
    data = {
        "index_version": spec.INDEX_VERSION,
        "generated": date.today().isoformat(),
        "window_start": spec.WINDOW_START.isoformat(),
        "window_end": spec.WINDOW_END.isoformat(),
        "window_label": (f"{spec.WINDOW_START:%b %Y} – {spec.WINDOW_END:%b %Y}"),
        "issue_days": len(spec.issue_days()),
        "series": series,
        "rows": leaderboard_rows(summary, window_scores),
        "paired": paired_tables(),
        "per_ba": per_ba_tables(window_scores),
        "live": {"status": "starts on publication", "forecasts_made": 0,
                 "forecasts_scored": 0},
    }
    template = (SITE_DIR / "template.html").read_text()
    html = template.replace("__GLI_DATA__", json.dumps(data))
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html)
    for asset in ("kit.css", "kit-theme.js"):
        shutil.copyfile(SITE_DIR / asset, DOCS_DIR / asset)
    n_models = sum(1 for rows in data["rows"].values()
                   for r in rows if r["kind"] == "model" and not r["pending"])
    print(f"wrote {DOCS_DIR / 'index.html'}: {len(data['series'])} series, "
          f"{n_models // 2} models scored, version {data['index_version']}")


if __name__ == "__main__":
    main()

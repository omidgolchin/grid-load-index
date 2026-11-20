"""Draw the README chart from the shipped score summary.

Usage (from the repo root): python scripts/make_chart.py
Reads results/scores/summary.csv; writes results/chart_skill.png.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

S = pd.read_csv(Path("results/scores/summary.csv"))
LABELS = {
    "operator": "Operator forecast", "chronos_2": "Chronos-2", "moirai_2": "Moirai 2.0",
    "toto": "Toto", "tirex": "TiRex", "chronos_bolt": "Chronos-Bolt (base)",
    "timesfm_2_5": "TimesFM 2.5", "moirai_moe": "Moirai-MoE", "sundial": "Sundial",
    "ttm": "Granite TTM r2", "autoarima": "AutoARIMA", "autoets": "AutoETS", "naive": "Naive",
}
KIND = {"operator": "operator", "autoarima": "baseline", "autoets": "baseline", "naive": "baseline"}
COLOR = {"model": "#2a78d6", "baseline": "#8a8985", "operator": "#eb6834"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#dddcd7"
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans", "axes.edgecolor": GRID,
                     "xtick.color": MUTED, "ytick.color": INK})

fig, axes = plt.subplots(1, 2, figsize=(11, 5.4), sharex=True)
for ax, (h, title) in zip(axes, [("day", "Day-ahead (24 h)"), ("week", "Week-ahead (168 h)")]):
    d = S[(S.horizon == h) & S.method.isin(LABELS)].sort_values("skill_pct", ascending=True)
    for i, r in enumerate(d.itertuples()):
        c = COLOR[KIND.get(r.method, "model")]
        ax.errorbar(r.skill_pct, i, xerr=[[r.skill_pct - r.skill_ci_lo], [r.skill_ci_hi - r.skill_pct]],
                    fmt="o", color=c, ecolor=c, elinewidth=1.6, ms=6.5, capsize=0)
    ax.set_yticks(range(len(d)), [LABELS[m] for m in d.method])
    ax.axvline(0, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_title(title, loc="left", fontsize=10.5, color=INK)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Skill vs same hour last week, % (higher is better)", color=MUTED, fontsize=8.5)

handles = [plt.Line2D([], [], marker="o", color=COLOR[k], ls="none", ms=6.5, label=l)
           for k, l in [("model", "Foundation model (zero-shot)"), ("baseline", "Statistical baseline"),
                        ("operator", "Grid operator's own forecast")]]
fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8.5)
fig.suptitle("Grid Load Forecasting Index v2026.11: skill with 95% paired-bootstrap intervals",
             x=0.01, ha="left", fontsize=11.5, color=INK)
fig.tight_layout(rect=(0, 0.06, 1, 0.97))
fig.savefig("results/chart_skill.png", dpi=180, facecolor="white")
print("wrote results/chart_skill.png")

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import style
from .spreads import GAL_PER_BBL, LABELS

FIG_DIR = Path(__file__).resolve().parents[1] / "figures"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _save(fig, name):
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / name)
    plt.close(fig)


def spread_history(sp: pd.DataFrame):
    style.apply()
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    ax = axes[0, 0]
    ax.plot(sp["crack_321"], color=style.SERIES[0], lw=1.2)
    ax.set_title(LABELS["crack_321"])
    ax = axes[0, 1]
    ax.plot(sp["gasoline_crack"], lw=1.2, label="Gasoline (RBOB)", color=style.SERIES[0])
    ax.plot(sp["distillate_crack"], lw=1.2, label="Distillate (HO)", color=style.SERIES[1])
    ax.set_title("Product cracks vs WTI ($/bbl)")
    ax.legend(loc="upper left")
    ax = axes[1, 0]
    ax.plot(sp["brent_wti"], color=style.SERIES[0], lw=1.2)
    ax.axhline(0, color=style.AXIS, lw=0.8)
    ax.set_title(LABELS["brent_wti"])
    ax = axes[1, 1]
    ax.plot(sp["board_crush"], color=style.SERIES[0], lw=1.2)
    ax.set_title(LABELS["board_crush"])
    fig.suptitle("Processing margins and the Brent-WTI spread, front-month futures", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "spreads.png")


def seasonality(profiles: dict[str, pd.DataFrame]):
    style.apply()
    fig, axes = plt.subplots(1, len(profiles), figsize=(6 * len(profiles), 4), sharey=False)
    for ax, (name, p) in zip(axes, profiles.items()):
        x = range(1, 13)
        yr_cols = [c for c in p.columns if c.isdigit()]
        ax.fill_between(x, p["p10"], p["p90"], color=style.SERIES[0], alpha=0.15, lw=0, label="10-90% of past years")
        ax.plot(x, p["mean"], color=style.SERIES[0], label="Average of past years")
        ax.plot(x, p[yr_cols[0]], color=style.MUTED, lw=1.4, label=yr_cols[0])
        ax.plot(x, p[yr_cols[1]], color=style.SERIES[1], lw=2.2, marker="o", ms=4, label=yr_cols[1])
        ax.set_xticks(list(x)); ax.set_xticklabels(MONTHS)
        ax.set_title(LABELS[name] + ", monthly average")
        ax.legend(loc="upper left")
    fig.tight_layout()
    _save(fig, "seasonality.png")


def curves(curves: dict[str, pd.Series], fwd_cracks: pd.DataFrame | None):
    style.apply()
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))

    def lab(idx):
        return [d.strftime("%b\n%y") if (i == 0 or d.month == 1) else d.strftime("%b") for i, d in enumerate(idx)]

    ax = axes[0, 0]
    for i, r in enumerate(["CL", "BZ"]):
        if r in curves:
            ax.plot(curves[r].index, curves[r].values, marker="o", ms=4, color=style.SERIES[i], label={"CL": "WTI", "BZ": "Brent"}[r])
    ax.set_title("Crude curves ($/bbl)"); ax.legend()
    ax = axes[0, 1]
    for i, r in enumerate(["RB", "HO"]):
        if r in curves:
            ax.plot(curves[r].index, curves[r].values * GAL_PER_BBL, marker="o", ms=4, color=style.SERIES[i], label={"RB": "RBOB gasoline", "HO": "ULSD (HO)"}[r])
    ax.set_title("Product curves ($/bbl)"); ax.legend()
    ax = axes[1, 0]
    if "NG" in curves:
        ax.plot(curves["NG"].index, curves["NG"].values, marker="o", ms=4, color=style.SERIES[0])
    ax.set_title("Henry Hub natural gas curve ($/MMBtu)")
    ax = axes[1, 1]
    if fwd_cracks is not None and len(fwd_cracks):
        ax.plot(fwd_cracks.index, fwd_cracks["gasoline_crack"], marker="o", ms=4, color=style.SERIES[0], label="Gasoline")
        ax.plot(fwd_cracks.index, fwd_cracks["distillate_crack"], marker="o", ms=4, color=style.SERIES[1], label="Distillate")
        ax.plot(fwd_cracks.index, fwd_cracks["crack_321"], marker="o", ms=4, color=style.SERIES[2], label="3-2-1")
        ax.legend()
    ax.set_title("Forward cracks by delivery month ($/bbl)")
    for ax in axes.ravel():
        ax.tick_params(axis="x", rotation=0)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))
        ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(interval=3))
    asof = pd.Timestamp.today().strftime("%d %b %Y")
    fig.suptitle(f"Forward curves from listed contract months, snapshot {asof}", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.tight_layout()
    _save(fig, "curves.png")


def backtest(results: dict[str, pd.Series]):
    style.apply()
    fig, axes = plt.subplots(1, len(results), figsize=(6 * len(results), 3.8))
    for ax, (name, daily) in zip(axes, results.items()):
        eq = daily.cumsum()
        ax.plot(eq, color=style.SERIES[0], lw=1.5)
        ax.axhline(0, color=style.AXIS, lw=0.8)
        unit = "$/bu" if "crush" in name else "$/bbl"
        ax.set_title(f"Fading 2-sigma extremes: {LABELS[name].split(' (')[0]}, cumulative {unit}")
    fig.tight_layout()
    _save(fig, "backtest.png")

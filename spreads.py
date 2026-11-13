"""
Commodity Spread Tracker
========================
Tracks the three classic refining/processing spreads used by physical traders:
  - Crack spread   : crude oil â†’ gasoline + heating oil  (energy)
  - Crush spread   : soybeans â†’ soybean meal + soybean oil  (agri)
  - Spark spread   : natural gas â†’ electricity  (power, proxy only)

Also detects contango / backwardation on front-month WTI futures.

Data: Yahoo Finance (free, no API key needed)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")


# â”€â”€ tickers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TICKERS = {
    "CL=F":  "WTI Crude Oil ($/bbl)",
    "RB=F":  "RBOB Gasoline ($/gal)",
    "HO=F":  "Heating Oil ($/gal)",
    "NG=F":  "Natural Gas ($/MMBtu)",
    "ZS=F":  "Soybeans (Â¢/bu)",
    "ZM=F":  "Soybean Meal ($/ton)",
    "ZL=F":  "Soybean Oil (Â¢/lb)",
}

LOOKBACK_DAYS = 365 * 3   # 3 years of history
ZSCORE_WINDOW = 60         # rolling window for z-score (trading days)


def fetch_prices(start: str, end: str) -> pd.DataFrame:
    """Download adjusted close prices for all commodity tickers."""
    raw = yf.download(list(TICKERS.keys()), start=start, end=end, auto_adjust=True, progress=False)
    prices = raw["Close"].copy()
    prices.columns = [TICKERS[c] for c in prices.columns]
    prices.dropna(how="all", inplace=True)
    return prices


def compute_crack_spread(prices: pd.DataFrame) -> pd.Series:
    """
    3-2-1 crack spread (most common refinery proxy):
      3 barrels crude â†’ 2 barrels gasoline + 1 barrel heating oil
      All converted to $/bbl.
      Gasoline & heating oil are priced per gallon â†’ Ã— 42 (gal/bbl)
    """
    cl  = prices["WTI Crude Oil ($/bbl)"]
    rb  = prices["RBOB Gasoline ($/gal)"] * 42
    ho  = prices["Heating Oil ($/gal)"]  * 42
    spread = (2 * rb + 1 * ho - 3 * cl) / 3
    spread.name = "3-2-1 Crack Spread ($/bbl)"
    return spread


def compute_crush_spread(prices: pd.DataFrame) -> pd.Series:
    """
    Soybean crush spread:
      1 bushel soybeans â†’ 11 lbs soybean oil + 44 lbs soybean meal
      Soybeans in Â¢/bu â†’ Ã· 100 for $
      Soybean oil in Â¢/lb â†’ Ã— 11 lbs â†’ Ã· 100 for $
      Soybean meal in $/ton â†’ Ã— (44/2000) for $/bu equivalent
    """
    sb  = prices["Soybeans (Â¢/bu)"]     / 100          # $/bu
    sbo = prices["Soybean Oil (Â¢/lb)"]  / 100 * 11     # $/bu of oil
    sbm = prices["Soybean Meal ($/ton)"] * (44 / 2000) # $/bu of meal
    spread = sbo + sbm - sb
    spread.name = "Crush Spread ($/bu)"
    return spread


def compute_spark_spread(prices: pd.DataFrame, heat_rate: float = 7.0) -> pd.Series:
    """
    Spark spread proxy (gas-fired power plant):
      spark spread = power price âˆ’ (gas price Ã— heat rate)
    We use a fixed $45/MWh proxy for power (no free live feed).
    Heat rate default = 7 MMBtu/MWh (efficient CCGT).
    """
    ng = prices["Natural Gas ($/MMBtu)"]
    power_proxy = 45.0  # $/MWh â€” replace with real power data if available
    spread = power_proxy - ng * heat_rate
    spread.name = "Spark Spread ($/MWh, proxy)"
    return spread


def rolling_zscore(series: pd.Series, window: int = ZSCORE_WINDOW) -> pd.Series:
    """Z-score of a spread relative to its recent rolling mean/std."""
    mu  = series.rolling(window).mean()
    sig = series.rolling(window).std()
    return ((series - mu) / sig).rename(f"{series.name} Z-score")


def classify_signal(z: float) -> str:
    if   z >  2.0: return "â¬†  HISTORICALLY WIDE  â€” spread elevated, potential mean-reversion short"
    elif z >  1.0: return "â†—  Above average"
    elif z < -2.0: return "â¬‡  HISTORICALLY NARROW â€” spread compressed, potential mean-reversion long"
    elif z < -1.0: return "â†˜  Below average"
    else:          return "â†’  Normal range"


def detect_curve_structure(prices: pd.DataFrame) -> str:
    """
    Rough contango/backwardation proxy using front-month WTI.
    A proper implementation needs 2nd-month futures (CL2=F),
    but yfinance only carries front-month reliably.
    We use the 20-day rolling trend of the front month as a proxy.
    """
    cl = prices["WTI Crude Oil ($/bbl)"].dropna()
    if len(cl) < 25:
        return "insufficient data"
    recent_slope = (cl.iloc[-1] - cl.iloc[-20]) / cl.iloc[-20] * 100
    if recent_slope > 1.5:
        return f"BACKWARDATION proxy (front-month up {recent_slope:.1f}% over 20d â€” spot premium)"
    elif recent_slope < -1.5:
        return f"CONTANGO proxy (front-month down {recent_slope:.1f}% over 20d â€” carry cost)"
    else:
        return f"FLAT curve proxy ({recent_slope:+.1f}% over 20d)"


def print_summary(spreads: dict, zscores: dict, curve: str):
    print("\n" + "=" * 65)
    print("  COMMODITY SPREAD TRACKER  â€”  " + datetime.today().strftime("%Y-%m-%d"))
    print("=" * 65)

    for name, s in spreads.items():
        last_val  = s.dropna().iloc[-1]
        last_z    = zscores[name].dropna().iloc[-1]
        signal    = classify_signal(last_z)
        unit      = s.name.split("(")[1].rstrip(")")
        print(f"\n{'â”€'*55}")
        print(f"  {s.name}")
        print(f"  Current : {last_val:+.3f} {unit}")
        print(f"  Z-score : {last_z:+.2f}  ({ZSCORE_WINDOW}d window)")
        print(f"  Signal  : {signal}")

    print(f"\n{'â”€'*55}")
    print(f"  WTI CURVE STRUCTURE")
    print(f"  {curve}")
    print("=" * 65 + "\n")


def plot_spreads(spreads: dict, zscores: dict, save_path: str = "outputs/spreads.png"):
    fig, axes = plt.subplots(len(spreads), 2, figsize=(16, 4 * len(spreads)),
                             facecolor="#0d1117")
    fig.suptitle("Commodity Spread Tracker", fontsize=16, color="white", y=1.01)

    colors = ["#58a6ff", "#3fb950", "#f78166"]

    for i, (name, s) in enumerate(spreads.items()):
        ax_l = axes[i][0]
        ax_r = axes[i][1]
        z    = zscores[name]
        col  = colors[i % len(colors)]

        # left: spread level
        ax_l.plot(s.index, s.values, color=col, linewidth=1.2)
        ax_l.axhline(s.rolling(ZSCORE_WINDOW).mean().iloc[-1], color="white",
                     linestyle="--", linewidth=0.7, alpha=0.5, label=f"{ZSCORE_WINDOW}d mean")
        ax_l.set_title(s.name, color="white", fontsize=10)
        ax_l.set_facecolor("#161b22")
        ax_l.tick_params(colors="gray")
        ax_l.spines[:].set_color("#30363d")
        ax_l.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax_l.legend(fontsize=8, labelcolor="gray")

        # right: z-score
        ax_r.plot(z.index, z.values, color=col, linewidth=1.0, alpha=0.85)
        ax_r.axhline(0,    color="white",  linewidth=0.6, linestyle="-")
        ax_r.axhline(2,    color="#f85149", linewidth=0.8, linestyle="--", alpha=0.7, label="+2Ïƒ")
        ax_r.axhline(-2,   color="#f85149", linewidth=0.8, linestyle="--", alpha=0.7, label="-2Ïƒ")
        ax_r.fill_between(z.index, z.values, 0,
                          where=(z > 2),  alpha=0.25, color="#f85149")
        ax_r.fill_between(z.index, z.values, 0,
                          where=(z < -2), alpha=0.25, color="#f85149")
        ax_r.set_title(f"{s.name.split('(')[0].strip()} â€” Z-score ({ZSCORE_WINDOW}d)", color="white", fontsize=10)
        ax_r.set_facecolor("#161b22")
        ax_r.tick_params(colors="gray")
        ax_r.spines[:].set_color("#30363d")
        ax_r.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax_r.legend(fontsize=8, labelcolor="gray")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"Chart saved â†’ {save_path}")


def run():
    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    print(f"Fetching commodity prices {start} â†’ {end}â€¦")
    prices = fetch_prices(start, end)

    spreads = {
        "crack":  compute_crack_spread(prices),
        "crush":  compute_crush_spread(prices),
        "spark":  compute_spark_spread(prices),
    }

    zscores = {k: rolling_zscore(v) for k, v in spreads.items()}
    curve   = detect_curve_structure(prices)

    print_summary(spreads, zscores, curve)
    plot_spreads(spreads, zscores)

    # save csv
    df_out = pd.concat(list(spreads.values()) + list(zscores.values()), axis=1)
    df_out.to_csv("outputs/spread_data.csv")
    print("Data saved â†’ outputs/spread_data.csv")


if __name__ == "__main__":
    run()

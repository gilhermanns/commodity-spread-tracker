"""
Spread Mean-Reversion Backtest
==============================
Simple long/short strategy: go long (short) the spread when z-score
crosses below -2 (above +2) and exit at mean reversion to 0.

This is a pure research / idea-generation tool.
No transaction costs, slippage or margin modelling included â€” add those
before trading anything real.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings("ignore")

from spreads import fetch_prices, compute_crack_spread, compute_crush_spread, rolling_zscore, ZSCORE_WINDOW

ENTRY_Z  =  2.0   # enter when |z| > this
EXIT_Z   =  0.3   # exit when |z| < this (back to mean)
LOOKBACK = 365 * 3


def backtest_spread(spread: pd.Series, entry_z: float = ENTRY_Z, exit_z: float = EXIT_Z) -> pd.DataFrame:
    z = rolling_zscore(spread).dropna()
    s = spread.reindex(z.index)

    position  = 0    # +1 long spread, -1 short spread, 0 flat
    trades    = []
    entry_val = None
    entry_dt  = None

    for dt in z.index:
        z_val = z.loc[dt]
        s_val = s.loc[dt]

        if position == 0:
            if z_val < -entry_z:
                position  = 1
                entry_val = s_val
                entry_dt  = dt
            elif z_val > entry_z:
                position  = -1
                entry_val = s_val
                entry_dt  = dt
        else:
            if abs(z_val) < exit_z:
                pnl = (s_val - entry_val) * position
                trades.append({
                    "entry_dt":  entry_dt,
                    "exit_dt":   dt,
                    "direction": "LONG" if position == 1 else "SHORT",
                    "entry_val": entry_val,
                    "exit_val":  s_val,
                    "pnl":       pnl,
                    "hold_days": (dt - entry_dt).days,
                })
                position  = 0
                entry_val = None
                entry_dt  = None

    df = pd.DataFrame(trades)
    if df.empty:
        return df

    df["cum_pnl"]   = df["pnl"].cumsum()
    df["hit_rate"]  = (df["pnl"] > 0).expanding().mean()
    return df


def summarise(df: pd.DataFrame, name: str):
    if df.empty:
        print(f"\n{name}: no completed trades in sample.")
        return

    wins   = (df["pnl"] > 0).sum()
    losses = (df["pnl"] <= 0).sum()
    total  = len(df)

    print(f"\n{'='*55}")
    print(f"  BACKTEST SUMMARY â€” {name}")
    print(f"{'='*55}")
    print(f"  Trades         : {total}")
    print(f"  Win rate       : {wins/total*100:.1f}%  ({wins}W / {losses}L)")
    print(f"  Avg PnL/trade  : {df['pnl'].mean():+.4f}")
    print(f"  Avg hold (days): {df['hold_days'].mean():.0f}")
    print(f"  Total PnL      : {df['pnl'].sum():+.4f}")
    print(f"  Max winner     : {df['pnl'].max():+.4f}")
    print(f"  Max loser      : {df['pnl'].min():+.4f}")
    sharpe = df["pnl"].mean() / df["pnl"].std() * np.sqrt(total) if df["pnl"].std() > 0 else 0
    print(f"  Trade Sharpe   : {sharpe:.2f}  (per-trade, not annualised)")
    print(f"{'='*55}")


def plot_backtest(df: pd.DataFrame, spread: pd.Series, name: str, save_path: str):
    if df.empty:
        return

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), facecolor="#0d1117")
    fig.suptitle(f"Mean-Reversion Backtest â€” {name}", color="white", fontsize=13)

    ax1, ax2 = axes

    # spread + trade markers
    z = rolling_zscore(spread).dropna()
    ax1.plot(spread.index, spread.values, color="#58a6ff", linewidth=1.0, label="Spread")
    for _, row in df.iterrows():
        col = "#3fb950" if row["pnl"] > 0 else "#f85149"
        ax1.axvspan(row["entry_dt"], row["exit_dt"], alpha=0.15, color=col)
    ax1.set_title("Spread Level + Trades (green=win, red=loss)", color="white", fontsize=10)
    ax1.set_facecolor("#161b22"); ax1.tick_params(colors="gray"); ax1.spines[:].set_color("#30363d")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    # cumulative pnl
    ax2.plot(df["exit_dt"], df["cum_pnl"], color="#f0e68c", linewidth=1.5, marker="o", markersize=3)
    ax2.axhline(0, color="white", linewidth=0.5)
    ax2.fill_between(df["exit_dt"], df["cum_pnl"], 0,
                     where=(df["cum_pnl"] >= 0), alpha=0.2, color="#3fb950")
    ax2.fill_between(df["exit_dt"], df["cum_pnl"], 0,
                     where=(df["cum_pnl"] < 0),  alpha=0.2, color="#f85149")
    ax2.set_title("Cumulative PnL (spread units, no costs)", color="white", fontsize=10)
    ax2.set_facecolor("#161b22"); ax2.tick_params(colors="gray"); ax2.spines[:].set_color("#30363d")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    print(f"Backtest chart saved â†’ {save_path}")


def run():
    from datetime import datetime, timedelta
    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=LOOKBACK)).strftime("%Y-%m-%d")

    print(f"Fetching data {start} â†’ {end}â€¦")
    prices = fetch_prices(start, end)

    crack = compute_crack_spread(prices)
    crush = compute_crush_spread(prices)

    for spread, label, path in [
        (crack, "3-2-1 Crack Spread", "outputs/backtest_crack.png"),
        (crush, "Soybean Crush Spread", "outputs/backtest_crush.png"),
    ]:
        df = backtest_spread(spread)
        summarise(df, label)
        plot_backtest(df, spread, label, path)
        if not df.empty:
            df.to_csv(f"outputs/trades_{label.split()[0].lower()}.csv", index=False)


if __name__ == "__main__":
    run()

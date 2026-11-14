"""Does fading an extreme spread pay? A deliberately plain test.

Rules are fixed up front, nothing is fitted:
  enter   when |z| crosses the entry threshold (signal on day t, position from t+1)
  exit    when z is back inside the exit band, or after max_hold days
  pnl     in spread units ($/bbl or $/bu), one unit of the spread per trade

What this is not: a tradeable P&L. The inputs are continuous front-month series,
so roll days leak into the spread, and there is no margin or liquidity model.
Read it as 'is there mean reversion worth a closer look', nothing more.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def run(spread: pd.Series, z: pd.Series, entry: float = 2.0, exit_: float = 0.5,
        max_hold: int = 60, cost: float = 0.0) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.concat([spread.rename("s"), z.rename("z")], axis=1).dropna()
    pos = np.zeros(len(df))
    trades, cur, held = [], 0, 0
    entry_i = None
    zv, sv = df["z"].to_numpy(), df["s"].to_numpy()
    for i in range(len(df) - 1):
        if cur == 0:
            if zv[i] > entry:
                cur = -1
            elif zv[i] < -entry:
                cur = 1
            if cur != 0:
                entry_i, held = i + 1, 0
        else:
            held += 1
            if abs(zv[i]) < exit_ or held >= max_hold:
                trades.append({
                    "entry": df.index[entry_i], "exit": df.index[i + 1], "side": cur,
                    "entry_spread": sv[entry_i], "exit_spread": sv[i + 1],
                    "pnl": cur * (sv[i + 1] - sv[entry_i]) - cost, "days": i + 1 - entry_i,
                    "exit_reason": "reverted" if abs(zv[i]) < exit_ else "time stop",
                })
                cur = 0
        pos[i + 1] = cur
    if cur != 0:  # still open on the last bar: mark it there so trades and daily P&L agree
        last = len(df) - 1
        trades.append({
            "entry": df.index[entry_i], "exit": df.index[last], "side": cur,
            "entry_spread": sv[entry_i], "exit_spread": sv[last],
            "pnl": cur * (sv[last] - sv[entry_i]) - cost, "days": last - entry_i,
            "exit_reason": "open at end",
        })
    # position held over day i earns the change from i-1 to i
    daily = pd.Series(pos, index=df.index).shift(1).fillna(0) * df["s"].diff().fillna(0)
    return pd.DataFrame(trades), daily


def summary(trades: pd.DataFrame, daily: pd.Series) -> dict:
    if trades.empty:
        return {"trades": 0}
    eq = daily.cumsum()
    dd = (eq - eq.cummax()).min()
    active = daily[daily != 0]
    return {
        "trades": len(trades),
        "hit_rate_pct": (trades["pnl"] > 0).mean() * 100,
        "avg_pnl": trades["pnl"].mean(),
        "median_days": trades["days"].median(),
        "time_stops_pct": (trades["exit_reason"] == "time stop").mean() * 100,
        "total_pnl": trades["pnl"].sum(),
        "max_drawdown": dd,
        "worst_trade": trades["pnl"].min(),
        "sharpe_in_market": active.mean() / active.std() * np.sqrt(252) if len(active) > 20 else np.nan,
    }


def sensitivity(spread: pd.Series, zfunc, entries=(1.5, 2.0, 2.5), windows=(126, 252, 504), **kw) -> pd.DataFrame:
    """Total P&L across a small grid. If only one cell works, it doesn't work."""
    rows = []
    for w in windows:
        z = zfunc(spread, w)
        for e in entries:
            t, d = run(spread, z, entry=e, **kw)
            s = summary(t, d)
            rows.append({"window": w, "entry_z": e, "trades": s.get("trades", 0),
                         "total_pnl": s.get("total_pnl", 0.0), "hit_rate_pct": s.get("hit_rate_pct", np.nan)})
    return pd.DataFrame(rows)

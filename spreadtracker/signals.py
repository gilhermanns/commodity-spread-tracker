"""Two ways of asking 'is this spread unusual?'.

rolling_z   - against its own last year. Simple, but a gasoline crack is *supposed*
              to be high in May and low in December, so it flags the calendar.
seasonal_z  - against the same calendar month in earlier years only. This is the
              one that matters for anything with a driving or heating season.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_z(s: pd.Series, window: int = 252) -> pd.Series:
    mu = s.rolling(window, min_periods=window // 2).mean()
    sd = s.rolling(window, min_periods=window // 2).std()
    return (s - mu) / sd


def seasonal_z(s: pd.Series, min_years: int = 4) -> pd.Series:
    """z-score vs. the same calendar month in *previous* years (no look-ahead)."""
    s = s.dropna()
    out = pd.Series(np.nan, index=s.index)
    years = s.index.year
    for m in range(1, 13):
        in_month = s.index.month == m
        for y in np.unique(years[in_month]):
            hist = s[in_month & (years < y)]
            if hist.index.year.nunique() < min_years:
                continue
            cur = in_month & (years == y)
            out[cur] = (s[cur] - hist.mean()) / hist.std()
    return out


def seasonal_profile(s: pd.Series) -> pd.DataFrame:
    """Average level by calendar month, plus the current and previous year for overlay."""
    m = s.groupby([s.index.year, s.index.month]).mean().unstack(0)
    this_year = m.columns.max()
    hist = m.drop(columns=[this_year])
    return pd.DataFrame({
        "mean": hist.mean(axis=1),
        "p10": hist.quantile(0.10, axis=1),
        "p90": hist.quantile(0.90, axis=1),
        str(this_year - 1): m.get(this_year - 1),
        str(this_year): m[this_year],
    })


def percentile_rank(s: pd.Series, lookback: int = 252 * 5) -> float:
    """Where the latest value sits in its own recent history, 0-100."""
    w = s.dropna().iloc[-lookback:]
    return float((w <= w.iloc[-1]).mean() * 100)

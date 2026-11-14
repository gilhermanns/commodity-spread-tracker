"""Price loading. Everything comes from Yahoo Finance, cached to data/ so reruns are quick."""
from __future__ import annotations

import time
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

import logging

warnings.filterwarnings("ignore")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)  # expired contract months are expected

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# continuous front-month series
FRONT = {
    "CL=F": "wti",        # $/bbl
    "BZ=F": "brent",      # $/bbl
    "RB=F": "rbob",       # $/gal
    "HO=F": "ho",         # $/gal (ULSD, still called heating oil)
    "ZS=F": "soybeans",   # cents/bu
    "ZM=F": "soymeal",    # $/short ton
    "ZL=F": "soyoil",     # cents/lb
}

MONTH_CODES = "FGHJKMNQUVXZ"  # Jan..Dec
EXCHANGE = {"CL": "NYM", "BZ": "NYM", "RB": "NYM", "HO": "NYM", "NG": "NYM", "HG": "CMX"}


def load_front(start: str = "2008-01-01", max_age_hours: float = 12) -> pd.DataFrame:
    """Daily settlement-ish closes of the front-month contracts."""
    DATA_DIR.mkdir(exist_ok=True)
    cache = DATA_DIR / "front_month.csv"
    if cache.exists() and time.time() - cache.stat().st_mtime < max_age_hours * 3600:
        return pd.read_csv(cache, index_col=0, parse_dates=True)

    raw = yf.download(list(FRONT), start=start, auto_adjust=True, progress=False, threads=False)["Close"]
    px = raw.rename(columns=FRONT)[list(FRONT.values())]
    px.index = pd.to_datetime(px.index).tz_localize(None)
    # WTI printed negative on 20 Apr 2020. That is a real price, but it wrecks any
    # spread statistic for a day, so the single print is masked rather than "fixed".
    px.loc[px["wti"] <= 0, "wti"] = float("nan")
    px = px.dropna(how="all")
    px.to_csv(cache)
    return px


def contract_ticker(root: str, year: int, month: int) -> str:
    return f"{root}{MONTH_CODES[month - 1]}{year % 100:02d}.{EXCHANGE[root]}"


def load_curve(root: str, n_months: int = 14, asof: pd.Timestamp | None = None) -> pd.Series:
    """Live forward curve: last close of each listed contract month.

    Yahoo only serves contracts that are still trading, so this is a snapshot,
    not a history. Index = delivery month (month start), values = price.
    """
    asof = asof or pd.Timestamp.today().normalize()
    months = pd.period_range(asof.to_period("M"), periods=n_months + 2, freq="M")
    tickers = {contract_ticker(root, p.year, p.month): p.to_timestamp() for p in months}
    raw = yf.download(list(tickers), period="5d", auto_adjust=True, progress=False, threads=False)["Close"]
    last = raw.ffill().iloc[-1].dropna()
    curve = pd.Series({tickers[t]: float(v) for t, v in last.items()}).sort_index()
    curve.name = root
    return curve.iloc[:n_months]

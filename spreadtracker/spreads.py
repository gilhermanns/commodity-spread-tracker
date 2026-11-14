"""Spread definitions. Each function documents the unit conversion, because that is
where these calculations usually go wrong."""
from __future__ import annotations

import pandas as pd

GAL_PER_BBL = 42.0
# CBOT board crush: one 60 lb bushel yields roughly 44 lb of 48% meal and 11 lb of oil.
MEAL_TON_PER_BU = 44.0 / 2000.0   # meal is quoted per short ton (2000 lb) -> 0.022
OIL_LB_PER_BU = 11.0


def gasoline_crack(rbob_gal, crude_bbl):
    """RBOB minus crude, $/bbl."""
    return rbob_gal * GAL_PER_BBL - crude_bbl


def distillate_crack(ho_gal, crude_bbl):
    """ULSD (HO) minus crude, $/bbl."""
    return ho_gal * GAL_PER_BBL - crude_bbl


def crack_321(rbob_gal, ho_gal, crude_bbl):
    """3-2-1: three barrels of crude into two of gasoline and one of distillate, $/bbl of crude."""
    return (2 * rbob_gal * GAL_PER_BBL + ho_gal * GAL_PER_BBL - 3 * crude_bbl) / 3


def board_crush(meal_ton, oil_cents_lb, beans_cents_bu):
    """Gross soybean processing margin, $/bu."""
    return meal_ton * MEAL_TON_PER_BU + oil_cents_lb * OIL_LB_PER_BU / 100 - beans_cents_bu / 100


def oil_share(meal_ton, oil_cents_lb):
    """Share of crush revenue coming from oil (the renewable-diesel story in one number)."""
    oil = oil_cents_lb * OIL_LB_PER_BU / 100
    meal = meal_ton * MEAL_TON_PER_BU
    return oil / (oil + meal)


def all_spreads(px: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=px.index)
    out["crack_321"] = crack_321(px["rbob"], px["ho"], px["wti"])
    out["gasoline_crack"] = gasoline_crack(px["rbob"], px["wti"])
    out["distillate_crack"] = distillate_crack(px["ho"], px["wti"])
    out["brent_wti"] = px["brent"] - px["wti"]
    out["board_crush"] = board_crush(px["soymeal"], px["soyoil"], px["soybeans"])
    out["oil_share"] = oil_share(px["soymeal"], px["soyoil"])
    return out.dropna(how="all")


LABELS = {
    "crack_321": "3-2-1 crack ($/bbl)",
    "gasoline_crack": "Gasoline crack, RBOB-WTI ($/bbl)",
    "distillate_crack": "Distillate crack, HO-WTI ($/bbl)",
    "brent_wti": "Brent-WTI ($/bbl)",
    "board_crush": "Soybean board crush ($/bu)",
    "oil_share": "Soyoil share of crush revenue",
}

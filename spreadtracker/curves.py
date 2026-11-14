"""Forward-curve shape from actual contract months."""
from __future__ import annotations

import pandas as pd

from . import spreads
from .data import load_curve


SEASONAL = {"NG", "RB"}  # winter gas / summer gasoline premia dominate the curve shape


def curve_metrics(curve: pd.Series) -> dict:
    """Time spreads and the roll yield a long position earns (+) or pays (-).

    For gas and gasoline the front spread mostly reflects the season you are
    rolling into, so the label says so instead of pretending M1-M2 measures tightness.
    """
    m1, m2 = curve.iloc[0], curve.iloc[1]
    gap = (curve.index[1].to_period("M") - curve.index[0].to_period("M")).n
    far = curve.iloc[min(12, len(curve) - 1)]
    far_gap = (curve.index[min(12, len(curve) - 1)].to_period("M") - curve.index[0].to_period("M")).n
    return {
        "front": curve.index[0].strftime("%b-%y"),
        "m1": m1,
        "m1_m2": m1 - m2,
        "m1_far": m1 - far,
        "far_months": far_gap,
        "roll_yield_ann_pct": (m1 / m2 - 1) * 12 / gap * 100,
        "structure": ("backwardation" if m1 > far else "contango") + (" (seasonal curve)" if curve.name in SEASONAL else ""),
    }


def forward_cracks(cl: pd.Series, rb: pd.Series, ho: pd.Series) -> pd.DataFrame:
    """Crack spreads by delivery month, with product and crude months lined up.

    The front-month continuous series can't do this properly: CL expires around
    the 20th of the month before delivery, RB and HO on the last business day,
    so for the last third of every month 'front crude' and 'front gasoline' are
    different delivery months.
    """
    df = pd.concat([cl.rename("cl"), rb.rename("rb"), ho.rename("ho")], axis=1).dropna()
    return pd.DataFrame({
        "gasoline_crack": spreads.gasoline_crack(df["rb"], df["cl"]),
        "distillate_crack": spreads.distillate_crack(df["ho"], df["cl"]),
        "crack_321": spreads.crack_321(df["rb"], df["ho"], df["cl"]),
    })


def snapshot(roots=("CL", "BZ", "RB", "HO", "NG", "HG")) -> dict[str, pd.Series]:
    out = {}
    for r in roots:
        try:
            c = load_curve(r)
            if len(c) >= 3:
                out[r] = c
        except Exception as e:  # one missing chain shouldn't kill the report
            print(f"  curve {r} unavailable: {e}")
    return out

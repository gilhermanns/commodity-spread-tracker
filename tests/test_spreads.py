import numpy as np
import pandas as pd

from spreadtracker import backtest, signals, spreads


def test_crack_units():
    # $2.50/gal gasoline, $3.00/gal diesel, $80 crude
    assert spreads.gasoline_crack(2.5, 80) == 2.5 * 42 - 80
    assert spreads.distillate_crack(3.0, 80) == 46.0
    assert np.isclose(spreads.crack_321(2.5, 3.0, 80), (2 * 105 + 126 - 240) / 3)


def test_board_crush():
    # meal $300/ton, oil 50 c/lb, beans 1200 c/bu -> 6.60 + 5.50 - 12.00
    assert np.isclose(spreads.board_crush(300, 50, 1200), 0.10)
    assert np.isclose(spreads.oil_share(300, 50), 5.5 / 12.1)


def test_seasonal_z_has_no_lookahead():
    idx = pd.bdate_range("2010-01-01", "2020-12-31")
    rng = np.random.default_rng(0)
    s = pd.Series(10 + 5 * np.sin(2 * np.pi * idx.dayofyear / 365) + rng.normal(0, 1, len(idx)), index=idx)
    z1 = signals.seasonal_z(s)
    s2 = s.copy(); s2.loc["2020"] += 100            # change the future
    z2 = signals.seasonal_z(s2)
    pd.testing.assert_series_equal(z1.loc[:"2019"], z2.loc[:"2019"])
    assert z1.loc["2010":"2013"].isna().all()       # needs 4 prior years


def test_backtest_pnl_adds_up():
    idx = pd.bdate_range("2015-01-01", periods=1500)
    rng = np.random.default_rng(1)
    x = np.zeros(len(idx))
    for i in range(1, len(idx)):                    # mean-reverting AR(1)
        x[i] = 0.97 * x[i - 1] + rng.normal()
    s = pd.Series(20 + x, index=idx)
    trades, daily = backtest.run(s, signals.rolling_z(s, 252), cost=0.0)
    assert len(trades) > 0
    assert np.isclose(trades["pnl"].sum(), daily.sum())
    assert (trades["exit"] > trades["entry"]).all()

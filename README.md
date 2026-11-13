# Commodity Spread Tracker

Real-time monitor and mean-reversion backtester for the three classic commodity processing spreads used by physical traders and energy desks.

---

## Spreads Covered

| Spread | Formula | Market |
|--------|---------|--------|
| **3-2-1 Crack** | (2 Ã— gasoline + 1 Ã— heating oil) âˆ’ 3 Ã— crude | Energy / Refining |
| **Crush** | soybean oil + soybean meal âˆ’ soybeans | Agriculture |
| **Spark** | power price âˆ’ (gas price Ã— heat rate) | Power / Gas |

The crack spread is the primary margin indicator for oil refiners. The crush spread drives crush capacity decisions for soy processors. The spark spread determines gas-fired power plant profitability.

---

## What It Does

**`spreads.py`** â€” live monitor
- Downloads 3 years of front-month futures prices via Yahoo Finance (no API key needed)
- Computes all three spreads with correct unit conversions (galâ†’bbl, Â¢/buâ†’$/bu, etc.)
- Calculates 60-day rolling z-scores to flag historically wide or narrow levels
- Detects crude oil curve structure (contango vs backwardation proxy)
- Outputs a signal table and saves a chart + CSV

**`backtest.py`** â€” mean-reversion strategy
- Entry: z-score crosses Â±2Ïƒ
- Exit: z-score reverts to Â±0.3Ïƒ
- Reports win rate, avg PnL per trade, hold time, trade-level Sharpe
- Saves per-trade logs as CSV

---

## Quickstart

```bash
pip install -r requirements.txt

# live spread monitor
python spreads.py

# mean-reversion backtest
python backtest.py
```

Outputs land in `outputs/`:
- `spreads.png` â€” spread levels + z-scores
- `spread_data.csv` â€” full time series
- `backtest_crack.png` / `backtest_crush.png` â€” trade visualisations
- `trades_crack.csv` / `trades_crush.csv` â€” per-trade logs

---

## Sample Output

```
=================================================================
  COMMODITY SPREAD TRACKER  â€”  2026-11-13
=================================================================

  3-2-1 Crack Spread ($/bbl)
  Current : +18.420 $/bbl
  Z-score : +1.73  (60d window)
  Signal  : â†—  Above average

  Crush Spread ($/bu)
  Current : +1.082 $/bu
  Z-score : -2.31  (60d window)
  Signal  : â¬‡  HISTORICALLY NARROW â€” spread compressed, potential mean-reversion long

  WTI CURVE STRUCTURE
  CONTANGO proxy (front-month down -2.1% over 20d â€” carry cost)
=================================================================
```

---

## Methodology Notes

- **Unit conversions**: gasoline and heating oil are quoted in $/gallon on NYMEX â€” multiplied by 42 (gallons per barrel) to get $/bbl for the crack spread calculation
- **Crush spread**: 1 bushel soybeans yields approximately 11 lbs of soybean oil and 44 lbs of soybean meal (industry standard yield assumption)
- **Spark spread**: uses a fixed $45/MWh power proxy as EIA hourly power prices are not freely available. Replace with CAISO/PJM API data for a live implementation
- **Z-score window**: 60 trading days (~3 months) balances responsiveness vs noise. Adjust `ZSCORE_WINDOW` in `spreads.py`

---

## Extensions

- Add second-month futures (CL2=F) for a proper calendar spread / contango measure
- Integrate EIA weekly petroleum storage reports as a fundamental overlay
- Add seasonal adjustments (crack spreads have strong summer/winter seasonality)
- Connect to a CME API for settlement prices instead of Yahoo Finance

---

## Data Sources

- **Yahoo Finance** â€” front-month NYMEX/CBOT futures via `yfinance`
- **CME Group** â€” for production use, replace with CME DataMine or Quandl futures feeds
- **EIA** â€” weekly petroleum storage, refinery utilisation (free API at `api.eia.gov`)

---

*Not financial advice. Spread trading involves substantial risk. Past backtest results do not guarantee future performance.*

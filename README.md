# Alpha Momentum & Risk Management Terminal

Single-page dashboard synthesizing four trading systems into one workflow:

- **Jesse Livermore** — pyramiding into strength, cutting losses fast
- **William O'Neil** — CAN SLIM fundamentals, Follow-Through Days, Relative Strength Line
- **Mark Minervini** — Trend Template, Volatility Contraction Pattern (VCP), fixed-risk position sizing
- **Stan Weinstein** — 4-Stage market regime analysis

All data in the dashboard is **mock data** (deterministic, seeded synthetic price series) built to
exercise every rule honestly — the pass/fail flags you see are computed by the real detection
functions, not hardcoded. Stock tickers (`NOVA`, `ZENITH`, `ORION`, `QUARTZ`, `ATLAS`, `BOLT`,
`STELLA`, `VELOX`, `TRIUM`) are fictional and do not represent real SET-listed companies.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project layout

```
app.py                     Streamlit single-page dashboard (4 sections)
core/
  models.py                Dataclasses & enums shared by every engine
  market_regime.py         Weinstein Stage Analysis (weekly) + O'Neil Follow-Through Day (daily)
  screener.py               CAN SLIM + Minervini Trend Template + RS Line + VCP detection
  position_sizing.py        1.5% fixed-risk sizing, 7-8% hard stop, 20-25% single-stock cap,
                             board-lot rounding, 50/30/20 pyramid scale-in plan
  exit_engine.py             2R partial profit-taking + Chandelier Exit (22d high - 3x ATR14)
  mock_data.py               Deterministic seeded mock SET index + stock price generators
```

## Architecture notes

- **Market Regime Engine** (`core/market_regime.py`): classifies Stage 1-4 from the weekly 30-period
  SMA and its 4-week slope, and independently scans the daily index for a Follow-Through Day
  (day 4-10 of a rally attempt, index +1.5%+ on rising volume). Stage 4 forces 100% cash and blocks
  all new buys; Stage 3 blocks new buys and squeezes trailing stops to the 20-day EMA; Stage 1
  requires a confirmed FTD before unlocking a pilot buy; Stage 2 is normal exposure.
- **Stock Alpha Screener** (`core/screener.py`): liquidity/free-float filter, CAN SLIM fundamentals,
  the 4-condition Minervini Trend Template, an RS Line 60-day-high check (or "approaching high"),
  and VCP detection via swing-point pullback depths (contracting T1 > T2 > T3) with a volume
  dry-up check on the final wave, producing a pivot price and % distance to it.
- **Position Sizing & Scale-in Engine** (`core/position_sizing.py`): sizes to 1.5% risk capital,
  caps the hard stop at 7.5% (mid of the 7-8% band) off the pivot, caps single-name exposure at
  22.5% (mid of the 20-25% band), rounds down to 100-share board lots, and splits the result into
  the 50/30/20 pyramid (Pilot / Confirm +3% / Add-on up to +5%), moving stops to breakeven and then
  to a blended risk-free level as each leg fires.
- **Lifecycle & Exit Engine** (`core/exit_engine.py`): computes the 2R target from the initial stop
  distance and the Chandelier Exit (22-day highest high minus 3x ATR-14) for trailing the runner
  half of the position after the 2R partial sale.

## Disclaimer

This is a demonstration of trading-system logic with synthetic data. It is not investment advice
and should not be used to make real trading decisions without independent verification against
real market data and a licensed advisor.

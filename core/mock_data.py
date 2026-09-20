"""Deterministic mock data for the Alpha Momentum & Risk Terminal.

All tickers below (NOVA, ZENITH, ORION, ...) are FICTIONAL mock symbols
invented for this demo — they do not represent real SET-listed companies.
Series are built with a seeded RNG plus hand-placed swing points so that
the real detection functions in ``core.market_regime`` / ``core.screener``
have genuine, honest patterns to find (Stage 2 + FTD on the index, VCP
contractions on the candidate stocks) rather than hardcoded flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from core.models import PortfolioPosition, TradeState

TRADING_DAYS = 500


def _business_day_index(n: int, end: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.bdate_range(end=end, periods=n)


def _ramp_with_noise(start: float, end: float, n: int, noise_std: float, rng: np.random.Generator) -> np.ndarray:
    """A smooth deterministic exponential trend from ``start`` to ``end`` with
    small bounded (non-compounding) noise — avoids the variance-drag of a
    pure random walk so long histories land at a predictable level.
    """
    trend = start * np.exp(np.linspace(0.0, np.log(end / start), n))
    return trend * (1 + rng.normal(0, noise_std, n))


def _ohlcv_from_closes(closes: np.ndarray, volumes: np.ndarray, wick_pct: float = 0.006) -> pd.DataFrame:
    """Synthesize plausible open/high/low around a close series."""
    rng = np.random.default_rng(abs(hash(tuple(closes[:3]))) % (2**32))
    opens = np.empty_like(closes)
    opens[0] = closes[0]
    opens[1:] = closes[:-1] * (1 + rng.normal(0, 0.001, len(closes) - 1))
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.normal(wick_pct, wick_pct / 3, len(closes))))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.normal(wick_pct, wick_pct / 3, len(closes))))
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}
    )


# ---------------------------------------------------------------------------
# SET index: long uptrend -> short correction -> Follow-Through Day -> Stage 2
# ---------------------------------------------------------------------------
def generate_set_index_daily(end_date: pd.Timestamp, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_hist = TRADING_DAYS - 39  # bulk history before the scripted tail
    n_decline = 19
    n_tail = 20
    total = n_hist + n_decline + n_tail

    # 1) Long deterministic uptrend (+ bounded noise) to build a rising 30-week SMA.
    hist_closes = _ramp_with_noise(1300.0, 1300.0 * 1.22, n_hist, noise_std=0.006, rng=rng)

    # 2) Short, strictly-decreasing correction (~-6%) — no interior up-days,
    #    so the rally-attempt scanner cannot find a false "Day 1" inside it.
    decline_start = hist_closes[-1]
    decline_closes = decline_start * np.linspace(1.0, 0.94, n_decline)

    # 3) Scripted rally: every day from here on is a strictly higher close
    #    than the day before (no interior wiggles), so the FTD scan finds
    #    exactly one rally-attempt start and counts days cleanly from it.
    tail_pct_changes = [0.003, 0.004, 0.002, 0.005, 0.018] + [0.0015] * (n_tail - 5)
    tail_closes = []
    last = decline_closes[-1]
    for pct in tail_pct_changes:
        last = last * (1 + pct)
        tail_closes.append(last)
    tail_closes = np.array(tail_closes)

    closes = np.concatenate([hist_closes, decline_closes, tail_closes])
    assert len(closes) == total

    # Volume: baseline noise, with a clear spike on the FTD day (index n_hist+n_decline+4).
    volumes = rng.integers(1_800_000_000, 2_400_000_000, total).astype(float)
    ftd_idx = n_hist + n_decline + 4  # day_offset 5 (0-indexed offset 4) of the tail
    volumes[ftd_idx] = volumes[ftd_idx - 1] * 1.9
    for i in range(n_hist + n_decline, n_hist + n_decline + n_tail):
        if i != ftd_idx:
            volumes[i] = volumes[i - 1] * rng.uniform(0.85, 1.05)

    df = _ohlcv_from_closes(closes, volumes, wick_pct=0.004)
    df.index = _business_day_index(total, end_date)
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# Individual stocks: long uptrend base + a 3-wave contracting VCP into a pivot
# ---------------------------------------------------------------------------
@dataclass
class VCPStockSpec:
    symbol: str
    seed: int
    base_price: float
    uptrend_days: int
    uptrend_drift: float
    wave_depths_pct: Tuple[float, float, float]  # T1 > T2 > T3, contracting
    final_offset_from_pivot_pct: float  # how far current price sits below the pivot


def generate_vcp_stock_daily(spec: VCPStockSpec, end_date: pd.Timestamp) -> pd.DataFrame:
    rng = np.random.default_rng(spec.seed)

    # 1) Long uptrend base (builds EMA50 > SMA150 > SMA200 stacking, a 52w low
    #    well under the current price, and a rising SMA200).
    target_end = spec.base_price * np.exp(spec.uptrend_drift * spec.uptrend_days)
    hist_closes = _ramp_with_noise(spec.base_price, target_end, spec.uptrend_days, noise_std=0.010, rng=rng)
    h0 = hist_closes[-1]  # first resistance high

    depth1, depth2, depth3 = spec.wave_depths_pct
    l1 = h0 * (1 - depth1 / 100.0)
    h1 = h0 * 0.985
    l2 = h1 * (1 - depth2 / 100.0)
    h2 = h1 * 0.99
    l3 = h2 * (1 - depth3 / 100.0)
    current = h2 * (1 - spec.final_offset_from_pivot_pct / 100.0)

    def ramp(a: float, b: float, n: int) -> np.ndarray:
        return a * np.exp(np.linspace(0, np.log(b / a), n))

    seg_w1_down = ramp(h0, l1, 10)[1:]
    seg_w1_up = ramp(l1, h1, 8)[1:]
    seg_w2_down = ramp(h1, l2, 8)[1:]
    seg_w2_up = ramp(l2, h2, 7)[1:]
    seg_w3_down = ramp(h2, l3, 6)[1:]
    seg_w3_consolidate = ramp(l3, current, 10)[1:]

    vcp_closes = np.concatenate(
        [[h0], seg_w1_down, seg_w1_up, seg_w2_down, seg_w2_up, seg_w3_down, seg_w3_consolidate]
    )
    closes = np.concatenate([hist_closes, vcp_closes])

    n_total = len(closes)
    base_volume = rng.integers(1_400_000, 2_200_000, n_total).astype(float)

    vcp_start = spec.uptrend_days
    idx = vcp_start
    lengths = {
        "w1_down": len(seg_w1_down),
        "w1_up": len(seg_w1_up),
        "w2_down": len(seg_w2_down),
        "w2_up": len(seg_w2_up),
        "w3_down": len(seg_w3_down),
        "w3_consolidate": len(seg_w3_consolidate),
    }
    # Rallies (up-legs) trade on heavier volume; each successive pullback and
    # the final consolidation trade on progressively lighter, drying-up volume.
    volume_multipliers = {
        "w1_down": 1.3,
        "w1_up": 1.6,
        "w2_down": 1.0,
        "w2_up": 1.2,
        "w3_down": 0.75,
        "w3_consolidate": 0.55,
    }
    pos = idx + 1  # first point (h0) already counted in base
    for seg_name in ["w1_down", "w1_up", "w2_down", "w2_up", "w3_down", "w3_consolidate"]:
        seg_len = lengths[seg_name]
        mult = volume_multipliers[seg_name]
        base_volume[pos : pos + seg_len] = rng.integers(1_400_000, 2_200_000, seg_len) * mult
        pos += seg_len

    df = _ohlcv_from_closes(closes, base_volume, wick_pct=0.008)
    df.index = _business_day_index(n_total, end_date)
    df.index.name = "date"
    return df


DEFAULT_WATCHLIST_SPECS: List[VCPStockSpec] = [
    VCPStockSpec("NOVA", 101, 18.0, 320, 0.0016, (17.0, 11.0, 5.0), 1.5),
    VCPStockSpec("ZENITH", 102, 25.0, 320, 0.0014, (20.0, 13.0, 6.0), 0.8),
    VCPStockSpec("ORION", 103, 14.5, 300, 0.0012, (16.0, 9.0, 4.5), 2.2),
    VCPStockSpec("QUARTZ", 104, 32.0, 300, 0.0010, (14.0, 12.0, 9.0), 4.0),  # still contracting slowly -> FORMING
    VCPStockSpec("ATLAS", 105, 20.0, 280, 0.0006, (10.0, 8.0, 7.5), 6.0),  # weak contraction -> NONE/FORMING
]

FUNDAMENTALS_DB: Dict[str, dict] = {
    "NOVA": dict(eps_growth_yoy_pct=34.0, sales_growth_yoy_pct=22.0, net_income_positive=True, roe_pct=19.5),
    "ZENITH": dict(eps_growth_yoy_pct=41.5, sales_growth_yoy_pct=28.0, net_income_positive=True, roe_pct=23.0),
    "ORION": dict(eps_growth_yoy_pct=26.0, sales_growth_yoy_pct=18.5, net_income_positive=True, roe_pct=16.0),
    "QUARTZ": dict(eps_growth_yoy_pct=12.0, sales_growth_yoy_pct=9.0, net_income_positive=True, roe_pct=11.0),  # fails CAN SLIM
    "ATLAS": dict(eps_growth_yoy_pct=8.0, sales_growth_yoy_pct=6.0, net_income_positive=True, roe_pct=9.0),  # fails CAN SLIM
}

LIQUIDITY_DB: Dict[str, dict] = {
    "NOVA": dict(turnover_20d_avg_mbaht=85.0, avg_volume_50d=4_200_000, free_float_pct=42.0),
    "ZENITH": dict(turnover_20d_avg_mbaht=62.0, avg_volume_50d=2_600_000, free_float_pct=35.0),
    "ORION": dict(turnover_20d_avg_mbaht=48.0, avg_volume_50d=3_100_000, free_float_pct=55.0),
    "QUARTZ": dict(turnover_20d_avg_mbaht=110.0, avg_volume_50d=3_800_000, free_float_pct=48.0),
    "ATLAS": dict(turnover_20d_avg_mbaht=33.0, avg_volume_50d=1_500_000, free_float_pct=28.0),
}


# ---------------------------------------------------------------------------
# Portfolio holdings: hand-placed to demonstrate every stage of the lifecycle
# ---------------------------------------------------------------------------
def generate_runner_stock_daily(
    symbol: str, seed: int, base_price: float, breakout_price: float, uptrend_days: int, runner_days: int, end_date: pd.Timestamp
) -> pd.DataFrame:
    """A stock that already broke out and has been trending (for Chandelier Exit demos)."""
    rng = np.random.default_rng(seed)
    hist_returns = rng.normal(0.0010, 0.013, uptrend_days)
    hist_closes = base_price * np.cumprod(1 + hist_returns)
    hist_closes = hist_closes * (breakout_price / hist_closes[-1])

    runner_returns = rng.normal(0.0055, 0.011, runner_days)
    runner_closes = breakout_price * np.cumprod(1 + runner_returns)

    closes = np.concatenate([hist_closes, runner_closes])
    volumes = rng.integers(1_200_000, 3_000_000, len(closes)).astype(float)
    df = _ohlcv_from_closes(closes, volumes, wick_pct=0.009)
    df.index = _business_day_index(len(closes), end_date)
    df.index.name = "date"
    return df


PORTFOLIO_SPECS = [
    dict(symbol="BOLT", seed=201, base_price=16.0, breakout_price=19.8, uptrend_days=260, runner_days=6,
         avg_cost=19.8, shares=15_000, weight_pct=9.5, state=TradeState.IN_PILOT_50,
         initial_stop=18.35, trailing_stop=18.35, target_2r_mult=2.0),
    dict(symbol="STELLA", seed=202, base_price=22.0, breakout_price=26.5, uptrend_days=260, runner_days=10,
         avg_cost=27.1, shares=28_000, weight_pct=15.0, state=TradeState.IN_CONFIRM_80,
         initial_stop=24.4, trailing_stop=26.5, target_2r_mult=2.0),
    dict(symbol="VELOX", seed=203, base_price=13.5, breakout_price=15.9, uptrend_days=260, runner_days=16,
         avg_cost=16.35, shares=42_000, weight_pct=19.0, state=TradeState.IN_FULL_100_RISK_FREE,
         initial_stop=14.6, trailing_stop=16.35, target_2r_mult=2.0),
    dict(symbol="TRIUM", seed=204, base_price=28.0, breakout_price=33.0, uptrend_days=260, runner_days=34,
         avg_cost=33.5, shares=20_000, weight_pct=13.5, state=TradeState.RUNNER_50,
         initial_stop=30.4, trailing_stop=None, target_2r_mult=2.0),
]


def build_portfolio(end_date: pd.Timestamp) -> Tuple[List[PortfolioPosition], Dict[str, pd.DataFrame]]:
    from core.exit_engine import compute_chandelier_exit, compute_2r_target

    positions: List[PortfolioPosition] = []
    price_data: Dict[str, pd.DataFrame] = {}

    for spec in PORTFOLIO_SPECS:
        df = generate_runner_stock_daily(
            spec["symbol"], spec["seed"], spec["base_price"], spec["breakout_price"],
            spec["uptrend_days"], spec["runner_days"], end_date,
        )
        price_data[spec["symbol"]] = df
        current_price = round(float(df["close"].iloc[-1]), 2)

        target_2r = compute_2r_target(spec["breakout_price"], spec["initial_stop"])

        if spec["trailing_stop"] is None:  # RUNNER_50 -> trails on Chandelier Exit
            trailing_stop = round(float(compute_chandelier_exit(df).iloc[-1]), 2)
        else:
            trailing_stop = spec["trailing_stop"]

        positions.append(
            PortfolioPosition(
                symbol=spec["symbol"],
                avg_cost=spec["avg_cost"],
                shares=spec["shares"],
                portfolio_weight_pct=spec["weight_pct"],
                trade_state=spec["state"],
                initial_stop=spec["initial_stop"],
                trailing_stop=trailing_stop,
                target_2r=target_2r,
                current_price=current_price,
            )
        )
    return positions, price_data


def get_full_universe_daily(end_date: pd.Timestamp) -> Dict[str, pd.DataFrame]:
    """All watchlist-candidate stock price series, keyed by symbol."""
    return {spec.symbol: generate_vcp_stock_daily(spec, end_date) for spec in DEFAULT_WATCHLIST_SPECS}

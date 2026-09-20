"""Stock Alpha Screener — O'Neil CAN SLIM + Minervini Trend Template + VCP.

Works on a daily OHLCV DataFrame (``open, high, low, close, volume``) for a
single stock plus the matching market-index close series for Relative
Strength, and a small fundamentals dict for the CAN SLIM checks.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from core.models import (
    CanSlimResult,
    LiquidityProfile,
    TrendTemplateResult,
    VCPResult,
    WatchlistItem,
)


def evaluate_liquidity(
    price: float, turnover_20d_avg_mbaht: float, avg_volume_50d: int, free_float_pct: float
) -> LiquidityProfile:
    return LiquidityProfile(
        price=price,
        turnover_20d_avg_mbaht=turnover_20d_avg_mbaht,
        avg_volume_50d=avg_volume_50d,
        free_float_pct=free_float_pct,
    )


def evaluate_can_slim(
    eps_growth_yoy_pct: float, sales_growth_yoy_pct: float, net_income_positive: bool, roe_pct: float
) -> CanSlimResult:
    return CanSlimResult(
        eps_growth_yoy_pct=eps_growth_yoy_pct,
        sales_growth_yoy_pct=sales_growth_yoy_pct,
        net_income_positive=net_income_positive,
        roe_pct=roe_pct,
    )


def evaluate_trend_template(daily_df: pd.DataFrame) -> TrendTemplateResult:
    """Minervini's Trend Template, 4 pass/fail conditions."""
    close = daily_df["close"]
    ema50 = close.ewm(span=50, adjust=False).mean()
    sma150 = close.rolling(150, min_periods=150).mean()
    sma200 = close.rolling(200, min_periods=200).mean()

    price = float(close.iloc[-1])
    ema50_last = float(ema50.iloc[-1])
    sma150_last = float(sma150.iloc[-1]) if not np.isnan(sma150.iloc[-1]) else float("nan")
    sma200_last = float(sma200.iloc[-1]) if not np.isnan(sma200.iloc[-1]) else float("nan")

    price_above_ema50 = price > ema50_last
    stacked = (
        not np.isnan(sma150_last)
        and not np.isnan(sma200_last)
        and ema50_last > sma150_last > sma200_last
    )

    sma200_valid = sma200.dropna()
    if len(sma200_valid) > 20:
        sma200_trending_up = float(sma200_valid.iloc[-1]) > float(sma200_valid.iloc[-21])
    else:
        sma200_trending_up = False

    window = min(252, len(daily_df))
    low_52w = float(daily_df["low"].iloc[-window:].min())
    high_52w = float(daily_df["high"].iloc[-window:].max())
    above_52w_low_pct = (price - low_52w) / low_52w * 100.0
    within_52w_high_pct = (high_52w - price) / high_52w * 100.0

    return TrendTemplateResult(
        price_above_ema50=price_above_ema50,
        ema50_above_sma150_above_sma200=stacked,
        sma200_trending_up=sma200_trending_up,
        above_52w_low_ge_25pct=above_52w_low_pct >= 25.0,
        within_52w_high_le_25pct=within_52w_high_pct <= 25.0,
        above_52w_low_pct=round(above_52w_low_pct, 1),
        within_52w_high_pct=round(within_52w_high_pct, 1),
    )


def compute_relative_strength(
    stock_close: pd.Series, index_close: pd.Series, new_high_window: int = 60, near_high_tolerance_pct: float = 10.0
) -> Tuple[bool, float]:
    """RS Line = stock close / index close. Returns (made_new_60d_high, pct_off_60d_high)."""
    aligned = pd.concat([stock_close.rename("s"), index_close.rename("i")], axis=1).dropna()
    rs_line = aligned["s"] / aligned["i"]
    window = min(new_high_window, len(rs_line))
    rolling_max = rs_line.iloc[-window:].max()
    last = rs_line.iloc[-1]
    pct_off_high = (rolling_max - last) / rolling_max * 100.0
    made_new_high = pct_off_high <= near_high_tolerance_pct
    return bool(made_new_high), round(float(pct_off_high), 2)


def _find_swing_points(prices: np.ndarray, window: int = 5) -> List[Tuple[int, float, str]]:
    """Locate local maxima/minima where a point is the extreme within +/- window bars."""
    points: List[Tuple[int, float, str]] = []
    n = len(prices)
    for i in range(window, n - window):
        segment = prices[i - window : i + window + 1]
        if prices[i] == segment.max() and prices[i] != prices[i - 1]:
            points.append((i, prices[i], "high"))
        elif prices[i] == segment.min() and prices[i] != prices[i - 1]:
            points.append((i, prices[i], "low"))

    # Collapse consecutive same-type points, keeping the more extreme one.
    collapsed: List[Tuple[int, float, str]] = []
    for pt in points:
        if collapsed and collapsed[-1][2] == pt[2]:
            better = pt if (pt[2] == "high" and pt[1] > collapsed[-1][1]) or (
                pt[2] == "low" and pt[1] < collapsed[-1][1]
            ) else collapsed[-1]
            collapsed[-1] = better
        else:
            collapsed.append(pt)
    return collapsed


def detect_vcp(
    daily_df: pd.DataFrame, lookback: int = 90, swing_window: int = 5, pivot_buffer_pct: float = 0.3
) -> VCPResult:
    """Detect a Volatility Contraction Pattern over the trailing ``lookback`` bars.

    Looks for the last 2-3 high->low pullback waves and checks that each
    wave is shallower than the previous one (T1 > T2 > T3), and that the
    volume during the final wave has dried up below the 50-day average.
    """
    window_df = daily_df.iloc[-lookback:]
    highs = window_df["high"].to_numpy()
    lows = window_df["low"].to_numpy()
    closes = window_df["close"].to_numpy()
    volumes = window_df["volume"].to_numpy()

    swings = _find_swing_points(highs, swing_window) + [
        (i, lows[i], "low") for i in range(len(lows))
    ]
    # Rebuild swings using close-based extremes for stability instead of mixing arrays.
    swings = _find_swing_points(closes, swing_window)

    pullbacks: List[Tuple[float, int, int]] = []  # (depth_pct, high_idx, low_idx)
    for j in range(len(swings) - 1):
        idx_a, price_a, type_a = swings[j]
        idx_b, price_b, type_b = swings[j + 1]
        if type_a == "high" and type_b == "low" and price_a > 0:
            depth_pct = (price_a - price_b) / price_a * 100.0
            pullbacks.append((depth_pct, idx_a, idx_b))

    if len(pullbacks) < 2:
        return VCPResult(contraction_depths_pct=[], is_contracting=False, volume_dry_up=False, pivot_price=None, status="NONE")

    last_waves = pullbacks[-3:] if len(pullbacks) >= 3 else pullbacks[-2:]
    depths = [round(d, 1) for d, _, _ in last_waves]
    is_contracting = all(depths[i] > depths[i + 1] for i in range(len(depths) - 1))

    last_high_idx, last_low_idx = last_waves[-1][1], last_waves[-1][2]
    final_wave_volume = volumes[last_high_idx : last_low_idx + 1]
    avg_vol_50d = float(daily_df["volume"].iloc[-50:].mean())
    volume_dry_up = bool(final_wave_volume.mean() < avg_vol_50d) if len(final_wave_volume) else False

    pivot_price = round(float(closes[last_high_idx]) * (1 + pivot_buffer_pct / 100.0), 2)

    current_price = float(daily_df["close"].iloc[-1])
    near_pivot = current_price >= pivot_price * 0.97

    if is_contracting and volume_dry_up and near_pivot:
        status = "READY"
    elif is_contracting:
        status = "FORMING"
    else:
        status = "NONE"

    return VCPResult(
        contraction_depths_pct=depths,
        is_contracting=is_contracting,
        volume_dry_up=volume_dry_up,
        pivot_price=pivot_price,
        status=status,
    )


def build_watchlist_item(
    symbol: str,
    daily_df: pd.DataFrame,
    index_close: pd.Series,
    fundamentals: dict,
    liquidity_kwargs: dict,
) -> WatchlistItem:
    """Run the full O'Neil/Minervini screen for one stock and package the result."""
    price = float(daily_df["close"].iloc[-1])
    liquidity = evaluate_liquidity(price=price, **liquidity_kwargs)
    can_slim = evaluate_can_slim(**fundamentals)
    trend = evaluate_trend_template(daily_df)
    rs_new_high, rs_pct_off = compute_relative_strength(daily_df["close"], index_close)
    vcp = detect_vcp(daily_df)

    pct_to_pivot: Optional[float] = None
    if vcp.pivot_price:
        pct_to_pivot = round((vcp.pivot_price - price) / price * 100.0, 2)

    return WatchlistItem(
        symbol=symbol,
        price=round(price, 2),
        liquidity=liquidity,
        rs_new_high_60d=rs_new_high,
        rs_pct_off_60d_high=rs_pct_off,
        trend_template=trend,
        can_slim=can_slim,
        vcp=vcp,
        pct_to_pivot=pct_to_pivot,
    )

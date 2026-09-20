"""Market Regime Engine — Stan Weinstein Stage Analysis + William O'Neil FTD.

All functions take pandas DataFrames indexed by date with at minimum
``open, high, low, close, volume`` columns (lowercase).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from core.models import BuyLight, FollowThroughDay, MarketRegime, MarketStage

FLAT_SLOPE_THRESHOLD_PCT = 0.5


def resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse a daily OHLCV frame into a weekly OHLCV frame (W-FRI bars)."""
    weekly = daily_df.resample("W-FRI").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return weekly.dropna()


def classify_stage(weekly_df: pd.DataFrame, sma_period: int = 30) -> tuple[MarketStage, float, float]:
    """Classify the current Weinstein stage from a weekly OHLCV frame.

    Returns (stage, sma30w_last_value, slope_4w_pct). The slope is measured
    over the last 4 weekly bars; a secondary 13-week slope disambiguates
    Stage 1 (basing, coming from a decline) from Stage 3 (topping, coming
    from an advance) when the 4-week slope is flat.
    """
    sma = weekly_df["close"].rolling(sma_period).mean()
    if sma.dropna().shape[0] < 5:
        raise ValueError("Not enough weekly history to compute a 30-week SMA")

    sma_now = float(sma.iloc[-1])
    sma_4w_ago = float(sma.iloc[-5])
    slope_4w_pct = (sma_now - sma_4w_ago) / sma_4w_ago * 100.0

    long_lookback = min(14, sma.dropna().shape[0] - 1)
    sma_long_ago = float(sma.iloc[-1 - long_lookback])
    slope_long_pct = (sma_now - sma_long_ago) / sma_long_ago * 100.0

    price = float(weekly_df["close"].iloc[-1])
    price_above_sma = price > sma_now

    if slope_4w_pct > FLAT_SLOPE_THRESHOLD_PCT and price_above_sma:
        stage = MarketStage.STAGE_2
    elif slope_4w_pct < -FLAT_SLOPE_THRESHOLD_PCT and not price_above_sma:
        stage = MarketStage.STAGE_4
    elif slope_long_pct > 0:
        stage = MarketStage.STAGE_3
    else:
        stage = MarketStage.STAGE_1

    return stage, sma_now, slope_4w_pct


def _find_rally_attempt_start(daily_df: pd.DataFrame, lookback: int = 40) -> Optional[int]:
    """Locate the most recent 'Day 1' of a rally attempt: the first up-close
    following a down-close, searched backward within ``lookback`` sessions."""
    closes = daily_df["close"].to_numpy()
    n = len(closes)
    start = max(n - lookback, 1)
    for i in range(n - 2, start - 1, -1):
        if closes[i] < closes[i - 1] and closes[i + 1] > closes[i]:
            return i + 1
    return None


def detect_follow_through_day(daily_df: pd.DataFrame, min_day: int = 4, max_day: int = 10) -> FollowThroughDay:
    """Scan for an O'Neil Follow-Through Day: on rally day ``min_day``..``max_day``
    the index must close up >= +1.50% on volume higher than the prior session.
    """
    day1_idx = _find_rally_attempt_start(daily_df)
    if day1_idx is None:
        return FollowThroughDay(detected=False)

    closes = daily_df["close"].to_numpy()
    volumes = daily_df["volume"].to_numpy()
    n = len(closes)

    for day_offset in range(min_day, max_day + 1):
        idx = day1_idx + day_offset - 1
        if idx >= n or idx <= 0:
            break
        pct_change = (closes[idx] - closes[idx - 1]) / closes[idx - 1] * 100.0
        volume_confirmed = bool(volumes[idx] > volumes[idx - 1])
        if pct_change >= 1.5 and volume_confirmed:
            return FollowThroughDay(
                detected=True,
                ftd_date=daily_df.index[idx].date(),
                day_count=day_offset,
                index_change_pct=round(float(pct_change), 2),
                volume_confirmed=True,
                rally_attempt_start=daily_df.index[day1_idx].date(),
            )
    return FollowThroughDay(detected=False, rally_attempt_start=daily_df.index[day1_idx].date())


def build_market_regime(index_symbol: str, daily_df: pd.DataFrame, weekly_df: Optional[pd.DataFrame] = None) -> MarketRegime:
    """Full Market Regime Engine: Stage Analysis + FTD -> cash%/buy-light rules.

    Hard rules from the spec:
      * Stage 4  -> 100% cash, buying forbidden.
      * Stage 3  -> no new buys, trailing stops squeezed to the 20d EMA.
      * Stage 1  -> wait for a confirmed FTD before any pilot buy.
      * Stage 2  -> normal exposure, green light.
    """
    if weekly_df is None:
        weekly_df = resample_to_weekly(daily_df)

    stage, sma30w, slope_4w_pct = classify_stage(weekly_df)
    ftd = detect_follow_through_day(daily_df)

    last_close = float(daily_df["close"].iloc[-1])
    prev_close = float(daily_df["close"].iloc[-2])
    change_1d = (last_close - prev_close) / prev_close * 100.0

    notes: List[str] = []

    if stage == MarketStage.STAGE_4:
        cash_pct = 100.0
        light = BuyLight.RED
        allow_buys = False
        stop_policy = "N/A — ปิดสถานะทั้งหมด, ถือเงินสด 100%"
        notes.append("Stage 4 (Declining): บังคับเงินสด 100% ห้ามเปิดไม้ซื้อใหม่เด็ดขาด")
    elif stage == MarketStage.STAGE_3:
        cash_pct = 60.0
        light = BuyLight.RED
        allow_buys = False
        stop_policy = "บีบ Trailing Stop เข้าชิด EMA 20 วัน"
        notes.append("Stage 3 (Topping): ห้ามซื้อหุ้นใหม่ และบีบ Stop เข้าใกล้ EMA20")
    elif stage == MarketStage.STAGE_1:
        if ftd.detected:
            cash_pct = 50.0
            light = BuyLight.YELLOW
            allow_buys = True
            stop_policy = "Stop เริ่มต้นตามแผน Pilot Buy ปกติ (7-8% จาก Pivot)"
            notes.append(
                f"Stage 1 (Basing) + FTD ยืนยันวันที่ {ftd.day_count} "
                f"(+{ftd.index_change_pct}% พร้อมวอลุ่ม) -> ปลดล็อก Pilot Buy"
            )
        else:
            cash_pct = 90.0
            light = BuyLight.YELLOW
            allow_buys = False
            stop_policy = "N/A — ยังไม่มีสถานะใหม่ระหว่างรอ FTD"
            notes.append("Stage 1 (Basing): รอสัญญาณ Follow-Through Day ก่อนเปิดไม้ซื้อ")
    else:  # STAGE_2
        cash_pct = 10.0
        light = BuyLight.GREEN
        allow_buys = True
        stop_policy = "Stop เริ่มต้นตามแผน Pilot Buy ปกติ (7-8% จาก Pivot)"
        notes.append("Stage 2 (Advancing): ตลาดเป็นขาขึ้นเต็มตัว เปิดไม้ซื้อได้ตามแผน")

    return MarketRegime(
        index_symbol=index_symbol,
        last_close=round(last_close, 2),
        index_change_pct_1d=round(change_1d, 2),
        stage=stage,
        sma30w=round(sma30w, 2),
        sma30w_slope_4w_pct=round(slope_4w_pct, 2),
        ftd=ftd,
        recommended_cash_pct=cash_pct,
        buy_light=light,
        allow_new_buys=allow_buys,
        trailing_stop_policy=stop_policy,
        notes=notes,
    )

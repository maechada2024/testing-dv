"""Lifecycle & Exit Engine — R-multiple profit-taking + Chandelier Exit trailing stop."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def compute_2r_target(entry_price: float, initial_stop_price: float) -> float:
    """2R target = entry + 2 x (entry - initial stop)."""
    initial_risk = entry_price - initial_stop_price
    return round(entry_price + 2 * initial_risk, 2)


def compute_atr(daily_df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = daily_df["high"], daily_df["low"], daily_df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.rolling(period).mean()


def compute_chandelier_exit(
    daily_df: pd.DataFrame, lookback: int = 22, atr_period: int = 14, multiplier: float = 3.0
) -> pd.Series:
    """Chandelier Exit = Highest High(lookback) - multiplier x ATR(atr_period)."""
    highest_high = daily_df["high"].rolling(lookback).max()
    atr = compute_atr(daily_df, atr_period)
    return highest_high - multiplier * atr


@dataclass
class ExitEvaluation:
    r_multiple_now: float
    target_2r: float
    chandelier_stop: float
    hit_2r_target: bool
    hit_chandelier_stop: bool
    recommended_action: str


def evaluate_lifecycle(
    entry_price: float,
    initial_stop_price: float,
    current_price: float,
    daily_df: pd.DataFrame,
    already_took_2r_partial: bool = False,
) -> ExitEvaluation:
    """Decide the current lifecycle action for an open position.

    Rules:
      * On touching the 2R target, sell 50% and move the remaining stop to breakeven.
      * The remaining runner trails on the Chandelier Exit and exits fully on a close below it.
    """
    initial_risk = entry_price - initial_stop_price
    r_multiple_now = (current_price - entry_price) / initial_risk if initial_risk > 0 else 0.0
    target_2r = compute_2r_target(entry_price, initial_stop_price)
    chandelier_series = compute_chandelier_exit(daily_df)
    chandelier_stop = float(chandelier_series.iloc[-1])

    hit_2r_target = current_price >= target_2r
    hit_chandelier_stop = current_price <= chandelier_stop

    if already_took_2r_partial:
        if hit_chandelier_stop:
            action = "⛔ ปิดสถานะรันเนอร์ที่เหลือ — ราคาปิดหลุด Chandelier Exit"
        else:
            action = "✅ ถือรันเนอร์ต่อ — Trailing ด้วย Chandelier Exit"
    else:
        if hit_2r_target:
            action = "💰 ขายล็อกกำไร 50% ทันที (แตะเป้า 2R) และเลื่อน Stop ส่วนที่เหลือมาที่ Breakeven"
        elif current_price <= initial_stop_price:
            action = "⛔ ตัดขาดทุนตาม Stop เริ่มต้น"
        else:
            action = "✅ ถือต่อ — ยังไม่แตะเป้าหรือ Stop"

    return ExitEvaluation(
        r_multiple_now=round(r_multiple_now, 2),
        target_2r=target_2r,
        chandelier_stop=round(chandelier_stop, 2),
        hit_2r_target=hit_2r_target,
        hit_chandelier_stop=hit_chandelier_stop,
        recommended_action=action,
    )

"""Position Sizing & Progressive Scale-in Engine (Minervini & Livermore).

Fixed-fractional risk sizing (1.5% of equity), a hard 7-8% stop off the
pivot, a 20-25% single-name cap, board-lot rounding for the Thai market,
and the 50/30/20 pyramid entry plan.
"""
from __future__ import annotations

from typing import List

from core.models import PositionSizingPlan, ScaleInStep

RISK_CAPITAL_PCT = 1.5
HARD_STOP_PCT = 7.5  # midpoint of the 7.0-8.0% band
SINGLE_STOCK_CAP_PCT = 22.5  # midpoint of the 20-25% band
BOARD_LOT = 100


def round_to_board_lot(shares: float, lot: int = BOARD_LOT) -> int:
    """Round DOWN to the nearest Thai board lot (min 100 shares)."""
    return int(shares // lot) * lot


def build_scale_in_plan(
    symbol: str,
    portfolio_capital: float,
    pivot_price: float,
    risk_capital_pct: float = RISK_CAPITAL_PCT,
    hard_stop_pct: float = HARD_STOP_PCT,
    single_stock_cap_pct: float = SINGLE_STOCK_CAP_PCT,
) -> PositionSizingPlan:
    """Build the full 3-leg pyramid plan (Pilot 50% / Confirm 30% / Add-on 20%)."""
    if pivot_price <= 0 or portfolio_capital <= 0:
        raise ValueError("pivot_price and portfolio_capital must be positive")

    hard_stop_price = round(pivot_price * (1 - hard_stop_pct / 100.0), 2)
    risk_per_share = pivot_price - hard_stop_price
    risk_capital_baht = portfolio_capital * risk_capital_pct / 100.0

    shares_by_risk_cap = round_to_board_lot(risk_capital_baht / risk_per_share)
    shares_by_position_cap = round_to_board_lot(
        (portfolio_capital * single_stock_cap_pct / 100.0) / pivot_price
    )
    final_total_shares = min(shares_by_risk_cap, shares_by_position_cap)

    # Split 50/30/20, each leg rounded down to a board lot; push any lot
    # remainder from rounding into the pilot leg so the plan stays conservative.
    pilot_shares = round_to_board_lot(final_total_shares * 0.50)
    confirm_shares = round_to_board_lot(final_total_shares * 0.30)
    addon_shares = round_to_board_lot(final_total_shares * 0.20)
    allocated = pilot_shares + confirm_shares + addon_shares
    leftover = round_to_board_lot(final_total_shares - allocated)
    pilot_shares += leftover

    entry_1 = pivot_price
    entry_2 = round(pivot_price * 1.03, 2)
    entry_3_ceiling = round(pivot_price * 1.05, 2)

    stop_1 = hard_stop_price
    breakeven_after_2 = entry_1  # Step 1's stop is moved to its own breakeven once Step 2 fires.
    weighted_avg_after_3 = (
        (pilot_shares * entry_1 + confirm_shares * entry_2 + addon_shares * entry_3_ceiling)
        / max(pilot_shares + confirm_shares + addon_shares, 1)
    )

    steps: List[ScaleInStep] = [
        ScaleInStep(
            step_name="ไม้ 1: Pilot Buy (50%)",
            trigger_condition=f"ทะลุ Pivot Point ({pivot_price:.2f}) พร้อม Volume ยืนยัน",
            allocation_pct=50.0,
            shares=pilot_shares,
            entry_price=entry_1,
            stop_price=stop_1,
            risk_baht=round(pilot_shares * (entry_1 - stop_1), 2),
        ),
        ScaleInStep(
            step_name="ไม้ 2: Confirmation Add (30%)",
            trigger_condition=f"ราคาขึ้นต่อ +3.0% จากไม้แรก ({entry_2:.2f}) -> เลื่อน Stop ไม้ 1 เป็น Breakeven",
            allocation_pct=30.0,
            shares=confirm_shares,
            entry_price=entry_2,
            stop_price=breakeven_after_2,
            risk_baht=round(confirm_shares * (entry_2 - breakeven_after_2), 2),
        ),
        ScaleInStep(
            step_name="ไม้ 3: Add-on (20%)",
            trigger_condition=f"ทะลุ High ใหม่ ก่อนราคาเกิน +5.0% จาก Pivot (เพดาน {entry_3_ceiling:.2f}) -> ล็อกเป็น Risk-Free Trade",
            allocation_pct=20.0,
            shares=addon_shares,
            entry_price=entry_3_ceiling,
            stop_price=round(weighted_avg_after_3, 2),
            risk_baht=round(addon_shares * (entry_3_ceiling - weighted_avg_after_3), 2),
        ),
    ]

    return PositionSizingPlan(
        symbol=symbol,
        portfolio_capital=portfolio_capital,
        risk_capital_baht=round(risk_capital_baht, 2),
        pivot_price=pivot_price,
        hard_stop_price=hard_stop_price,
        stop_distance_pct=hard_stop_pct,
        shares_by_risk_cap=shares_by_risk_cap,
        shares_by_position_cap=shares_by_position_cap,
        final_total_shares=pilot_shares + confirm_shares + addon_shares,
        single_stock_cap_pct=single_stock_cap_pct,
        steps=steps,
    )

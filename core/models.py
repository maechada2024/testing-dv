"""Typed data structures shared across the Alpha Momentum & Risk Terminal engines.

Every engine module (market_regime, screener, position_sizing, exit_engine)
speaks in these dataclasses so the Streamlit UI never has to guess field
names or units.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import List, Optional


class MarketStage(str, Enum):
    """Stan Weinstein's four-stage market cycle."""

    STAGE_1 = "Stage 1: Basing"
    STAGE_2 = "Stage 2: Advancing"
    STAGE_3 = "Stage 3: Topping"
    STAGE_4 = "Stage 4: Declining"


class BuyLight(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class FollowThroughDay:
    """Result of scanning a daily index chart for an O'Neil Follow-Through Day."""

    detected: bool
    ftd_date: Optional[date] = None
    day_count: Optional[int] = None
    index_change_pct: Optional[float] = None
    volume_confirmed: Optional[bool] = None
    rally_attempt_start: Optional[date] = None


@dataclass
class MarketRegime:
    """Output of the Market Regime Engine (Weinstein Stage + O'Neil FTD)."""

    index_symbol: str
    last_close: float
    index_change_pct_1d: float
    stage: MarketStage
    sma30w: float
    sma30w_slope_4w_pct: float
    ftd: FollowThroughDay
    recommended_cash_pct: float
    buy_light: BuyLight
    allow_new_buys: bool
    trailing_stop_policy: str
    notes: List[str] = field(default_factory=list)


@dataclass
class TrendTemplateResult:
    """Minervini Trend Template — 4 conditions, all must pass ('4/4')."""

    price_above_ema50: bool
    ema50_above_sma150_above_sma200: bool
    sma200_trending_up: bool
    above_52w_low_ge_25pct: bool
    within_52w_high_le_25pct: bool
    above_52w_low_pct: float
    within_52w_high_pct: float

    @property
    def passed_count(self) -> int:
        checks = [
            self.price_above_ema50 and self.ema50_above_sma150_above_sma200,
            self.sma200_trending_up,
            self.above_52w_low_ge_25pct,
            self.within_52w_high_le_25pct,
        ]
        return sum(1 for c in checks if c)

    @property
    def passed_all(self) -> bool:
        return self.passed_count == 4


@dataclass
class CanSlimResult:
    """O'Neil CAN SLIM fundamental screen (the C-A-N-L pillars used here)."""

    eps_growth_yoy_pct: float
    sales_growth_yoy_pct: float
    net_income_positive: bool
    roe_pct: float

    @property
    def passed(self) -> bool:
        return (
            self.eps_growth_yoy_pct >= 20.0
            and self.sales_growth_yoy_pct >= 15.0
            and self.net_income_positive
            and self.roe_pct >= 15.0
        )


@dataclass
class VCPResult:
    """Volatility Contraction Pattern detection result."""

    contraction_depths_pct: List[float]
    is_contracting: bool
    volume_dry_up: bool
    pivot_price: Optional[float]
    status: str  # "READY" | "FORMING" | "NONE"


@dataclass
class LiquidityProfile:
    price: float
    turnover_20d_avg_mbaht: float
    avg_volume_50d: int
    free_float_pct: float

    @property
    def passed(self) -> bool:
        return (
            12.0 <= self.price <= 40.0
            and self.turnover_20d_avg_mbaht >= 30.0
            and self.avg_volume_50d >= 1_000_000
            and 20.0 <= self.free_float_pct <= 65.0
        )


@dataclass
class WatchlistItem:
    """One row of the Priority Alpha Watchlist (Section 2)."""

    symbol: str
    price: float
    liquidity: LiquidityProfile
    rs_new_high_60d: bool
    rs_pct_off_60d_high: float
    trend_template: TrendTemplateResult
    can_slim: CanSlimResult
    vcp: VCPResult
    pct_to_pivot: Optional[float]

    @property
    def is_actionable(self) -> bool:
        """True when every gate is open and price sits at/near the pivot."""
        return (
            self.liquidity.passed
            and self.can_slim.passed
            and self.trend_template.passed_all
            and self.rs_new_high_60d
            and self.vcp.status in ("READY", "FORMING")
        )


class TradeState(str, Enum):
    IN_PILOT_50 = "IN_PILOT_50"
    IN_CONFIRM_80 = "IN_CONFIRM_80"
    IN_FULL_100 = "IN_FULL_100"
    IN_FULL_100_RISK_FREE = "IN_FULL_100 (Risk-Free)"
    RUNNER_50 = "RUNNER_50 (Post-2R)"


@dataclass
class PortfolioPosition:
    """One row of the Active Portfolio Monitor (Section 3)."""

    symbol: str
    avg_cost: float
    shares: int
    portfolio_weight_pct: float
    trade_state: TradeState
    initial_stop: float
    trailing_stop: float
    target_2r: float
    current_price: float

    @property
    def unrealized_pnl_pct(self) -> float:
        return (self.current_price - self.avg_cost) / self.avg_cost * 100.0

    @property
    def action_alert(self) -> str:
        if self.current_price <= self.trailing_stop:
            return "⛔ SELL — ราคาหลุด Trailing Stop"
        if self.trade_state != TradeState.RUNNER_50 and self.current_price >= self.target_2r:
            return "💰 TAKE PROFIT 50% — แตะเป้า 2R"
        if self.trade_state == TradeState.IN_PILOT_50 and self.current_price >= self.avg_cost * 1.03:
            return "➕ ADD ไม้ 2 (Confirm 30%)"
        if self.trade_state == TradeState.IN_CONFIRM_80:
            return "➕ พิจารณาไม้ 3 (Add-on 20%) หากทะลุ High ใหม่"
        return "✅ HOLD — รันเทรนด์ต่อ"


@dataclass
class ScaleInStep:
    """One leg of the 50/30/20 pyramid entry plan."""

    step_name: str
    trigger_condition: str
    allocation_pct: float
    shares: int
    entry_price: float
    stop_price: float
    risk_baht: float


@dataclass
class PositionSizingPlan:
    """Full output of the Position Sizing & Scale-in Engine (Section 4)."""

    symbol: str
    portfolio_capital: float
    risk_capital_baht: float
    pivot_price: float
    hard_stop_price: float
    stop_distance_pct: float
    shares_by_risk_cap: int
    shares_by_position_cap: int
    final_total_shares: int
    single_stock_cap_pct: float
    steps: List[ScaleInStep]

"""Alpha Momentum & Risk Management Terminal — single-page Streamlit dashboard.

Trading systems synthesized from four masters:
  * Jesse Livermore  — pyramiding into strength, cutting losses fast
  * William O'Neil    — CAN SLIM fundamentals, Follow-Through Days, RS Line
  * Mark Minervini    — Trend Template, VCP, fixed-risk position sizing
  * Stan Weinstein    — 4-Stage market regime analysis

Run with:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.exit_engine import evaluate_lifecycle
from core.market_regime import build_market_regime
from core.mock_data import (
    FUNDAMENTALS_DB,
    LIQUIDITY_DB,
    build_portfolio,
    generate_set_index_daily,
    get_full_universe_daily,
)
from core.models import BuyLight, MarketStage, TradeState, WatchlistItem
from core.position_sizing import (
    HARD_STOP_PCT,
    RISK_CAPITAL_PCT,
    SINGLE_STOCK_CAP_PCT,
    build_scale_in_plan,
)
from core.screener import build_watchlist_item

st.set_page_config(page_title="Alpha Momentum & Risk Terminal", layout="wide", page_icon="📈")

# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
    .regime-card {
        border-radius: 12px; padding: 14px 18px; color: white; text-align: center;
        height: 100%; display:flex; flex-direction:column; justify-content:center;
    }
    .stage-2 { background: linear-gradient(135deg,#0f9d58,#0a7a43); }
    .stage-1 { background: linear-gradient(135deg,#f4b400,#c98f00); }
    .stage-3 { background: linear-gradient(135deg,#e8710a,#b85400); }
    .stage-4 { background: linear-gradient(135deg,#d93025,#a3221b); }
    .light-green { background:#0f9d58; }
    .light-yellow { background:#f4b400; color:#3a2a00 !important; }
    .light-red { background:#d93025; }
    .metric-label { font-size:0.78rem; opacity:0.85; text-transform:uppercase; letter-spacing:0.04em;}
    .metric-value { font-size:1.5rem; font-weight:700; }
    .section-title { font-size:1.15rem; font-weight:700; margin-top:0.4rem; margin-bottom:0.3rem; }
    .disclaimer { font-size:0.75rem; opacity:0.65; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Data pipeline (cached — deterministic given the "as of" date)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="กำลังประมวลผลข้อมูลตลาด (Mock Data)...")
def load_terminal_data(as_of: str):
    end_date = pd.Timestamp(as_of)

    index_df = generate_set_index_daily(end_date)
    regime = build_market_regime("SET-MOCK", index_df)

    universe = get_full_universe_daily(end_date)
    watchlist = [
        build_watchlist_item(sym, df, index_df["close"], FUNDAMENTALS_DB[sym], LIQUIDITY_DB[sym])
        for sym, df in universe.items()
    ]

    positions, portfolio_price_data = build_portfolio(end_date)

    return regime, watchlist, universe, positions, portfolio_price_data, index_df


AS_OF = pd.Timestamp.today().normalize().strftime("%Y-%m-%d")
regime, watchlist, universe, positions, portfolio_price_data, index_df = load_terminal_data(AS_OF)

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = watchlist[0].symbol

st.title("📈 Alpha Momentum & Risk Management Terminal")
st.caption(
    "ระบบสังเคราะห์จาก 4 ปรมาจารย์: Jesse Livermore · William O'Neil · Mark Minervini · Stan Weinstein "
    "— ข้อมูลทั้งหมดในหน้านี้เป็น **Mock Data** เพื่อสาธิตการทำงานของระบบเท่านั้น"
)

# =========================================================================== #
# SECTION 1 — Market Command Bar
# =========================================================================== #
st.markdown('<div class="section-title">1. Market Command Bar</div>', unsafe_allow_html=True)

stage_css = {
    MarketStage.STAGE_1: "stage-1",
    MarketStage.STAGE_2: "stage-2",
    MarketStage.STAGE_3: "stage-3",
    MarketStage.STAGE_4: "stage-4",
}[regime.stage]
light_css = {BuyLight.GREEN: "light-green", BuyLight.YELLOW: "light-yellow", BuyLight.RED: "light-red"}[
    regime.buy_light
]

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(
        f"""<div class="regime-card" style="background:#1e2530;">
        <div class="metric-label">SET-MOCK Index</div>
        <div class="metric-value">{regime.last_close:,.2f}</div>
        <div>{'+' if regime.index_change_pct_1d >= 0 else ''}{regime.index_change_pct_1d:.2f}% (1D)</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f"""<div class="regime-card {stage_css}">
        <div class="metric-label">Market Stage (Weinstein)</div>
        <div class="metric-value">{regime.stage.value}</div>
        <div>SMA30W: {regime.sma30w:,.1f} | Slope 4W: {regime.sma30w_slope_4w_pct:+.2f}%</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c3:
    ftd = regime.ftd
    ftd_text = (
        f"✅ ยืนยันวันที่ {ftd.day_count} (+{ftd.index_change_pct}%)"
        if ftd.detected
        else "⏳ ยังไม่พบสัญญาณ FTD"
    )
    st.markdown(
        f"""<div class="regime-card" style="background:#1e2530;">
        <div class="metric-label">Follow-Through Day</div>
        <div class="metric-value" style="font-size:1.05rem;">{ftd_text}</div>
        <div>{'เริ่มนับจาก ' + str(ftd.rally_attempt_start) if ftd.rally_attempt_start else ''}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f"""<div class="regime-card" style="background:#1e2530;">
        <div class="metric-label">Recommended Cash %</div>
        <div class="metric-value">{regime.recommended_cash_pct:.0f}%</div>
        <div>{regime.trailing_stop_policy}</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c5:
    label = "GREEN LIGHT — เปิดไม้ซื้อได้" if regime.buy_light == BuyLight.GREEN else (
        "YELLOW — ระวัง/รอสัญญาณ" if regime.buy_light == BuyLight.YELLOW else "RED LIGHT — ห้ามซื้อ"
    )
    st.markdown(
        f"""<div class="regime-card {light_css}">
        <div class="metric-label">Buy Signal</div>
        <div class="metric-value" style="font-size:1.1rem;">{label}</div>
        </div>""",
        unsafe_allow_html=True,
    )

for note in regime.notes:
    st.info(note)

st.divider()

# =========================================================================== #
# SECTION 2 — Priority Alpha Watchlist
# =========================================================================== #
st.markdown('<div class="section-title">2. Priority Alpha Watchlist</div>', unsafe_allow_html=True)
st.caption("หุ้นที่ผ่านเกณฑ์สแกน CAN SLIM + Minervini Trend Template + VCP (คำนวณจริงจากราคา/ปริมาณ mock)")

header_cols = st.columns([0.9, 0.8, 1.0, 0.9, 0.9, 0.9, 0.9, 1.0, 1.0, 1.0, 0.9])
headers = [
    "Symbol", "Price", "Turnover(M฿)", "50d Vol", "RS 60d High?", "Trend 4/4",
    "CAN SLIM", "VCP Status", "Pivot", "% to Pivot", "",
]
for col, h in zip(header_cols, headers):
    col.markdown(f"**{h}**")

def _flag(ok: bool) -> str:
    return "✅" if ok else "❌"

for item in watchlist:
    cols = st.columns([0.9, 0.8, 1.0, 0.9, 0.9, 0.9, 0.9, 1.0, 1.0, 1.0, 0.9])
    cols[0].markdown(f"**{item.symbol}**")
    cols[1].write(f"{item.price:,.2f}")
    cols[2].write(f"{item.liquidity.turnover_20d_avg_mbaht:,.0f}")
    cols[3].write(f"{item.liquidity.avg_volume_50d:,.0f}")
    cols[4].write(_flag(item.rs_new_high_60d))
    cols[5].write(f"{_flag(item.trend_template.passed_all)} ({item.trend_template.passed_count}/4)")
    cols[6].write(_flag(item.can_slim.passed))
    status_badge = {"READY": "🟢 READY", "FORMING": "🟡 FORMING", "NONE": "⚪ NONE"}[item.vcp.status]
    cols[7].write(status_badge)
    cols[8].write(f"{item.vcp.pivot_price:,.2f}" if item.vcp.pivot_price else "-")
    if item.pct_to_pivot is not None:
        cols[9].write(f"{item.pct_to_pivot:+.2f}%")
    else:
        cols[9].write("-")
    if cols[10].button("Plan Trade", key=f"plan_{item.symbol}"):
        st.session_state.selected_symbol = item.symbol
        st.toast(f"เลือก {item.symbol} สำหรับวางแผนเทรดในส่วนที่ 4 แล้ว")

with st.expander("เกณฑ์การคัดกรอง (อ้างอิงสเปค)"):
    st.markdown(
        f"""
        - **สภาพคล่อง:** ราคา 12.00–40.00 บาท, มูลค่าซื้อขาย 20 วัน ≥ 30 ลบ./วัน, Volume 50 วัน ≥ 1,000,000 หุ้น, Free Float 20–65%
        - **CAN SLIM:** EPS Growth YoY ≥ 20%, Sales Growth YoY ≥ 15%, กำไรสุทธิเป็นบวก, ROE ≥ 15%
        - **Trend Template 4/4:** ราคา > EMA50 > SMA150 > SMA200, SMA200 ชันขึ้น, สูงกว่า 52W Low ≥ 25%, ห่างจาก 52W High ≤ 25%
        - **VCP:** คลื่นย่อตัวแคบลงเรื่อยๆ (T1 > T2 > T3) พร้อม Volume คลื่นสุดท้ายต่ำกว่าเฉลี่ย 50 วัน
        """
    )

st.divider()

# =========================================================================== #
# SECTION 3 — Active Portfolio Monitor
# =========================================================================== #
st.markdown('<div class="section-title">3. Active Portfolio Monitor</div>', unsafe_allow_html=True)
st.caption("หุ้นที่ถือครองอยู่จริงในพอร์ต พร้อมสถานะวงจรชีวิตการเทรดและคำแนะนำการกระทำ")

port_header_cols = st.columns([0.8, 0.8, 0.9, 0.9, 1.3, 0.9, 0.9, 0.9, 1.8])
port_headers = [
    "Symbol", "Avg Cost", "Shares", "% Port", "Trade State",
    "Trailing Stop", "Target 2R", "P&L %", "Action Alert",
]
for col, h in zip(port_header_cols, port_headers):
    col.markdown(f"**{h}**")

for pos in positions:
    cols = st.columns([0.8, 0.8, 0.9, 0.9, 1.3, 0.9, 0.9, 0.9, 1.8])
    cols[0].markdown(f"**{pos.symbol}**")
    cols[1].write(f"{pos.avg_cost:,.2f}")
    cols[2].write(f"{pos.shares:,}")
    cols[3].write(f"{pos.portfolio_weight_pct:.1f}%")
    cols[4].write(pos.trade_state.value)
    cols[5].write(f"{pos.trailing_stop:,.2f}")
    cols[6].write(f"{pos.target_2r:,.2f}")
    pnl = pos.unrealized_pnl_pct
    pnl_color = "green" if pnl >= 0 else "red"
    cols[7].markdown(f":{pnl_color}[{pnl:+.2f}%]")
    cols[8].write(pos.action_alert)

total_weight = sum(p.portfolio_weight_pct for p in positions)
st.caption(f"สัดส่วนพอร์ตที่ถือครองรวม: {total_weight:.1f}% | เงินสดคงเหลือโดยประมาณ: {100 - total_weight:.1f}%")

st.divider()

# =========================================================================== #
# SECTION 4 — Position Sizing Calculator & Scale-in Visualizer
# =========================================================================== #
st.markdown('<div class="section-title">4. Position Sizing Calculator & Scale-in Visualizer</div>', unsafe_allow_html=True)
st.caption(
    f"Risk Capital {RISK_CAPITAL_PCT}% ต่อไม้ | Hard Stop สูงสุด {HARD_STOP_PCT}% จาก Pivot | "
    f"เพดานถือหุ้นตัวเดียว {SINGLE_STOCK_CAP_PCT}% ของพอร์ต | ปัดเศษ Board Lot ขั้นต่ำ 100 หุ้น"
)

calc_col1, calc_col2, calc_col3 = st.columns([1.2, 1.0, 1.0])
with calc_col1:
    portfolio_capital = st.number_input(
        "เงินทุนพอร์ตรวม (บาท)", min_value=100_000, max_value=1_000_000_000, value=1_000_000, step=50_000
    )
with calc_col2:
    symbols_available = [w.symbol for w in watchlist]
    default_idx = symbols_available.index(st.session_state.selected_symbol) if st.session_state.selected_symbol in symbols_available else 0
    selected_symbol = st.selectbox("เลือกหุ้น", symbols_available, index=default_idx)
    st.session_state.selected_symbol = selected_symbol
with calc_col3:
    selected_item: WatchlistItem = next(w for w in watchlist if w.symbol == selected_symbol)
    default_pivot = selected_item.vcp.pivot_price or selected_item.price
    pivot_price = st.number_input("Pivot Point (บาท)", min_value=0.01, value=float(default_pivot), step=0.05, format="%.2f")

if regime.stage == MarketStage.STAGE_4:
    st.error("Stage 4 (Declining): ตลาดบังคับเงินสด 100% — ห้ามคำนวณเปิดไม้ซื้อใหม่")
elif not regime.allow_new_buys:
    st.warning("ตลาดยังไม่อนุญาตให้เปิดไม้ซื้อใหม่ในสถานะปัจจุบัน (ดูส่วนที่ 1) — ตารางด้านล่างเป็นการจำลองเพื่ออ้างอิงเท่านั้น")

plan = build_scale_in_plan(symbol=selected_symbol, portfolio_capital=portfolio_capital, pivot_price=pivot_price)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Risk Capital (1.5%)", f"{plan.risk_capital_baht:,.0f} บาท")
m2.metric("Hard Stop Price", f"{plan.hard_stop_price:,.2f}", f"-{plan.stop_distance_pct:.1f}% จาก Pivot")
m3.metric("จำนวนหุ้นสูงสุด (ตาม Risk)", f"{plan.shares_by_risk_cap:,} หุ้น")
m4.metric("จำนวนหุ้นสูงสุด (ตาม Cap พอร์ต)", f"{plan.shares_by_position_cap:,} หุ้น")

st.markdown(f"**จำนวนหุ้นรวมทั้งแผน (Board Lot 100):** {plan.final_total_shares:,} หุ้น")

plan_rows = []
for step in plan.steps:
    plan_rows.append(
        {
            "ไม้": step.step_name,
            "เงื่อนไขเข้าซื้อ": step.trigger_condition,
            "สัดส่วน": f"{step.allocation_pct:.0f}%",
            "จำนวนหุ้น": f"{step.shares:,}",
            "ราคาเข้า": f"{step.entry_price:,.2f}",
            "จุดตัดขาดทุน": f"{step.stop_price:,.2f}",
            "ความเสี่ยง (บาท)": f"{step.risk_baht:,.0f}",
        }
    )
st.dataframe(pd.DataFrame(plan_rows), use_container_width=True, hide_index=True)

alloc_df = pd.DataFrame(
    {"ไม้": [s.step_name.split(":")[0] for s in plan.steps], "สัดส่วน (%)": [s.allocation_pct for s in plan.steps]}
).set_index("ไม้")
st.bar_chart(alloc_df)

with st.expander(f"ดูกราฟราคาและ Lifecycle/Exit Engine ของ {selected_symbol}"):
    df = universe[selected_symbol]
    st.line_chart(df["close"].rename(f"{selected_symbol} Close"))
    evaluation = evaluate_lifecycle(
        entry_price=pivot_price,
        initial_stop_price=plan.hard_stop_price,
        current_price=selected_item.price,
        daily_df=df,
    )
    e1, e2, e3 = st.columns(3)
    e1.metric("R-Multiple ปัจจุบัน", f"{evaluation.r_multiple_now:.2f}R")
    e2.metric("เป้าหมาย 2R", f"{evaluation.target_2r:,.2f}")
    e3.metric("Chandelier Exit (22d / 3xATR14)", f"{evaluation.chandelier_stop:,.2f}")
    st.write(evaluation.recommended_action)

st.divider()
st.markdown(
    '<p class="disclaimer">⚠️ เครื่องมือนี้ใช้ Mock Data เพื่อสาธิตตรรกะระบบเท่านั้น ไม่ใช่คำแนะนำการลงทุน '
    "สัญลักษณ์หุ้นทั้งหมด (NOVA, ZENITH, ORION, QUARTZ, ATLAS, BOLT, STELLA, VELOX, TRIUM) เป็นชื่อสมมติ "
    "ไม่มีความเกี่ยวข้องกับบริษัทจดทะเบียนจริงแต่อย่างใด</p>",
    unsafe_allow_html=True,
)

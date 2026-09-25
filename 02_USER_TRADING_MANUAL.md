# 02 — User Trading Manual

**Gold Trading & Compounding Accumulation System: Field Operations Manual**
Version 1.2.0 · Pricing unit: USD per troy ounce · Reference FX: **32.50 THB/USD** · Timeframe: 1H execution, 4H context

> Read `01_INVESTMENT_KNOWLEDGE_MANUAL.md` first for the theory. This manual is what to **do**: lookup tables, checklists, rules and one full trade walked from alert to exit. It is not investment advice.

---

## Table of Contents

1. [Quick-Lookup Tables](#1-quick-lookup-tables)
2. [Standard Operating Procedures (SOP)](#2-standard-operating-procedures-sop)
3. [Psychology & Risk Management Rules](#3-psychology--risk-management-rules)
4. [End-to-End Case Study: $4,319 → $4,280 → $4,321](#4-end-to-end-case-study-4319--4280--4321)
5. [Daily / Weekly Routine](#5-daily--weekly-routine)
6. [Trade Journal Template](#6-trade-journal-template)

---

## 1. Quick-Lookup Tables

### 1.1 Formulas (for any entry price not listed)

| Quantity | Formula | Example (0.10 oz @ 4,319, +1.0%) |
|---|---|---|
| Target sell price | `Entry × (1 + g)` | 4,319 × 1.010 = **4,362.19** |
| USD diff (profit) | `(Sell − Entry) × oz` | (4,362.19 − 4,319) × 0.10 = **$4.32** |
| THB profit | `USD diff × USD/THB` | 4.319 × 32.50 = **140.37 THB** |
| Position cost | `Entry × oz` | 4,319 × 0.10 = **$431.90** (14,036.75 THB) |
| Price at −X% | `Entry × (1 − X)` | 4,319 × 0.99 = 4,275.81 |
| Stop loss (R:R gate) | `Swing low − $5` | 4,300.20 − 5 = **4,295.20** |
| R:R | `(Entry × 1.015 − Entry) ÷ (Entry − SL)` | 64.785 ÷ 23.80 = **1 : 2.72** |
| Maximum entry for R:R ≥ 1.5 | `SL ÷ 0.99` | 4,295.20 ÷ 0.99 = **4,338.59** |

> Prices are **wallet execution prices**. Entry is the buy (ask) price you actually paid, and exit is the sell (bid) price you actually receive, so the dealer spread is already included. If you read targets off a mid-price XAU/USD chart instead, add the spread (Manual 01, §1.3).

### 1.2 Target price tables

USD diff and THB profit are computed from unrounded values and then rounded half-up to 2 decimals. THB uses 32.50 THB/USD. Rescale by `your_rate / 32.50` for a different rate.

#### Position size: 0.05 oz (≈ 1.555 g)

| Entry (USD/oz) | Cost (USD) | Cost (THB) | Target | Sell price (USD/oz) | USD diff | THB profit |
|---:|---:|---:|:---:|---:|---:|---:|
| **4,250** | 212.50 | 6,906.25 | +1.0% | 4,292.50 | +$2.13 | +69.06 |
|  |  |  | +1.5% | 4,313.75 | +$3.19 | +103.59 |
|  |  |  | +2.0% | 4,335.00 | +$4.25 | +138.13 |
|  |  |  | +3.0% | 4,377.50 | +$6.38 | +207.19 |
| **4,280** | 214.00 | 6,955.00 | +1.0% | 4,322.80 | +$2.14 | +69.55 |
|  |  |  | +1.5% | 4,344.20 | +$3.21 | +104.33 |
|  |  |  | +2.0% | 4,365.60 | +$4.28 | +139.10 |
|  |  |  | +3.0% | 4,408.40 | +$6.42 | +208.65 |
| **4,300** | 215.00 | 6,987.50 | +1.0% | 4,343.00 | +$2.15 | +69.88 |
|  |  |  | +1.5% | 4,364.50 | +$3.23 | +104.81 |
|  |  |  | +2.0% | 4,386.00 | +$4.30 | +139.75 |
|  |  |  | +3.0% | 4,429.00 | +$6.45 | +209.63 |
| **4,319** | 215.95 | 7,018.38 | +1.0% | 4,362.19 | +$2.16 | +70.18 |
|  |  |  | +1.5% | 4,383.79 | +$3.24 | +105.28 |
|  |  |  | +2.0% | 4,405.38 | +$4.32 | +140.37 |
|  |  |  | +3.0% | 4,448.57 | +$6.48 | +210.55 |
| **4,350** | 217.50 | 7,068.75 | +1.0% | 4,393.50 | +$2.18 | +70.69 |
|  |  |  | +1.5% | 4,415.25 | +$3.26 | +106.03 |
|  |  |  | +2.0% | 4,437.00 | +$4.35 | +141.38 |
|  |  |  | +3.0% | 4,480.50 | +$6.53 | +212.06 |
| **4,400** | 220.00 | 7,150.00 | +1.0% | 4,444.00 | +$2.20 | +71.50 |
|  |  |  | +1.5% | 4,466.00 | +$3.30 | +107.25 |
|  |  |  | +2.0% | 4,488.00 | +$4.40 | +143.00 |
|  |  |  | +3.0% | 4,532.00 | +$6.60 | +214.50 |

#### Position size: 0.10 oz (≈ 3.110 g)

| Entry (USD/oz) | Cost (USD) | Cost (THB) | Target | Sell price (USD/oz) | USD diff | THB profit |
|---:|---:|---:|:---:|---:|---:|---:|
| **4,250** | 425.00 | 13,812.50 | +1.0% | 4,292.50 | +$4.25 | +138.13 |
|  |  |  | +1.5% | 4,313.75 | +$6.38 | +207.19 |
|  |  |  | +2.0% | 4,335.00 | +$8.50 | +276.25 |
|  |  |  | +3.0% | 4,377.50 | +$12.75 | +414.38 |
| **4,280** | 428.00 | 13,910.00 | +1.0% | 4,322.80 | +$4.28 | +139.10 |
|  |  |  | +1.5% | 4,344.20 | +$6.42 | +208.65 |
|  |  |  | +2.0% | 4,365.60 | +$8.56 | +278.20 |
|  |  |  | +3.0% | 4,408.40 | +$12.84 | +417.30 |
| **4,300** | 430.00 | 13,975.00 | +1.0% | 4,343.00 | +$4.30 | +139.75 |
|  |  |  | +1.5% | 4,364.50 | +$6.45 | +209.63 |
|  |  |  | +2.0% | 4,386.00 | +$8.60 | +279.50 |
|  |  |  | +3.0% | 4,429.00 | +$12.90 | +419.25 |
| **4,319** | 431.90 | 14,036.75 | +1.0% | 4,362.19 | +$4.32 | +140.37 |
|  |  |  | +1.5% | 4,383.79 | +$6.48 | +210.55 |
|  |  |  | +2.0% | 4,405.38 | +$8.64 | +280.74 |
|  |  |  | +3.0% | 4,448.57 | +$12.96 | +421.10 |
| **4,350** | 435.00 | 14,137.50 | +1.0% | 4,393.50 | +$4.35 | +141.38 |
|  |  |  | +1.5% | 4,415.25 | +$6.53 | +212.06 |
|  |  |  | +2.0% | 4,437.00 | +$8.70 | +282.75 |
|  |  |  | +3.0% | 4,480.50 | +$13.05 | +424.13 |
| **4,400** | 440.00 | 14,300.00 | +1.0% | 4,444.00 | +$4.40 | +143.00 |
|  |  |  | +1.5% | 4,466.00 | +$6.60 | +214.50 |
|  |  |  | +2.0% | 4,488.00 | +$8.80 | +286.00 |
|  |  |  | +3.0% | 4,532.00 | +$13.20 | +429.00 |


### 1.3 Drawdown reference (0.10 oz)

| Entry | −0.5% price | −0.5% P/L | −1.0% price | −1.0% P/L | −2.0% price | −2.0% P/L |
|---:|---:|---:|---:|---:|---:|---:|
| 4,300 | 4,278.50 | −$2.15 / −69.88 THB | 4,257.00 | −$4.30 / −139.75 THB | 4,214.00 | −$8.60 / −279.50 THB |
| 4,319 | 4,297.41 | −$2.16 / −70.18 THB | 4,275.81 | −$4.32 / −140.37 THB | 4,232.62 | −$8.64 / −280.74 THB |
| 4,350 | 4,328.25 | −$2.18 / −70.69 THB | 4,306.50 | −$4.35 / −141.38 THB | 4,263.00 | −$8.70 / −282.75 THB |

For 0.05 oz, halve every P/L figure.

---

## 2. Standard Operating Procedures (SOP)

The monitoring bot (`04_GOLD_BOT_MONITOR_ENGINE.py`) sends a Telegram **photo alert**. It contains a 60-candle 1H chart with the divergence line drawn on both price and RSI, dashed RSI levels at 30/35/55/70, and a caption with price, signal type, RSI values, your position's P/L in USD and THB, the 4H regime and recommended actions. Bullish alerts also show the **R:R block** (entry, +1.5% target, stop loss, R:R and money at risk for a 0.05 oz lot), and the chart marks the target (green) and stop (red) as dash-dot lines. If the full text is longer than Telegram's caption limit, the recommended actions arrive as a second text message right after the photo.

### 2.1 SOP-A: 🟢 Bullish Divergence alert (ENTRY WATCH)

**Trigger conditions (the bot has already checked these):** price made a lower or equal low (`price2 ≤ price1 × 1.001`), RSI made a higher low (`rsi2 > rsi1`), the first trough was a climax (`rsi1 < 30`), the second trough is still low (`rsi2 ≤ 35`), and the second trough was confirmed within the last 3 closed 1H candles.

**R:R gate (also checked by the bot):** with SL = second-trough low − $5 and target = price × 1.015, the alert is sent only when R:R ≥ 1 : 1.5. A divergence that fails the gate is not sent. The bot re-checks it every poll while the signal is fresh, so it can still arrive later if price pulls back toward the low.

| Step | Action | ✔ |
|---|---|---|
| A1 | **Read the whole caption.** Note the *4H regime* line (BULL RANGE / TRANSITION / BEAR RANGE). | ☐ |
| A2 | **Check the chart.** Is the green line on price sloping **down or flat** and the green line on RSI sloping **up**? Is the second trough near the right edge? | ☐ |
| A3 | **Check the spread** in the wallet. If the round-trip spread is more than half of your intended net target, **skip the trade**. | ☐ |
| A4 | **Wait for the trigger candle.** Buy only after a 1H candle **closes above the high of the second-trough candle**. No close above within 3 candles means the setup has expired. | ☐ |
| A4b | **Re-check R:R at your real buy price.** The alert used the close at alert time; the trigger candle usually lifts the price. Skip the trade if your buy price is above `SL ÷ 0.99` (R:R would fall below 1 : 1.5). Write the SL and your stop mode (Rule R6) in the journal **before** buying. | ☐ |
| A5 | **Size from the 4H regime:** BULL RANGE → full tranche; TRANSITION → half tranche; BEAR RANGE → half tranche, counter-trend scalp rules. | ☐ |
| A6 | **Execute the buy** in the wallet. Record the **actual** execution price and quantity. | ☐ |
| A7 | **Set targets** from §1.2: primary target (+1.0% in BEAR/TRANSITION, +1.5% to +2.0% in BULL) and stretch target (+3.0% in BULL only). Set in-app price alerts at those levels. | ☐ |
| A8 | **Update the bot:** set `ENTRY_PRICE` and `POSITION_OZ` (environment or `--entry-price/--position-oz`) and restart it, so future alerts report your live P/L and the trailing stop starts watching the position (SOP-D). In **hard-stop** mode (R6) also set `INITIAL_STOP_LOSS` to your SL; in **physical-hold** mode leave it unset. | ☐ |
| A9 | **Log the trade** in the journal (§6). | ☐ |

**If you already hold a position** when a bullish alert arrives:

- Position **under water** → **HOLD**. Do not sell (Rule R1). Add only if a second tranche was **written in your plan before** the first entry, and never beyond your maximum allocation.
- Position **in profit** → do nothing. Do not chase a second entry at a worse price.

### 2.2 SOP-B: 🔴 RSI 55 / Bearish Divergence alert (EXIT WATCH)

**Trigger conditions:** price made a higher or equal high (`price2 ≥ price1 × 0.999`), RSI made a lower high (`rsi2 < rsi1`), and the second RSI peak is in or above the **55 exhaustion band** (`rsi2 ≥ 55`). The second peak was confirmed within the last 3 closed candles.

| Step | Action | ✔ |
|---|---|---|
| B1 | **Read the P/L line** in the caption (USD, THB, %). | ☐ |
| B2 | **Classify your position:** (a) ≥ +1.0% net, (b) 0% to +1.0%, (c) below entry, (d) flat (no position). | ☐ |
| B3 | **(a) ≥ +1.0%: TAKE PROFIT.** Sell all, or at least half, now. Trail the rest per Rule R4. | ☐ |
| B4 | **(b) 0% to +1.0%: EXIT / SCRATCH.** Momentum is fading. Close at breakeven or better; do not let a winner become a loser. In a 4H BEAR range this is mandatory. | ☐ |
| B5 | **(c) Below entry: HOLD, DO NOT ADD.** Wait for the next bullish divergence and exit near breakeven on the next rally (Rule R3). | ☐ |
| B6 | **(d) Flat: NO NEW BUY.** Wait for a pullback and a fresh bullish setup. | ☐ |
| B7 | After any sale: **clear `ENTRY_PRICE`** in the bot configuration and restart it. Log the result. | ☐ |
| B8 | **Compounding step:** the next position is sized from the **new total balance**, which is how the Manual 01 model compounds. | ☐ |

### 2.3 SOP-C: Alert housekeeping

| Situation | What to do |
|---|---|
| Two alerts for the **same** pivot | Should never happen: the bot debounces by pivot timestamp and persists state to `gold_bot_state.json`. If it does, check that the state file is writable. |
| No alerts for > 48 h | Normal in quiet trends. Confirm the bot is alive: `systemctl status gold-bot` or `docker logs gold-bot` (Manual 03). |
| Alert arrives while you are away and is > 3 candles old | The setup is stale. Do **not** enter late; wait for the next one. |
| Bullish **and** bearish alerts close together | The market is choppy. Stand aside or trade half size. |

### 2.4 SOP-D: Trailing-stop alerts (open position)

While `ENTRY_PRICE` is set, the bot manages the position's stop on every closed 1H candle and sends a **text message** (no chart) when something changes:

| Alert | When | What to do |
|---|---|---|
| 🛡️ **[ล็อกทุนเรียบร้อย]** | A 1H close at or above entry × 1.010 (+1.0%) | Nothing to sell. Your stop is now the entry price; set an in-app price alert at that level |
| 🚀 **[ยกจุดล็อกกำไรสูงขึ้น]** | On a later candle, the highest close minus 0.5% of entry is above the current stop | Move your in-app price alert up to the new stop. The minimum locked-in profit is shown in USD and THB |
| 🎯 **[สั่งปิดสถานะ]** | A 1H close at or below the stop | **Sell the whole position now** at the wallet's current quote. The message shows the result at the stop level and the estimated result at the current price, which is usually a little worse because the candle closed through the stop |
| After the sale | — | Remove `ENTRY_PRICE` from the bot configuration and restart it. Until you do, the bot treats the position as closed and sends no further trailing alerts for it |

The exit label tells you which case it was: **ล็อกกำไรสำเร็จ** (stop above entry), **ปิดสถานะเท่าทุน** (stop at entry) or **ตัดขาดทุนตาม SL** (the initial hard stop was hit before the +1.0% lock).

The bot remembers the stop, the highest close and the lock in `gold_bot_state.json`. A restart does not reset them, and candles missed while the bot was down are replayed in order when it comes back.

---

## 3. Psychology & Risk Management Rules

### R1. Never panic-sell at RSI < 30 in a physical-backed wallet

In a leveraged account, RSI < 30 during a support break is where margin calls liquidate people. In a **fully paid, 1:1 physical-backed wallet** that mechanism does not exist:

- no margin call, no forced liquidation, no swap fee eating your balance overnight;
- a price below your entry is an **unrealised** mark-to-market loss;
- **the only person who can realise the loss is you**, by pressing *sell*, and RSI < 30 is statistically the worst moment to do it, because forced sellers elsewhere are running out (Manual 01, §4.4).

**Script to repeat to yourself:** *"I own the metal. Nobody can take it. RSI under 30 means sellers are running out. I wait for the bot's divergence and the rally."*

The rule has limits. It does **not** mean "never accept a loss". It means *never at the panic point*. If your thesis is invalid (for example, the 4H regime flips to a confirmed BEAR range and you entered as a BULL-range trade), the planned exit is a rally back to breakeven or a bearish-divergence alert, not the bottom tick.

### R2. Position sizing and allocation caps

| Rule | Value |
|---|---|
| Standard tranche | 0.10 oz (starter tranche 0.05 oz) |
| Maximum open gold for trading | The balance of the compounding account; **never** borrowed money |
| Maximum pre-planned add-on | One additional tranche of equal or smaller size, written down **before** the first entry |
| Emergency reserve | Living expenses are never in the trading wallet |

### R3. Breakeven trade management

A **breakeven exit** (a scratch) is a successful outcome whenever the alternative was a realised loss.

1. After entry, if price has **not** reached +1.0% and a **bearish divergence / RSI 55** alert fires, exit at breakeven or better (SOP-B4).
2. If the position is under water, the next rally that returns price to entry (wallet sell price ≥ entry price) is the default exit. Do not hope for the full target when the 4H regime is bearish.
3. A scratch trade costs time, not capital. Compounding (Manual 01, §2.4) is destroyed by losses, not by scratches.

### R4. Trailing stop guidelines

Most wallets do not support resting stop orders, so these are **mental stops backed by in-app price alerts**. The bot computes them for you (SOP-D):

1. **Break-even lock:** the first 1H close at or above **entry + 1.0%** moves the stop to the entry price.
2. **Trail:** from the next candle on, the stop is the **highest 1H close minus 0.5% of entry**.
3. **Up only:** the stop never moves down.
4. **Exit:** a 1H close **at or below** the stop means sell.

Resulting stop levels (the one-candle lag after the lock aside):

| Highest close reached | Stop | Locked-in result |
|---|---|---|
| +1.0% | Entry (break-even) | 0% |
| +1.5% | Entry + 1.0% | +1.0% |
| +2.0% | Entry + 1.5% | +1.5% |
| +3.0% | Entry + 2.5% | +2.5% |

Example, 0.05 oz @ $4,270 (offset 0.5% × 4,270 = $21.35): lock at $4,312.70 → stop $4,270.00; highest close $4,330.00 → stop **$4,308.65**, locking +$1.93 (≈ +63 THB at 32.50). Only 1H closes count, not intrabar wicks, because wicks through obvious levels are often stop runs (Manual 01, §4.2).

### R5. Behavioural rules

| # | Rule |
|---|---|
| B1 | Enter only on a bot alert **plus** the trigger candle (SOP-A4). No "feel" trades. |
| B2 | Never increase size after a loss to "win it back". |
| B3 | Never override the 4H regime: a BEAR-range long is a scalp with a +1.0% or RSI 55–60 exit. |
| B4 | Stop trading for 48 hours after two consecutive realised losses; review the journal first. |
| B5 | Do not watch 1-minute charts. The system is 1H/4H; lower timeframes only add noise and fear. |

### R6. The R:R stop loss and how it fits with R1

The alert's **SL (swing low − $5)** is the level at which the divergence setup is **invalidated**: the double bottom has failed. The bot uses it to measure risk and to reject poor-value entries. The bot never sells anything; what you do if price closes below the SL is decided **before** entry, as one of two modes:

| Mode | When price **closes** a 1H candle below the SL | Suits |
|---|---|---|
| **Hard stop** | Sell at the next wallet quote. Loss is capped near the planned risk. Set `INITIAL_STOP_LOSS` so the bot sends the 🎯 exit alert. | Traders who want every loss limited to `1R`, as the R:R maths assumes |
| **Physical hold** (R1) | Do not sell into the flush. Stop adding, cancel the original target and switch to the breakeven exit plan (R3). Leave `INITIAL_STOP_LOSS` unset; the bot then only starts protecting the trade after the +1.0% lock. | Fully paid physical holders who accept a longer, deeper drawdown instead of a realised loss |

Rules for both modes:

1. Choose the mode before the buy and write it in the journal. Switching modes during a drawdown is a panic decision, which is exactly what R1 forbids.
2. Intrabar wicks through the SL do not count, only 1H closes. The $5 buffer exists to survive stop hunts (Manual 01, §4.2).
3. In hold mode, the R:R figure is a **measure of the setup**, not a cap on your loss. The possible drawdown is open-ended until the next rally, so hold mode only works with money you will not need for months.

---

## 4. End-to-End Case Study: $4,319 → $4,280 → $4,321

**Setup:** position size 0.10 oz, FX 32.50 THB/USD, all times Indochina Time (ICT, UTC+7). All prices are wallet execution prices (spread included).

### 4.1 Timeline

| # | Time (ICT) | Market event | 1H RSI | Position P/L (0.10 oz) | Decision |
|---|---|---|---:|---|---|
| 1 | Day 1, 08:00 | Bot 🟢 **BULLISH DIVERGENCE**: trough 1 $4,301.40 (RSI 27.6), trough 2 $4,300.20 (RSI 33.4), confirmed 2 candles ago. 4H regime: **BEAR RANGE** (RSI4H 41.8). | 36.9 | — | SOP-A. 4H is a BEAR range, so half-tranche logic applies. The trader's plan allows 0.10 oz as the half of a 0.20 oz full plan. |
| 2 | Day 1, 09:00 | Trigger candle closes at $4,317.60, above the trough-2 candle high ($4,309.80). | 44.2 | — | Trigger confirmed (SOP-A4). |
| 3 | Day 1, 10:00 | **R:R re-check (A4b):** SL = 4,300.20 − 5 = **$4,295.20**; +1.5% target **$4,383.79**; risk $23.80/oz, reward $64.79/oz → **R:R 1 : 2.72 ✔** (max entry $4,338.59). **BUY 0.10 oz @ $4,319.00** (cost $431.90 = 14,036.75 THB). Money at risk to SL: $2.38 / 77.35 THB. Working target in a BEAR range: +1.0% **$4,362.19**, or RSI 55–60 exit if the rally stalls. Stop mode chosen: **physical hold** (R6). | 47.5 | $0.00 | Entry logged; bot restarted with `ENTRY_PRICE=4319 POSITION_OZ=0.10`. |
| 4 | Day 1, 13:00 | Rally stalls at $4,326. Strong USD data at 19:30 is scheduled. | 53.1 | +$0.70 / +22.75 THB | Hold. Below +1.0%, no bearish alert yet. |
| 5 | Day 1, 19:30–21:00 | Data surprise. **$4,300 support breaks** and stop cascades hit (Manual 01, §4.2). Low of **$4,280.00** printed at 21:00 with a long lower wick. | **22.8** | **−$3.90 / −126.75 THB (−0.90%)** | **SL $4,295.20 broken on a 1H close** (first close below: $4,291.00). Pre-chosen mode is physical hold, so per R6: no adds, target cancelled, breakeven exit plan (R3). **Rule R1: no panic sell.** Checklist: fully paid physical ✔, no margin ✔, RSI < 30 = climax zone ✔. HOLD. |
| 6 | Day 1, 22:00–Day 2, 02:00 | Climax bar closes at $4,288.40 (upper half of range). Next 3 candles fail to make a lower low. | 22.8 → 31.0 → 36.4 | −$3.06 → −$2.10 | Selling-climax evidence (Manual 01, §4.4): items 1, 2, 4, 5 and 6 present. |
| 7 | Day 2, 05:00 | Retest low **$4,281.50**. Bot 🟢 **BULLISH DIVERGENCE #2**: trough 1 $4,280.00 (RSI 22.8), trough 2 $4,281.50 (RSI 32.6). Check: 4,281.50 ≤ 4,280.00 × 1.001 = 4,284.28 ✔; 32.6 > 22.8 ✔; 32.6 ≤ 35 ✔; 22.8 < 30 ✔. | 34.9 | −$3.75 / −121.88 THB | SOP-A "already holding, under water" → **HOLD, do not add** (no second tranche was pre-planned). Plan: exit near breakeven on the rally (Rule R3). |
| 8 | Day 2, 09:00–13:00 | Recovery rally through EMA50; RSI crosses 50 at $4,305. | 50.6 → 63.5 | −$1.40 → −$0.06 | Hold. First RSI peak of 63.5 at $4,318.40 (13:00). |
| 9 | Day 2, 14:00–16:00 | Pullback to $4,309, then marginal new high **$4,324.10** at 16:00 with RSI **57.2**. | 57.2 | +$0.51 | Watching the 55–60 exhaustion band (Manual 01, §5.3). |
| 10 | Day 2, 18:00 | Bot 🔴 **BEARISH DIVERGENCE**: peak 1 $4,318.40 (RSI 63.5), peak 2 $4,324.10 (RSI 57.2), confirmed 2 candles ago. Check: 4,324.10 ≥ 4,318.40 × 0.999 = 4,314.08 ✔; 57.2 < 63.5 ✔; 57.2 ≥ 55 ✔. 4H regime still **BEAR RANGE** (RSI4H 52.0). | 53.8 | +$0.20 / +6.50 THB | SOP-B, class (b) 0% to +1.0% in a BEAR range → **EXIT / SCRATCH (mandatory)**. |
| 11 | Day 2, 18:05 | **SELL 0.10 oz @ $4,321.00** (proceeds $432.10 = 14,043.25 THB). | — | **Realised +$0.20 / +6.50 THB (+0.046%)** | Bot reconfigured with no `ENTRY_PRICE`. Journal updated. |

### 4.2 The numbers

| Metric | Value |
|---|---|
| Entry | 0.10 oz @ $4,319.00 → $431.90 (14,036.75 THB) |
| Maximum adverse excursion | $4,280.00 → **−$3.90 / −126.75 THB / −0.90%** |
| Exit | 0.10 oz @ $4,321.00 → $432.10 (14,043.25 THB) |
| Realised result | **+$0.20 / +6.50 THB / +0.046%** |
| Holding time | ~32 hours |
| Trailing stop (SOP-D) | Never activated: the highest 1H close ($4,324.10) stayed below the +1.0% lock at $4,362.19. With `INITIAL_STOP_LOSS` unset (physical hold), the bot sent no stop alerts, and the exit came from the bearish-divergence alert |
| Outcome if panic-sold at the low ($4,280) | −$3.90 / −126.75 THB realised |
| **Value of following Rule R1** | **+$4.10 / +133.25 THB** versus the panic sale |
| Outcome in hard-stop mode (R6) | Sold on the first 1H close below the SL ($4,291.00): **−$2.80 / −91.00 THB** realised, a controlled loss slightly worse than the planned 1R ($2.38) because the close gapped past the stop |

### 4.3 Post-trade review

| Question | Answer |
|---|---|
| Was the entry valid? | Yes. Bot alert + trigger candle close + spread check. |
| Was the size right? | Yes. Half-tranche logic in a 4H BEAR range limited the drawdown to −$3.90. |
| Was the R:R gate right? | Yes. 1 : 2.72 at the real entry. The SL break told the trader the setup had failed. Hold mode then recovered to breakeven, but it carried open-ended risk: had the decline continued, hard-stop mode would have been the better choice. |
| What went wrong? | A scheduled high-impact USD release fell inside the trade window. **Improvement:** avoid new entries within 12 hours of a known tier-1 release when the 4H regime is BEAR. |
| What went right? | R1 (no panic sell at RSI 22.8), R3 (breakeven exit in a BEAR range) and SOP-B were all followed. The bot's 55-band bearish divergence marked the end of the counter-trend rally, as predicted by the 4H-vs-1H conflict rules. |
| Compounding impact | A scratch does not advance `N` (Manual 01, §2), but it does not set it back either. A panic sale would have cost the equivalent of roughly one +1.0% win on a $390 balance. |

---

## 5. Daily / Weekly Routine

| When | Task | Duration |
|---|---|---|
| Morning (ICT) | Check the bot heartbeat (last log line < 2 h old). Read the 4H regime on the last alert or the log. Check the economic calendar for tier-1 USD releases. | 5 min |
| On every alert | Run SOP-A or SOP-B completely. | 5–10 min |
| Evening | Update the journal. Confirm `ENTRY_PRICE` in the bot matches your actual position. | 5 min |
| Weekly | Review win rate, average net gain and scratches. Recalculate `N` and time-to-goal with Manual 01's formula using your **actual** numbers. | 20 min |
| Monthly | Reconcile the wallet balance (grams/oz) with the journal. Review the custodian/platform disclosures. | 20 min |

---

## 6. Trade Journal Template

| Field | Example (case study) |
|---|---|
| Trade # | 2026-09-017 |
| Alert type / time | BULLISH, Day 1 08:00 ICT |
| 4H regime at entry | BEAR RANGE (RSI4H 41.8) |
| Entry price / size | $4,319.00 / 0.10 oz |
| Planned target / exit rule | +1.0% ($4,362.19) or RSI 55–60 bearish-divergence exit |
| Max adverse excursion | $4,280.00 (−0.90%) |
| Exit alert / time | BEARISH, Day 2 18:00 ICT |
| Exit price | $4,321.00 |
| Net result | +$0.20 / +6.50 THB (+0.046%) |
| R:R at entry / SL / stop mode | 1 : 2.72 / $4,295.20 / physical hold |
| Rules followed (R1–R6, SOP) | R1 ✔ R3 ✔ R6 ✔ SOP-A ✔ SOP-B ✔ |
| Lesson | Avoid entries within 12 h of tier-1 USD data in a BEAR range |
| Balance after trade | Previous balance + $0.20 |

---

*End of Manual 02. For system internals and deployment see `03_PROGRAMMER_TECHNICAL_MANUAL.md`.*

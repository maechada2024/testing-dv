# 01 — Investment Knowledge Manual

**Gold Trading & Compounding Accumulation System**
Document class: Academic & practical investment reference · Version 1.1.0 · Base currency: USD per troy ounce (XAU/USD) · Reference FX: 32.50 THB/USD

> **Scope and disclaimer.** This manual explains the asset, the mathematics, the market mechanics and the technical theory behind the system. It is education, not investment advice. Product terms (custodian, spread, minimum order, trading hours) change. Confirm them in the product disclosure inside your wallet app before you commit capital.

---

## Table of Contents

1. [Physical-Backed Digital Gold Assets](#1-physical-backed-digital-gold-assets)
2. [The Compounding Growth Model](#2-the-compounding-growth-model)
3. [Compounding Simulation: $250 → 1.0 oz](#3-compounding-simulation-250--10-oz)
4. [Market Mechanics](#4-market-mechanics)
5. [Technical Theory: RSI Range Rules & Timeframe Conflict](#5-technical-theory-rsi-range-rules--timeframe-conflict)
6. [Glossary](#6-glossary)

---

## 1. Physical-Backed Digital Gold Assets

### 1.1 What the asset is

A **physical-backed digital gold wallet** is a retail account where each unit you buy is a claim on real bullion. A licensed bullion dealer holds that bullion in a vault. One example is the *Gold Wallet* service in Thailand's **Paotang (เป๋าตัง)** app, which works with established Thai bullion houses. This system's operating notes list **MTS Gold (Mae Thong Suk)** and **YLG Bullion** as dealer/custodian examples. The app shows you a price, and your balance is recorded in grams or baht-weight. Behind that balance is metal held in a vault on your behalf.

The model has three layers:

```
┌──────────────────────────┐     ┌───────────────────────────┐     ┌────────────────────────────┐
│  Investor (app balance)  │ ──► │  Platform (order routing, │ ──► │  Bullion dealer/custodian  │
│  grams / oz of gold      │     │  KYC, ledger, payments)   │     │  allocated bars in vault   │
└──────────────────────────┘     └───────────────────────────┘     └────────────────────────────┘
         claim  ◄───────────────────── 1 : 1 backing ─────────────────────────►  metal
```

### 1.2 Allocated 1:1 physical vaulting

| Property | Allocated 1:1 physical (wallet model) | Unallocated / synthetic exposure |
|---|---|---|
| Legal nature | Claim on specific, segregated metal held for customers | General creditor claim on the provider |
| Backing ratio | Every gram sold is matched by a gram in the vault | Fractional; the provider may hedge with derivatives |
| Counterparty risk | Mainly the custodian's operational and legal soundness | The provider's whole balance sheet |
| Redemption | Often convertible to physical bars or ornaments (product-dependent) | Cash settlement only |
| Audit | Periodic vault audits of the bullion inventory | Financial statement audit only |

**Units you will see:**

| Unit | Grams | Troy ounces | Notes |
|---|---:|---:|---|
| 1 troy ounce (oz t) | 31.1035 g | 1.0000 | International pricing unit (XAU/USD) |
| 0.10 oz t | 3.1103 g | 0.1000 | Standard position size in this system |
| 0.05 oz t | 1.5552 g | 0.0500 | Starter position size in this system |
| 1 Thai baht-weight (bullion, 96.5%) | 15.244 g | 0.4901 gross / 0.4730 fine | Thai Gold Traders Association convention |

> The system prices everything in **USD per troy ounce** so that the technical analysis matches global XAU/USD charts. To turn a USD result into Thai baht, multiply by the USD/THB rate (reference 32.50). If your wallet quotes in THB per gram, the USD/THB rate itself also moves your P/L.

### 1.3 Why this structure changes trading behaviour

A fully paid physical holding lacks four features that ruin most leveraged gold traders:

1. **No liquidation risk.** No broker can force-close you. A drawdown is an unrealised mark-to-market loss, not a realised loss.
2. **No margin call.** You paid 100% up front, so nobody can demand more collateral when price falls.
3. **No swap / rollover fee.** CFD and spot-FX gold positions pay or receive overnight financing every day. A fully paid physical balance carries no interest-rate differential, so time does not work against you.
4. **No leverage-driven stop hunting of *your* position.** You can still get stopped out by your own orders, but no margin engine will sell for you at the worst tick.

**The one cost that remains is the dealer spread.** The dealer earns the gap between its buy price and its sell price. Every trade in this manual is measured by **net** gain, meaning after that spread. Gross move needed per swing, as a function of round-trip spread `s`:

$$\text{gross} = \frac{1 + r_{\text{net}}}{1 - s} - 1$$

| Target net gain | Spread 0.30% | Spread 0.50% | Spread 0.80% |
|---|---:|---:|---:|
| +1.0% net | +1.3039% gross | +1.5075% gross | +1.8145% gross |
| +1.5% net | +1.8054% gross | +2.0101% gross | +2.3185% gross |
| +2.0% net | +2.3069% gross | +2.5126% gross | +2.8226% gross |

Check your wallet's live buy/sell quotes before you set targets. A wide spread can make a +1.0% net plan impractical on the 1H timeframe.

### 1.4 Risks that remain

| Risk | Description | Mitigation |
|---|---|---|
| Custodian / platform risk | Operational failure, fraud or insolvency of the dealer or platform | Use regulated, long-established dealers; keep total exposure within your risk budget |
| Spread widening | Spreads widen in fast markets and around holidays | Avoid trading into major news; check the spread before every order |
| Trading-hours gaps | The wallet may quote only during local business hours while XAU/USD trades almost 24/5 | Expect gaps between the wallet's close and reopen |
| FX translation | THB-denominated wallets carry USD/THB exposure | Track P/L in both currencies (the bot's alerts do this) |
| Opportunity cost | Capital tied up in a drawdown cannot compound | Size so that one stuck position never freezes the whole plan |

---

## 2. The Compounding Growth Model

### 2.1 Definitions

| Symbol | Meaning |
|---|---|
| `PV` | Present value: starting capital (USD) |
| `FV` | Future value: target capital (USD) |
| `r` | Net return per completed swing trade (decimal: 1.0% → 0.01) |
| `N` | Number of completed winning swings needed |
| `f` | Trades per month |

### 2.2 Formal derivation of N = ln(FV / PV) / ln(1 + r)

When the full balance is reinvested after every swing, each trade multiplies capital by `(1 + r)`:

$$
\begin{aligned}
C_1 &= PV\,(1+r) \\
C_2 &= C_1\,(1+r) = PV\,(1+r)^2 \\
&\;\;\vdots \\
C_N &= PV\,(1+r)^N
\end{aligned}
$$

Set the terminal capital equal to the goal, `C_N = FV`:

$$FV = PV\,(1+r)^N \quad\Longrightarrow\quad \frac{FV}{PV} = (1+r)^N$$

Take the natural logarithm of both sides. The logarithm is strictly increasing, so the equality holds:

$$\ln\!\left(\frac{FV}{PV}\right) = \ln\!\left((1+r)^N\right) = N \cdot \ln(1+r)$$

Since `r > 0`, `ln(1 + r) > 0`, so we can divide:

$$\boxed{\,N = \dfrac{\ln(FV / PV)}{\ln(1 + r)}\,}$$

`N` is usually not an integer. You cannot complete a fraction of a trade, so the number of trades actually needed is `⌈N⌉` (ceiling).

**Time to goal:**

$$T_{\text{months}} = \frac{\lceil N \rceil}{f}, \qquad T_{\text{years}} = \frac{T_{\text{months}}}{12}$$

**Small-r approximation.** For small `r`, `ln(1+r) ≈ r − r²/2`, which gives the familiar "rule of 72" intuition. The system always uses the exact logarithm.

### 2.3 Worked derivation for this system

- `PV = $250`
- `FV = $4,300` (one troy ounce at the system's reference price)
- `FV / PV = 17.2`
- `ln(17.2) = 2.844909`

| Net gain per swing `r` | ln(1 + r) | N (exact) | ⌈N⌉ trades | Capital after ⌈N⌉ trades |
|---|---:|---:|---:|---:|
| +1.0% | 0.009950 | 285.91 | 286 | $4,303.81 |
| +1.5% | 0.014889 | 191.08 | 192 | $4,359.33 |
| +2.0% | 0.019803 | 143.66 | 144 | $4,328.77 |

### 2.4 Win-rate adjusted model (reality check)

The clean model assumes every swing wins. With a win rate `p`, winners of `+r` and losers of `−1.0%`, the expected log-growth per trade is:

$$g = p\,\ln(1+r) + (1-p)\,\ln(0.99), \qquad N_{\text{eff}} = \frac{\ln(FV/PV)}{g}$$

| r (win) | Win rate 60% | Win rate 70% | Win rate 80% |
|---|---:|---:|---:|
| +1.0% | 1,458.9 trades | 720.2 trades | 478.1 trades |
| +1.5% | 579.1 trades | 384.1 trades | 287.3 trades |
| +2.0% | 361.9 trades | 262.3 trades | 205.7 trades |

**Lesson:** at +1.0% per win, each −1.0% loss cancels one whole win. This is why the system (a) favours breakeven exits over panic cuts, caps risk per trade with the R:R gate (§2.5), and (b) prefers +1.5% or better when the RSI regime allows it. At a 70% win rate with −1% losers, a +1.0% plan needs 720 trades, 2.5× the clean model. A +2.0% plan needs 262 trades.

### 2.5 Risk:reward gate and breakeven win rate

Before a bullish entry, the bot measures the trade's reward against its risk (Manual 03, §5.5):

$$SL = \text{SwingLow} - \$5, \qquad TP = \text{Entry} \times 1.015, \qquad RR = \frac{TP - \text{Entry}}{\text{Entry} - SL}$$

It alerts only when `RR ≥ 1.5`. The minimum R:R sets the win rate at which a strategy stops losing money. If every loss is `1R` and every win is `RR × 1R`, expectancy is zero when:

$$p^{*} = \frac{1}{1 + RR}$$

| R:R | Breakeven win rate `p*` |
|---|---:|
| 1 : 1.0 | 50.0% |
| **1 : 1.5 (system minimum)** | **40.0%** |
| 1 : 2.0 | 33.3% |
| 1 : 2.72 (case study, Manual 02 §4) | 26.9% |
| 1 : 3.0 | 25.0% |

**Maximum entry price.** With the target fixed at `t = +1.5%` and a minimum R:R of `m = 1.5`, the condition `Entry·t ≥ m·(Entry − SL)` rearranges to:

$$\text{Entry} \le SL \cdot \frac{m}{m - t} = \frac{SL}{0.99}$$

For a swing low of $4,300.20 (SL $4,295.20), a new buy passes the gate only at or below **$4,338.59**. Chasing price well above the divergence low is exactly what the gate prevents.

---

## 3. Compounding Simulation: $250 → 1.0 oz

All figures reinvest the full balance, reach the goal at the ceiling trade count, and assume the stated net return per completed swing.

### 3.1 Time to goal by frequency

| Net per swing | Trades needed | 4 trades / month | 6 trades / month | 8 trades / month |
|---|---:|---|---|---|
| **+1.0%** | 286 | 71.5 months (**5.96 years**) | 47.7 months (**3.97 years**) | 35.8 months (**2.98 years**) |
| **+1.5%** | 192 | 48.0 months (**4.00 years**) | 32.0 months (**2.67 years**) | 24.0 months (**2.00 years**) |
| **+2.0%** | 144 | 36.0 months (**3.00 years**) | 24.0 months (**2.00 years**) | 18.0 months (**1.50 years**) |

### 3.2 Capital milestones (trades required)

| Milestone | +1.0% / swing | +1.5% / swing | +2.0% / swing |
|---|---:|---:|---:|
| $500 (2×) | 70 | 47 | 36 |
| $1,000 (4×) | 140 | 94 | 71 |
| $2,000 (8×) | 209 | 140 | 106 |
| $3,000 (12×) | 250 | 167 | 126 |
| $4,300 (1.0 oz) | 286 | 192 | 144 |

### 3.3 Balance-over-time grid (USD)

`Balance = 250 × (1 + r)^(f × months)`

**+1.0% net per swing**

| Frequency | 3 mo | 6 mo | 12 mo | 18 mo | 24 mo | 36 mo |
|---|---:|---:|---:|---:|---:|---:|
| 4 / month | 281.71 | 317.43 | 403.06 | 511.77 | 649.82 | 1,047.65 |
| 6 / month | 299.04 | 357.69 | 511.77 | 732.23 | 1,047.65 | 2,144.65 |
| 8 / month | 317.43 | 403.06 | 649.82 | 1,047.65 | 1,689.05 | **4,390.31** |

**+1.5% net per swing**

| Frequency | 3 mo | 6 mo | 12 mo | 18 mo | 24 mo | 36 mo |
|---|---:|---:|---:|---:|---:|---:|
| 4 / month | 298.90 | 357.38 | 510.87 | 730.29 | 1,043.95 | 2,133.29 |
| 6 / month | 326.84 | 427.28 | 730.29 | 1,248.17 | 2,133.29 | **6,231.68** |
| 8 / month | 357.38 | 510.87 | 1,043.95 | 2,133.29 | **4,359.33** | 18,203.72 |

**+2.0% net per swing**

| Frequency | 3 mo | 6 mo | 12 mo | 18 mo | 24 mo | 36 mo |
|---|---:|---:|---:|---:|---:|---:|
| 4 / month | 317.06 | 402.11 | 646.77 | 1,040.29 | 1,673.23 | **4,328.77** |
| 6 / month | 357.06 | 509.97 | 1,040.29 | 2,122.06 | **4,328.77** | 18,012.63 |
| 8 / month | 402.11 | 646.77 | 1,673.23 | **4,328.77** | 11,198.84 | 74,953.08 |

> **Interpretation.** Figures past the 1.0 oz goal (for example $74,953) show what exponential growth does mathematically. They are **not** forecasts. As the account grows, position sizes stop fitting the dealer's liquidity, spreads and psychology, and the constant-`r` assumption breaks. The plan's operational goal is **one ounce**. Past that point, re-plan with a lower target return and smaller relative position sizes.

### 3.4 Converting the goal into ounces (accumulation view)

The goal is stated in ounces, not dollars, so the dollar target moves with the gold price:

| Gold price (USD/oz) | FV for 1.0 oz | FV / PV | N @ +1.0% | N @ +1.5% | N @ +2.0% |
|---|---:|---:|---:|---:|---:|
| 4,000 | 4,000 | 16.0 | 278.6 | 186.2 | 140.0 |
| 4,300 | 4,300 | 17.2 | 285.9 | 191.1 | 143.7 |
| 4,600 | 4,600 | 18.4 | 292.7 | 195.6 | 147.1 |

The column values follow from `N = ln(FV/250)/ln(1+r)`. If you hold gold between swings (the default in this system), a rising gold price lifts your balance and the ounce target together. The **ounces held** then grow by exactly the net swing return, whatever the dollar price does.

---

## 4. Market Mechanics

### 4.1 Order book execution: Market Buy vs. Market Sell

A limit order book holds resting **bids** (buyers) below resting **asks** (sellers):

```
        ASK side (sellers)                    price       size (oz)
        ─────────────────                     4,302.40      35
                                              4,301.90      18
                                              4,301.30      22   ◄─ best ask
   ═══════════════════ spread = 0.80 ══════════════════════════
                                              4,300.50      25   ◄─ best bid
                                              4,300.00     120   (round-number cluster)
        BID side (buyers)                     4,299.20      40
```

| Order | Consumes | Fills at | Effect on price |
|---|---|---|---|
| **Market Buy** | Resting **asks**, lowest first | Best ask, then higher levels ("walking the book") | Lifts the ask. Large buys push price up |
| **Market Sell** | Resting **bids**, highest first | Best bid, then lower levels | Hits the bid. Large sells push price down |
| Limit Buy (below ask) | Nothing at first; it rests | Its own price or better | Adds liquidity |
| Limit Sell (above bid) | Nothing at first; it rests | Its own price or better | Adds liquidity |

**Slippage** is the gap between the price you expected and your average fill. Example: a market sell of 60 oz into the book above fills 25 oz @ 4,300.50 and 35 oz @ 4,300.00. The average fill is **4,300.21**, not the quoted 4,300.50. In a retail wallet you do not see this book, but the dealer's quote is built on the same wholesale mechanics. That is why spreads widen when the book is thin.

### 4.2 Stop-loss cascading

Traders cluster protective sell-stops just **below** obvious support: round numbers, prior swing lows, and the lower edges of ranges. When price reaches that zone:

1. The first stops trigger and become **market sell** orders.
2. They eat through the bids and push price down to the next cluster.
3. Those stops trigger too, and the chain feeds on itself. Leveraged longs hit margin thresholds and brokers liquidate them, adding more market sells.
4. The move is fast, on high volume, with long lower wicks or large-bodied red candles.

```
Price
4,320 ┤ ▆▆▅
4,310 ┤    ▆▄
4,300 ┤ ── ── ─▇── support (visible to everyone) ── ── ── ──
4,295 ┤          ▓  ◄ stop cluster #1 triggers (market sells)
4,288 ┤          ▓  ◄ stop cluster #2 + margin liquidations
4,280 ┤          ▓▁ ◄ exhaustion: sellers run out, long lower wick
4,290 ┤            ▅▆ ◄ rebound as short-covering + value buyers step in
```

### 4.3 Panic selling at a support break ($4,300 example)

The **$4,300** level is both a round number and, in this system's case study, a prior range floor. When it breaks:

| Participant | Behaviour at the break | Consequence |
|---|---|---|
| Leveraged CFD longs | Stopped out or margin-liquidated | Forced market sells |
| Breakout shorts | Sell-stop entries trigger below support | More market sells |
| Retail physical holders | See a "break" and sell in fear | Late, emotional market sells at the worst price |
| Institutions / value buyers | Wait for forced selling to exhaust | Absorb supply with limit bids lower down |

**Physical-backed implication:** the wallet holder has no margin and no forced liquidation. The only way to turn a panic flush into a realised loss is to press *sell* yourself. The system's rule (Manual 02, §3.1) is never to panic-sell into RSI < 30 in a physical-backed wallet.

### 4.4 Selling climax identification

A **selling climax** is the point where forced and emotional selling runs out. It often marks a tradeable low. Checklist (the more items present, the stronger the evidence):

| # | Evidence | How to observe it |
|---|---|---|
| 1 | Extended decline into support | Several consecutive lower lows, price well below EMA50 |
| 2 | Wide-range bar(s) | Candle range ≥ 2× the 14-bar ATR |
| 3 | Volume / tick-activity spike | Volume ≥ 2× its 20-bar average (where volume is available) |
| 4 | Long lower wick / close off the lows | Close in the upper half of the climax bar's range |
| 5 | RSI deeply oversold | 1H RSI(14) < 30, often < 25 |
| 6 | Follow-through failure | The next 1–3 bars **fail** to make a meaningfully lower low |
| 7 | Bullish RSI divergence on the retest | Retest low ≤ climax low (+0.1%), RSI higher and ≤ 35 → **the bot's BULLISH signal** |

The bot automates item 7, the most objective confirmation. The first trough (`RSI < 30`) is the climax. The second trough (`RSI ≤ 35` and higher than the first) is the **secondary test**. The **freshness filter** (the second pivot must be confirmed within the last 3 closed candles) makes sure you act on the retest while it is still actionable.

---

## 5. Technical Theory: RSI Range Rules & Timeframe Conflict

### 5.1 Wilder's RSI in one paragraph

J. Welles Wilder Jr. (1978) defined RSI as `RSI = 100 − 100/(1 + RS)`, where `RS` is the ratio of smoothed average gains to smoothed average losses over `n = 14` periods. His smoothing (RMA) is an exponential moving average with `α = 1/n`, seeded with a simple average. Manual 03 gives the exact formulas the bot implements.

### 5.2 Constance Brown / Andrew Cardwell RSI range rules

Andrew Cardwell (and Constance Brown in *Technical Analysis for the Trading Professional*) observed that RSI does **not** oscillate symmetrically around 50. **The trend decides which range RSI lives in:**

| Regime | RSI(14) typical range | Support zone | Resistance zone | Meaning of "30" and "70" |
|---|---|---|---|---|
| **Bull market range** | 40 – 80 (to 90) | **40 – 50** holds on pullbacks | 80 – 90 | RSI 70 is *normal strength*, not a sell |
| **Bear market range** | 20 – 60 (to 65) | 20 – 30 | **55 – 65** caps rallies | RSI 30 is *normal weakness*, not a buy |
| Transition | Breaks out of one range into the other | — | — | Regime change: failure of 40 in a bull range, or a push through 65 in a bear range |

**Practical rules derived for this system:**

1. **Range shift is the first trend signal.** In a bear range, an RSI rally that stalls at 55–60 and rolls over confirms the bear trend. The first rally that closes above 65 and whose pullback then holds 40 is the first hint of a bull range.
2. **Divergence quality depends on the range.** A bearish divergence whose second peak sits in the **55–60 band** during a bear range is a high-quality exhaustion signal (the bot's `rsi2 ≥ 55` rule). In a bull range, the same divergence usually produces only a pullback to RSI 40–50.
3. **Positive and negative reversals (Cardwell).** A *positive reversal* is a higher RSI low paired with a *higher* price low, and it signals trend continuation up. It is the mirror image of classic bullish divergence. The bot detects only classic divergence. Read reversals by eye as confirmation.

The bot measures the regime on the **4H** RSI over its last 30 bars: `min ≥ 40 → BULL_RANGE`, `max ≤ 60 → BEAR_RANGE`, otherwise `TRANSITION`. It prints this with every alert.

### 5.3 Timeframe conflict resolution: 4H bearish trend vs. 1H oversold rebound

The most common real-world situation: the **4H chart is in a bear range** (price below EMA50, 4H RSI capped under 60) while the **1H chart prints an oversold bullish divergence**. The two timeframes disagree. Resolution framework:

| Question | 4H (context / "tide") | 1H (execution / "wave") |
|---|---|---|
| What is it for? | Direction and expectation | Timing |
| Who wins on direction? | **4H** | — |
| Who wins on timing? | — | **1H** |

**Decision matrix:**

| 4H regime | 1H signal | Action | Target | Expectation |
|---|---|---|---|---|
| BULL range | Bullish divergence | Full planned tranche | +1.5% to +2.0% (or +3.0%) | Trend-aligned; RSI 40–50 support should hold |
| TRANSITION | Bullish divergence | Half tranche | +1.0% to +1.5% | Mixed; take the first target |
| **BEAR range** | **Bullish divergence** | **Counter-trend scalp only** | **+1.0%, or exit at 1H RSI 55–60** | The rebound will likely stall at the 1H RSI 55–60 band and the 4H EMA50 |
| BEAR range | Bearish divergence | No buys; exit any open long near breakeven | — | Trend-aligned downside |
| BULL range | Bearish divergence | Take partial profit; trail the rest | — | Likely a pullback, not a reversal |

**Why the 55–60 band is the exhaustion zone in a conflict:** during a 4H downtrend, 1H rallies are counter-trend. In Cardwell's terms, the 1H RSI of a counter-trend rally inside a larger bear regime tends to peak where the bear-range resistance sits, **55–60** (occasionally 65). Once the 1H RSI reaches 55–60, especially with a bearish divergence (`rsi2 < rsi1`, `rsi2 ≥ 55`), the rebound has probably done its work. This is where the bot's bearish rule and the **RSI 55 exit alert** fire.

### 5.4 RSI shift exhaustion zones (summary map)

```
RSI
100 ┤
 80 ┤ ░░░░░░ Bull-range overbought: trim only if bearish divergence
 70 ┤ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ (chart reference line)
 65 ┤ ▓▓▓▓▓▓ Bear-range ceiling (a close above = regime shift warning)
 60 ┤ ▓▓▓▓▓▓ ┐
 55 ┤ ▓▓▓▓▓▓ ┘ EXHAUSTION BAND: counter-trend rallies die here → bearish-divergence exits
 50 ┤ ──────── midline
 40 ┤ ▒▒▒▒▒▒ Bull-range support (pullbacks hold 40–50 in uptrends)
 35 ┤ ─ ─ ─ ─ Bullish divergence ceiling for the second trough (rsi2 ≤ 35)
 30 ┤ ─ ─ ─ ─ Climax threshold for the first trough (rsi1 < 30)
 20 ┤ ░░░░░░ Bear-range floor / capitulation
  0 ┤
```

---

## 6. Glossary

| Term | Definition |
|---|---|
| **Allocated gold** | Specific bars segregated and held for customers; not on the custodian's balance sheet |
| **ATR** | Average True Range: Wilder-smoothed average of `max(H−L, abs(H−C₋₁), abs(L−C₋₁))` |
| **Breakeven** | Exit price at which net P/L after spread is zero |
| **Bullish divergence** | Price makes a lower or equal low while RSI makes a higher low |
| **Bearish divergence** | Price makes a higher or equal high while RSI makes a lower high |
| **EMA** | Exponential moving average, `α = 2/(span+1)`; the system uses EMA50 and EMA200 |
| **Freshness** | Requirement that the second pivot of a divergence is confirmed within the last 3 closed candles |
| **Net gain per swing** | Percentage return of one completed buy→sell cycle after the dealer spread |
| **Pivot** | Local swing high or low found with `scipy.signal.find_peaks` (distance ≥ 5 bars, ATR-scaled prominence) |
| **RMA / Wilder smoothing** | `RMA_t = RMA_{t−1} + (x_t − RMA_{t−1})/n`, the EMA with `α = 1/n` |
| **Selling climax** | Capitulation low where forced selling exhausts, often followed by a secondary test |
| **Swap fee** | Overnight financing charged or paid on leveraged positions; absent in fully paid physical |
| **Troy ounce** | 31.1034768 g, the international unit for precious metals |

---

*End of Manual 01. Continue with `02_USER_TRADING_MANUAL.md` for operating procedures.*

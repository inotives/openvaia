# ES-0016 — DCA Grid + Regime Trading on Crypto.com

## Status: DRAFT

## Problem

Current strategies on Crypto.com (ES-0012) always execute as **taker** orders — paying 0.48% per fill. With round-trip fees of 0.96% (taker both sides), day trading is unprofitable and swing trading margins are thin.

Meanwhile, **maker** orders (limit orders resting on the book) cost only 0.24%. A DCA Grid strategy places limit orders at pre-calculated levels and waits for fills — all fills are **maker**. Combined with regime-switching, this halves our fee costs while trading the most appropriate style for current market conditions.

Reference: `docs/plans/hybrid_dca_grid_trading_bots.md`

## Goal

Implement a Hybrid DCA Grid + Regime-Switching system on Crypto.com that:
- Uses **maker orders only** (0.24% per fill vs 0.48% taker)
- Switches between grid (sideways) and trend (trending) based on regime score
- Operates autonomously on BTC/USD, ETH/USD, SOL/USD, XRP/USD
- Targets 1-5 grid fills per day in ranging markets

## Fee Advantage

| Order Type | Current Fee | Round-trip | Day Trade Viable? |
|-----------|-------------|-----------|-------------------|
| Taker (current) | 0.48% | 0.96% | No — need >0.96% per trade |
| **Maker (grid)** | 0.24% | **0.48%** | Better — need >0.48% per trade |
| Maker (Lvl 3, 10K CRO staked) | 0.20% | **0.40%** | Yes — 0.5% target nets +0.10% |
| Maker (Lvl 5, 50K CRO staked) | 0.12% | **0.24%** | Easily viable |

Even at current tier, maker-only cuts round-trip from 0.96% to 0.48% — a 50% reduction.

## System Design

```
                     ┌─────────────────────────┐
                     │    Regime Score (RS)     │
                     │    Computed daily        │
                     │    + Sentiment Score     │
                     └──────────┬──────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
         RS 0-60                             RS 60+
              │                                   │
    ┌─────────▼─────────────────┐    ┌───────────▼──────────┐
    │   DCA Grid                 │    │  Trend Follow         │
    │                            │    │  Single entry          │
    │   RS 0-30: Batch Grid      │    │  Trailing stop         │
    │   RS 30-60: Adaptive FIFO  │    │  Ride the trend        │
    │                            │    │                        │
    │   + Sentiment adjustments  │    │  Uses freed capital    │
    │   + Maker orders only      │    │  from cancelled grid   │
    └────────────────────────────┘    └────────────────────────┘

    Transition: grid TPs keep running, unfilled levels cancelled
                trend exits via trailing stop, grid resumes after
```

### Capital Allocation by Regime

| RS Range | Market State | Active Strategy | Grid Mode |
|----------|-------------|----------------|-----------|
| 0-30 | Deep bear / crash | Grid only | Batch Grid |
| 30-55 | Sideways / ranging | Grid only | Adaptive FIFO Grid |
| 55-65 | **Hysteresis zone** | Whichever was last active continues | No switching |
| 65+ | Trending | **Trend Follow only** | Grid paused |

Clean separation with hysteresis buffer (±5 around RS 60):
- Grid **pauses** when RS rises above **65** (not 60)
- Grid **resumes** when RS drops below **55** (not 60)
- Between 55-65: no switching — prevents whipsaw churn

```
Example: RS oscillates around 60

Without hysteresis:        With hysteresis (±5):
RS 58 → Grid              RS 58 → Grid
RS 62 → Trend (switch!)   RS 62 → Grid (still below 65)
RS 57 → Grid (switch!)    RS 57 → Grid
RS 63 → Trend (switch!)   RS 66 → Trend (crossed 65, NOW switch)
RS 59 → Grid (switch!)    RS 59 → Trend (still above 55)
= 4 switches, order churn  RS 53 → Grid (crossed 55, NOW switch)
                           = 2 switches, clean transitions
```

### Regime Transition Rules

**Regime rises above 65 (grid → trend):**
```
Open grid cycle exists:
  1. Cancel all UNFILLED buy levels (no more buying into a trend)
  2. KEEP filled levels' TP sell orders (trend up = TPs fill faster!)
  3. Wait for remaining TPs to fill naturally
  4. Free capital from cancelled levels → available for trend follow

Trend Follow:
  5. Activates with freed capital
  6. Enters on breakout/golden cross per ES-0012 trend_follow strategy
```

The grid actually benefits from regime going up — sell orders fill faster. No need to panic-close.

**Regime drops below 55 (trend → grid):**
```
Trend Follow position exists:
  1. Let open position exit via trailing stop (DON'T hard close)
  2. Trailing stop naturally locks in profit as trend weakens

Grid:
  3. Resume opening new grid cycles with available capital
  4. Mode auto-selected: RS < 30 → Batch, RS 30-55 → FIFO
```

No hard transitions — both sides exit gracefully.

**Example: Regime transition mid-cycle**
```
RS = 45 (ranging): Adaptive FIFO Grid running
  Level 1 ($82,749): open (unfilled)
  Level 2 ($81,498): filled → TP sell at $82,720
  Level 3 ($80,247): filled → TP sell at $81,451
  Level 4 ($78,996): open (unfilled)
  Level 5 ($77,744): open (unfilled)

RS rises to 66 (crossed 65 threshold → trending):
  Cancel: Level 1, 4, 5 buy orders (unfilled → no fee to cancel)
  Keep: Level 2 TP at $82,720, Level 3 TP at $81,451
  → Price trending up → Level 3 TP fills at $81,451 ✓
  → Price keeps going → Level 2 TP fills at $82,720 ✓
  → Grid cycle naturally closed, all profits banked

  Meanwhile: Trend Follow activates with freed capital
  → Enters long at breakout → rides the trend
```

### Capital Scaling Rules

- **Batch Grid:** capital set at cycle open only — no mid-cycle resizing. Sentiment applies on next cycle.
- **Adaptive FIFO Grid:** filled levels are locked. Unfilled levels can be cancelled and replaced mid-cycle when sentiment changes or regime transitions. New params apply to replacement levels only.
- **Regime transition:** unfilled levels cancelled immediately, filled levels run to completion. No capital is "stuck".

## DCA Grid Strategy

### Two Grid Modes

The system supports two grid modes. Robin switches between them based on market conditions.

| Mode | Sell Behavior | Mid-Cycle Sentiment Adjustment | Best For |
|------|-------------|-------------------------------|----------|
| **Batch Grid** | Sell all at avg entry + target (one order) | Wait for cycle end, apply on next | Downtrend — lower TP exits faster on bounces |
| **Adaptive FIFO Grid** (default) | Sell per-level independently + sentiment adjusts unfilled levels | Adjust unfilled levels immediately | Ranging/sideways — captures partial recoveries |

**Auto-selection by regime:**
```
Regime 0-30 (deep bear):   Batch Grid — need fast exits on any bounce
Regime 30-60 (ranging):    Adaptive FIFO Grid — capture partial recoveries + sentiment adaptation
```

### How It Works

Place **5 limit buy orders** below current price, spaced by ATR. When price drops, orders fill at lower prices. How they exit depends on the grid mode.

All grid orders are **maker** (limit orders resting on book).

### Grid Level Calculation

```
grid_spacing_pct = (ATR(14) / current_price × 100) × atr_multiplier

ATR multiplier by volatility:
  low volatility:    0.4 (tight grid, more fills)
  normal:            0.5
  high:              0.7 (wide grid, safety margin)
  extreme:           — (don't enter, too risky)
```

**Example: BTC at $84,000, ATR(14) = $2,500, normal volatility**

```
grid_spacing = (2500 / 84000 × 100) × 0.5 = 1.49%

Capital per cycle = $100 (10% of $1000)
Weights = [1, 1, 2, 3, 3] → total = 10

Level 1: $84,000 × (1 - 1×0.0149) = $82,749  capital = $10
Level 2: $84,000 × (1 - 2×0.0149) = $81,498  capital = $10
Level 3: $84,000 × (1 - 3×0.0149) = $80,247  capital = $20
Level 4: $84,000 × (1 - 4×0.0149) = $78,996  capital = $30
Level 5: $84,000 × (1 - 5×0.0149) = $77,744  capital = $30

Stop loss = Level 5 × (1 - spacing) = $77,744 × 0.9851 = $76,586

Stop-loss is placed as a real exchange trigger order (see "Exchange-Side Stop-Loss" section).
Executes in milliseconds on the exchange, even if our system is down.
```

Deeper levels get more capital (weights [1,1,2,3,3]) — buying more aggressively at better prices.

### Take Profit — Batch Grid Mode

All filled levels share one sell order at weighted average entry + target.

```
If levels 1-3 filled:
  Total BTC = qty1 + qty2 + qty3
  Total cost = $10 + $10 + $20 = $40
  avg_entry = $40 / total_qty

  profit_target = 1.5% (normal volatility)
  target_sell = avg_entry × (1 + 0.015 + maker_fee)

  → ONE limit sell order at target_sell → maker fee
  → Price must reach avg + 1.5% to exit everything
```

Best in downtrends: avg_entry is lower than any individual level, so TP is easier to reach on a bounce.

**TP order updates on each fill:** When a new level fills, the avg_entry changes. Cancel the old TP sell order (no fee) and place a new one at the updated avg_entry + target. See "Take-Profit Order Lifecycle" in the Maker Execution section for full flow.

### Take Profit — Adaptive FIFO Grid Mode (default)

Each filled level gets its **own independent sell order** at that level's entry + target.

```
Level 1 fills at $82,749 → place sell at $82,749 × 1.015 = $83,990
Level 2 fills at $81,498 → place sell at $81,498 × 1.015 = $82,720
Level 3 fills at $80,247 → place sell at $80,247 × 1.015 = $81,451

Price recovers to $81,451:
  → Level 3 TP fills → pocket 1.5% on $20 ✓ (deepest level exits first)
  → Levels 1 & 2 still open, waiting for their individual TPs

Price recovers to $82,720:
  → Level 2 TP fills → pocket 1.5% on $10 ✓
  → Level 1 still waiting

Price drops back down:
  → Level 3 & 2 profits already banked
  → Only Level 1 ($10) at risk
```

Best in ranging markets: captures partial recoveries. Deeper levels (bigger capital) exit first at lower prices.

### Sentiment Mid-Cycle Adjustment (FIFO only)

FIFO's per-level independence enables mid-cycle adaptation:

```
5 levels placed. Levels 1-2 filled, levels 3-5 unfilled.

Sentiment shifts from neutral → extreme fear:
  Levels 1-2: untouched — their TPs are already placed, let them run
  Levels 3-5: CANCEL → replace with contrarian params:
    - Wider spacing (0.7× ATR instead of 0.5×)
    - Bigger capital (1.5× normal per level)
    - Higher TP target (2.5% instead of 1.5%)

No disruption to filled positions. Only unfilled orders are adjusted.

Sentiment shifts to extreme greed:
  Levels 1-2: keep running to their TPs (already filled, let them profit)
  Levels 3-5: CANCEL entirely (don't buy more in euphoria)
  No new cycles until greed subsides
```

This is impossible with Batch Grid (all levels tied to one avg_entry/TP).

### Mode Comparison Summary

```
BTC drops from $84K → $78K → bounces to $81K → drops to $76K

Batch Grid:
  All 5 fill. avg_entry = $79,438. TP at $80,630.
  Bounce to $81K → TP fills → sell ALL → +$1.02 net ✓
  Clean exit before next drop.

Adaptive FIFO Grid:
  All 5 fill. Each has own TP.
  Bounce to $81K:
    Level 5 ($77,744 → TP $78,910) fills → +$0.45 ✓
    Level 4 ($78,996 → TP $80,181) fills → +$0.15 ✓
    Level 3 ($80,247 → TP $81,451) NOT reached
    Levels 1-2 NOT reached
  Drop to $76K → stop-loss on remaining $40 → -$2.43 ✗

  FIFO lost because shallow levels couldn't exit.

Score: Batch wins in downtrend. FIFO wins in ranging.
→ Auto-select by regime: RS 0-30 = Batch, RS 30-60 = FIFO
```

### Entry Conditions

All must pass before opening a new grid cycle:

| Condition | Default | Purpose |
|-----------|---------|---------|
| RS < 65 (pause threshold) | Required | Grid pauses at RS 65, resumes at RS 55 (hysteresis) |
| RSI(14) < 60 | Required | Don't enter overbought |
| ATR% < 6% | Required | Skip volatility spikes |
| No active cycle | Required | One active cycle per asset. "transition_pending" cycles (TPs running from regime change) don't count — new grid can open alongside them. |
| Price > SMA(200) | Optional | Avoid sustained bear (configurable) |
| SMA(50) > SMA(200) | Optional | Golden cross confirms uptrend |

### Grid Cycle State

Tracked in `orders` table + strategy metadata:

**Batch Grid state:**
```json
{
  "cycle_id": "grid-btc-20260405-001",
  "mode": "batch",
  "levels": [
    {"level": 1, "price": 82749, "qty": 0.000121, "status": "open", "order_id": 42},
    {"level": 2, "price": 81498, "qty": 0.000123, "status": "filled", "order_id": 43},
    {"level": 3, "price": 80247, "qty": 0.000249, "status": "open", "order_id": 44}
  ],
  "avg_entry": 81498,
  "total_filled": 0.000123,
  "take_profit_price": 82720,
  "take_profit_order_id": 50,
  "stop_loss_price": 76586,
  "sentiment_at_open": 0.0,
  "opened_at": "2026-04-05T10:00:00Z"
}
```

**Adaptive FIFO Grid state:**
```json
{
  "cycle_id": "grid-btc-20260405-002",
  "mode": "adaptive_fifo",
  "levels": [
    {"level": 1, "price": 82749, "qty": 0.000121, "status": "open", "buy_order_id": 42, "sell_order_id": null},
    {"level": 2, "price": 81498, "qty": 0.000123, "status": "filled", "buy_order_id": 43, "sell_order_id": 51, "tp_price": 82720},
    {"level": 3, "price": 80247, "qty": 0.000249, "status": "filled", "buy_order_id": 44, "sell_order_id": 52, "tp_price": 81451},
    {"level": 4, "price": 78996, "qty": 0.000380, "status": "open", "buy_order_id": 45, "sell_order_id": null},
    {"level": 5, "price": 77744, "qty": 0.000386, "status": "open", "buy_order_id": 46, "sell_order_id": null}
  ],
  "levels_sold": [3],
  "stop_loss_price": 76586,
  "sentiment_at_open": -0.3,
  "sentiment_current": -0.85,
  "last_sentiment_adjustment": "2026-04-05T14:00:00Z",
  "opened_at": "2026-04-05T10:00:00Z"
}
```

Key differences:
- FIFO tracks `buy_order_id` + `sell_order_id` per level (each independent)
- FIFO tracks `levels_sold` (which levels already took profit)
- FIFO tracks `sentiment_current` for mid-cycle adjustment decisions
- Batch has one `take_profit_order_id` for the entire position

Cycle status values: `active` → `transition_pending` → `expired_pending` → `closed`
- `active`: grid running, accepting fills
- `transition_pending`: regime changed, unfilled cancelled, TPs running
- `expired_pending`: 72h expired, unfilled cancelled, TPs + stop running on exchange
- `closed`: all orders settled, P&L logged

### Volatility Regime Adaptation

| Volatility | ATR Multiplier | Grid Spacing | Profit Target | Levels |
|-----------|---------------|-------------|---------------|--------|
| Low (ATR% < 2%) | 0.4 | Tight | 1.0% | 5 |
| Normal (2-4%) | 0.5 | Standard | 1.5% | 5 |
| High (4-6%) | 0.7 | Wide | 2.5% | 5 |
| Extreme (>6%) | — | No entry | — | — |

### Defensive Grid Mode

When normal entry conditions fail (downtrend) but RSI < 30 (oversold bounce signal):

```
Open defensive grid:
  atr_multiplier = 0.8 (wider spacing)
  profit_target = 2.5% (higher reward for risk)
  weights = [1,1,1,1,1] (equal, conservative)
```

## Trend Follow Component

When RS >= 61, the existing `trend_follow` strategy from ES-0012 activates. But modified for maker execution:

### Maker-Only Trend Entry

Instead of market order at breakout:
```
Current (taker): buy immediately at market → 0.48% fee
New (maker): place limit order at breakout price → wait for pullback fill → 0.24% fee
```

Trade-off: might miss some breakouts if price doesn't pull back. But saves 0.24% per trade.

### Trailing Stop as Limit

```
Current: poller monitors price, sends market sell → taker
New: place limit sell at trailing stop level, update each cycle → maker if filled
     Fallback: if price gaps below stop, market sell → taker (safety net)
```

## Cycle Management

### Grid Lifecycle

```
1. EVALUATE: check regime (< 60), sentiment, entry conditions
2. SELECT MODE: RS 0-30 → Batch Grid, RS 30-60 → Adaptive FIFO Grid
3. OPEN: place 5 limit buy orders on exchange (all maker)
4. MONITOR: every 60s, private poller checks fills
5. FILL:
   Batch: recalculate avg_entry → place/update single TP sell order
   FIFO: place individual TP sell order for the filled level
6. CLOSE (happy path): TP fills → log P&L → cycle complete
7. CLOSE (stop-loss): price below stop → cancel all open orders → market sell → log loss
8. CLOSE (regime transition): RS rises above 65 → see transition rules below
9. EXPIRE (72h timeout): see cycle expiry rules below
10. COOLDOWN: wait 30 min before opening new cycle (applies after normal close or stop-loss, NOT after regime transition or expiry)
```

### Cycle Expiry (72h Max Duration)

When a cycle reaches max duration without TP or stop filling:

```
72h reached:
  1. Cancel all unfilled buy orders on exchange (no fee)
  2. KEEP all filled levels' TP sell orders on exchange
  3. KEEP the shared stop-loss trigger order on exchange
  4. Mark cycle as "expired_pending"
  5. Free capital from cancelled unfilled levels
  6. New cycle CAN open alongside expired_pending cycle

TP fills later (price eventually recovers):
  → Poller detects TP fill → cancel stop → log profit
  → expired_pending cycle fully closed

Stop triggers later (price crashes):
  → Exchange executes market sell → poller detects → cancel TPs → log loss
  → expired_pending cycle fully closed
```

**Cap: max 2 expired_pending cycles per asset.**

```
Cycle 1: expired_pending (TPs at $82,720, $81,451 + stop at $76,586)
Cycle 2: expired_pending (TPs at $83,500, $82,200 + stop at $77,100)
Cycle 3: about to expire...

  → Force-close Cycle 1 first (oldest):
    Cancel all remaining TPs + stop on exchange
    Market sell any remaining position (taker fee)
    Log loss/profit on forced close

  → Then Cycle 3 becomes expired_pending (now only 2)
```

This prevents unlimited capital lockup while giving positions a chance to profit. The exchange-side stop-loss ensures risk is capped even on expired_pending cycles.
```

### Regime Transition Lifecycle

```
Grid active, RS rises above 65:

  Batch Grid:
    1. Cancel all unfilled buy orders on exchange
    2. Keep TP sell order — trend helps it fill faster
    3. If TP fills → cycle closed naturally ✓
    4. If price keeps rising past TP → done, profit banked
    5. If price reverses before TP → stop-loss still active as safety net
    6. Mark cycle as "transition_pending" until TP or stop hits

  Adaptive FIFO Grid:
    1. Cancel all unfilled buy levels on exchange
    2. Keep all filled levels' individual TP sell orders
    3. TPs fill progressively as trend pushes price up ✓
    4. Each TP fill = independent profit locked
    5. Mark cycle as "transition_pending" with list of remaining TPs

  Trend Follow:
    6. Activates with capital freed from cancelled unfilled levels
    7. Does NOT wait for grid TPs to complete — runs in parallel
    8. Grid TPs and trend position coexist until grid cycle naturally closes

Grid resumes, RS drops below 55:

  Trend Follow:
    1. Let position exit via trailing stop (don't force close)
    2. Capital returns as trailing stop fills

  Grid:
    3. If no "transition_pending" cycle → open new cycle
    4. If old cycle still has pending TPs → wait for them to close first
    5. Select mode based on new RS: < 30 = Batch, 30-60 = FIFO
```

### Robin's Workflow

```
Every 5 min:
  1. Check regime score + current mode (grid or trend)

  Grid mode active (RS last crossed below 55):
    2. If RS >= 65 → TRANSITION: cancel unfilled, keep TPs, switch to trend
    3. If no active cycle → check sentiment + entry conditions → open new grid
    4. If cycle open → check fills → update TPs (Batch: recalc avg, FIFO: per-level)
    5. If FIFO + sentiment changed → adjust unfilled levels
    6. If TP fills → log P&L, cancel matching stop-loss order on exchange
    7. If stop-loss triggers on exchange → cancel TP order, log loss

  Trend mode active (RS last crossed above 65):
    2. If RS < 55 → TRANSITION: let trend exit via trailing stop, switch to grid
    3. Trend follow managed by ES-0012 strategy
    4. Check transition_pending grid TPs → if filled, log and close

  Both modes:
    5. If exchange stop-loss triggered → detected by private poller → cancel matching TP → log loss
```

## Maker-Only Execution Model

The key advantage of DCA Grid: **both entry and exit are maker orders**.

### Fee Comparison

| Execution | Entry | Exit | Round-trip | Per $100 trade |
|-----------|-------|------|-----------|---------------|
| Current (both taker) | 0.48% | 0.48% | **0.96%** | $0.96 fees |
| Grid (both maker) | 0.24% | 0.24% | **0.48%** | $0.48 fees |
| Grid (maker entry, taker stop) | 0.24% | 0.48% | **0.72%** | $0.72 fees |

Grid saves 50% on fees in the happy path, 25% even on stop-loss exits.

### How Both Sides Are Maker

**Buy side (entry):**
```
Current price: $84,000
Grid Level 3:  $80,247 (1.49% × 3 below market)

→ Place limit BUY at $80,247
→ Order sits on order book (below market = maker)
→ Price drops to $80,247 → fills at maker fee (0.24%)
```

**Sell side (take-profit):**
```
Avg entry from filled levels: $81,500
Profit target: 1.5%
Take-profit: $81,500 × 1.015 = $82,722

→ Place limit SELL at $82,722
→ Order sits on order book (above market = maker)
→ Price rises to $82,722 → fills at maker fee (0.24%)

Round-trip fee: 0.24% + 0.24% = 0.48% (both maker)
```

### Three Exit Scenarios

**Scenario A: Happy Path (both maker) — 0.48% round-trip**
```
1. Grid levels fill as price drops (maker buy at 0.24%)
2. Price recovers → take-profit limit sell fills (maker sell at 0.24%)
3. Total fees: 0.48%
4. Example: $100 trade, 1.5% profit target
   Gross profit: $1.50
   Fees: $0.48
   Net profit: $1.02 ✓
```

**Scenario B: Partial Fill + Take Profit (both maker) — 0.48% round-trip**
```
1. Only levels 1-2 fill (price didn't drop to levels 3-5)
2. Cancel unfilled levels 3-5 (no fee for cancellation)
3. Take-profit on filled amount fills as maker sell
4. Total fees: 0.48% on filled amount only
```

**Scenario C: Stop-Loss (maker entry, exchange trigger exit) — 0.72% round-trip**
```
1. All 5 levels fill as price crashes through grid
2. Price continues below stop-loss trigger price
3. Exchange automatically executes market sell (trigger order fires)
4. Private poller detects stop filled → cancels all TP orders
5. Total fees: 0.24% entry + 0.48% taker exit = 0.72%
6. Example: $100 trade, stop-loss at -2%
   Gross loss: -$2.00
   Fees: $0.72
   Total loss: -$2.72
```

**Note:** Stop-loss is a real exchange trigger order — executes in milliseconds, even if our system is down. Uses market sell (taker) because speed matters more than fee savings when the stop fires.

### Take-Profit Order Lifecycle

```
Cycle opens:
  Place 5 limit BUY orders → sit on book as maker

Level 1 fills:
  avg_entry = level_1_price
  Place limit SELL at avg_entry × (1 + profit_target + maker_fee_adjustment)
  → sits on book as maker

Level 2 fills:
  New avg_entry = weighted average of level 1 + 2
  Cancel old sell order (no fee)
  Place new limit SELL at new avg_entry × (1 + target)
  → updated sell order sits on book

Level 3 fills:
  Recalculate avg_entry again
  Cancel + replace sell order

Take-profit fills:
  All done → cycle closed → both sides were maker

OR stop-loss triggers on exchange (trigger order fires automatically):
  Exchange executes market sell (taker fee)
  Poller detects stop fill → cancel all remaining buy orders (no fee)
  Cancel all TP sell orders (no fee)
  Log loss
```

### Fee-Adjusted Take Profit Price

The take-profit price must account for maker fees on both sides:

```
target_sell = avg_entry × (1 + profit_target_pct + exit_maker_fee_pct)

Example:
  avg_entry = $81,500
  profit_target = 1.5%
  maker_fee = 0.24%

  target_sell = $81,500 × (1 + 0.015 + 0.0024) = $81,500 × 1.0174 = $82,918

  Revenue: $82,918
  Entry cost: $81,500 × 1.0024 = $81,696 (including entry maker fee)
  Net profit: $82,918 - $81,696 = $1,222 per BTC
  Profit %: 1.222 / 81.696 = 1.50% ← target achieved after all fees
```

## Exchange-Side Stop-Loss

Crypto.com supports `createStopOrder` and `createTriggerOrder` via ccxt. Stop-loss is placed as a real exchange order — not poller-monitored.

### How It Works

```python
# Place stop-loss trigger order on exchange
# When price drops to triggerPrice, exchange automatically executes market sell
ex.create_order('BTC/USD', 'market', 'sell', amount, params={'triggerPrice': stop_price})
```

### Orders Per Grid Cycle

Each filled grid level results in up to 3 real orders on the exchange:

| Order | Type | Side | Purpose | Fee |
|-------|------|------|---------|-----|
| Grid buy | Limit (below market) | Buy | Entry — fills when price drops | Maker 0.24% |
| Take-profit | Limit (above entry) | Sell | Exit — fills when price recovers | Maker 0.24% |
| Stop-loss | Trigger → Market | Sell | Safety — fires when price crashes | Taker 0.48% |

### Pseudo-OCO (One-Cancels-Other)

Crypto.com doesn't have native OCO orders. Robin manages the cancellation:

```
TP fills → private poller detects fill → cancel matching stop-loss order
Stop triggers → private poller detects fill → cancel matching TP order
```

**Lifecycle:**
```
Level 2 fills at $81,498:
  1. Place limit SELL (TP) at $82,720                → order_id: 51
  2. Place trigger SELL (stop) at $76,586             → order_id: 52
  3. Store both IDs in cycle state

Scenario A: TP fills
  → Poller detects order 51 filled
  → Cancel order 52 (stop) on exchange
  → Log profit

Scenario B: Stop triggers
  → Poller detects order 52 filled (trigger → market sell executed)
  → Cancel order 51 (TP) on exchange
  → Log loss
```

### Batch Grid Stop-Loss

One stop-loss order for the entire position, placed when first level fills. Updated as more levels fill (total quantity increases):

```
Level 1 fills ($10 worth):
  Place stop: sell 0.000121 BTC at trigger $76,586

Level 2 also fills ($10 more):
  Cancel old stop
  Place new stop: sell 0.000244 BTC at trigger $76,586 (updated quantity)

Level 3 also fills ($20 more):
  Cancel old stop
  Place new stop: sell 0.000493 BTC at trigger $76,586 (updated quantity)
```

### Adaptive FIFO Grid Stop-Loss

Two options:

**Option A: One shared stop for all filled levels** (simpler)
Same as Batch — one stop order covering total filled quantity. Updated on each new fill.

**Option B: Per-level stop** (more granular but more orders)
Each filled level gets its own stop. More exchange orders but each level is fully independent.

**Recommended: Option A** — simpler, fewer orders, same protection. The stop price is the same for all levels anyway (below deepest level).

### Advantages Over Poller-Monitored Stop

| Aspect | Poller-Monitored (old) | Exchange-Side (new) |
|--------|----------------------|-------------------|
| Speed | 60s delay (poller cycle) | Milliseconds |
| System dependency | Requires poller running | Works even if our system is down |
| Gap protection | May miss during downtime | Always active on exchange |
| Order management | Simpler (no exchange order) | More complex (must cancel when TP fills) |
| Fee | Taker (same) | Taker (same) |

### Rate Limit Consideration

Per filled grid level: 1 TP order + 1 stop order = 2 orders.
5 levels filled: 5 buys + 5 TPs + 1 shared stop = 11 orders.
Per asset: ~11 orders max per cycle.
4 assets: ~44 orders. Well within Crypto.com rate limits.

## Sentiment Integration

### Why Sentiment + Grid

Grid alone is mechanical — it opens cycles whenever entry conditions pass, regardless of market context. Sentiment adds a **qualitative filter** that adjusts grid aggressiveness based on market psychology.

| Sentiment | Grid Adjustment | Reasoning |
|-----------|----------------|-----------|
| Extreme Fear (0-25) | Contrarian: wider grid, 1.5× capital, 2.5% target | Panic selling = discounted prices, historically marks bottoms |
| Fear (25-45) | Defensive: normal spacing, normal capital | Cautious, standard operation |
| Neutral (45-55) | Normal grid | Business as usual |
| Greed (55-75) | Cautious: tighter grid, 0.5× capital, 1.0% target | Market getting hot, reduce exposure |
| Extreme Greed (75-100) | **Pause grid entirely** | Euphoria = top signal, don't buy into bubble |

### Data Sources

**1. Fear & Greed Index (primary, free)**

```
API: https://api.alternative.me/fci/v2/
Returns: 0-100 score, updated daily
Sources: volatility, volume, social media, surveys, BTC dominance

Fetch: daily at 02:00 UTC alongside TA refresh
Store: in indicators_daily.custom JSONB as "fear_greed_index"
```

**2. Funding Rate (from exchange, free)**

```
Crypto.com perpetual futures funding rate
Positive → longs paying shorts → bullish crowded trade → caution
Negative → shorts paying longs → bearish crowded trade → contrarian opportunity
Extreme (> ±0.03%) → liquidation cascade likely → widen grid or pause

Fetch: every poller cycle (private poller)
Store: in indicators_intraday.custom JSONB as "funding_rate"
```

**3. Robin's LLM News Analysis (unique advantage)**

```
Robin reads top crypto headlines via browser tool
Scores sentiment: bullish / neutral / bearish + confidence
Identifies catalysts: Fed decisions, regulatory news, exchange hacks, ETF flows

Frequency: daily (part of ROB-011 daily review)
Store: research_store with tags ["sentiment", "daily"]
```

No traditional bot can do this — Robin combines numeric indicators with qualitative news analysis.

### Sentiment Score Computation

```
sentiment_score = (
    fear_greed_weight × fear_greed_normalized +     # 0.5 weight
    funding_rate_weight × funding_rate_signal +      # 0.3 weight
    news_sentiment_weight × robin_news_score         # 0.2 weight
)

fear_greed_normalized:
  FGI 0-25  → -1.0 (extreme fear)
  FGI 25-45 → -0.5 (fear)
  FGI 45-55 →  0.0 (neutral)
  FGI 55-75 → +0.5 (greed)
  FGI 75-100→ +1.0 (extreme greed)

funding_rate_signal:
  rate < -0.01% → -0.5 (bearish leverage, contrarian buy)
  rate -0.01% to +0.01% → 0.0 (neutral)
  rate > +0.01% → +0.5 (bullish leverage, caution)
  rate > +0.03% → +1.0 (extreme bullish, high risk of dump)

robin_news_score:
  Robin assigns -1.0 to +1.0 based on news analysis
  Stored with reasoning in research report

Final sentiment_score range: -1.0 (extreme fear) to +1.0 (extreme greed)
```

### Grid Parameter Adjustments

```json
{
  "sentiment": {
    "enabled": true,
    "sources": ["fear_greed_index", "funding_rate", "news_analysis"],
    "weights": {"fear_greed": 0.5, "funding_rate": 0.3, "news": 0.2},
    "adjustments": {
      "extreme_fear": {
        "threshold": -0.7,
        "capital_multiplier": 1.5,
        "atr_multiplier_override": 0.7,
        "profit_target_pct": 2.5,
        "note": "Contrarian: bigger position, wider grid, bigger target"
      },
      "fear": {
        "threshold": -0.3,
        "capital_multiplier": 1.0,
        "note": "Normal operation with defensive awareness"
      },
      "neutral": {
        "threshold": 0.3,
        "capital_multiplier": 1.0,
        "note": "Standard grid parameters"
      },
      "greed": {
        "threshold": 0.7,
        "capital_multiplier": 0.5,
        "profit_target_pct": 1.0,
        "note": "Reduce exposure, quick exits"
      },
      "extreme_greed": {
        "threshold": 1.0,
        "capital_multiplier": 0,
        "note": "Grid paused — don't buy into euphoria"
      }
    }
  }
}
```

### Robin's Daily Sentiment Workflow

```
02:00 UTC (ROB-012 enhanced):
  1. Fetch daily OHLCV + compute TA (existing)
  2. Fetch Fear & Greed Index from API
  3. Read funding rates from exchange

10:00 UTC (ROB-011 enhanced):
  1. Robin reads top 3-5 crypto headlines via browser
  2. Scores news sentiment using LLM reasoning
  3. Computes combined sentiment score
  4. Adjusts grid params if sentiment changed significantly
  5. Posts to Discord:
     "Sentiment: Fear (FGI=32, funding=-0.008%, news=bearish)
      Grid adjustment: normal capital, defensive spacing.
      Reason: Market cautious after Fed minutes, but no panic."

Grid cycle evaluation:
  Before opening any new cycle, check sentiment:
  - If extreme_greed → skip cycle
  - If extreme_fear → open with contrarian params (bigger, wider)
  - Otherwise → normal params with sentiment-adjusted capital
```

### Example: Sentiment Changes Grid Behavior

**Day 1: Neutral market (FGI=52, funding=0%, news=neutral)**
```
sentiment_score = 0.0
Grid: normal params, 10% capital, 1.5% target
→ Open standard grid on BTC
```

**Day 3: Fear hits (FGI=28, funding=-0.015%, Robin reads "ETF outflows $500M")**
```
sentiment_score = -0.5 × 0.5 + (-0.5) × 0.3 + (-0.5) × 0.2 = -0.50
Grid: fear mode, normal capital, defensive spacing
→ Grid widens slightly, keeps trading
```

**Day 5: Extreme fear (FGI=15, funding=-0.035%, Robin reads "Major exchange hack, $200M stolen")**
```
sentiment_score = -1.0 × 0.5 + (-0.5) × 0.3 + (-1.0) × 0.2 = -0.85
Grid: extreme fear mode, 1.5× capital, wide grid, 2.5% target
→ Contrarian: bigger bets at deeply discounted prices
→ Robin reports: "Extreme fear — contrarian opportunity. Opening large defensive grid."
```

**Day 8: Greed building (FGI=68, funding=+0.02%, Robin reads "BTC breaks $90K, FOMO building")**
```
sentiment_score = +0.5 × 0.5 + +0.5 × 0.3 + +0.5 × 0.2 = +0.50
Grid: greed mode, 0.5× capital, tight grid, 1.0% target
→ Small positions, quick exits, reducing exposure
→ Robin reports: "Greed building — reducing grid size, taking quick profits."
```

## Order Management

### Exchange Order Tracking

Grid orders are real limit orders on the exchange. Need to track:

| Our DB (orders table) | Exchange | Link |
|----------------------|----------|------|
| order with grid level metadata | Limit buy at $82,749 | exchange_order_id |
| order with take-profit metadata | Limit sell at $82,720 | exchange_order_id |

Private poller detects fills and updates our DB (existing flow from ES-0012).

### Cancel Management

When a grid cycle closes or regime changes:
```
1. Fetch all open orders for this cycle
2. Cancel each on exchange via ccxt
3. Update our DB (status = cancelled)
4. Log reason (take-profit hit, stop-loss, regime change)
```

## Strategy Parameters

### Grid Strategy Params

```json
{
  "type": "dca_grid",
  "mode": {
    "default": "adaptive_fifo",
    "auto_select_by_regime": true,
    "batch_regime_max": 30,
    "fifo_regime_min": 30,
    "regime_pause_threshold": 65,
    "regime_resume_threshold": 55,
    "hysteresis_note": "Grid pauses at RS 65, resumes at RS 55. Buffer prevents whipsaw."
  },
  "entry": {
    "max_regime_score": 60,
    "rsi_entry_max": 60,
    "max_atr_pct": 6.0,
    "require_sma200_above": false,
    "require_golden_cross": false,
    "defensive_mode_enabled": true,
    "defensive_rsi_oversold": 30
  },
  "grid": {
    "num_levels": 5,
    "weights": [1, 1, 2, 3, 3],
    "volatility_regimes": {
      "low": {"atr_mult": 0.4, "profit_target": 1.0},
      "normal": {"atr_mult": 0.5, "profit_target": 1.5},
      "high": {"atr_mult": 0.7, "profit_target": 2.5}
    }
  },
  "exit": {
    "stop_loss_spacing_mult": 1.0,
    "stop_loss_type": "exchange_trigger",
    "max_cycle_duration_hours": 72,
    "max_expired_pending_per_asset": 2,
    "cooldown_minutes": 30
  },
  "sentiment": {
    "enabled": true,
    "sources": ["fear_greed_index", "funding_rate", "news_analysis"],
    "weights": {"fear_greed": 0.5, "funding_rate": 0.3, "news": 0.2},
    "adjustments": {
      "extreme_fear":  {"threshold": -0.7, "capital_multiplier": 1.5, "profit_target_pct": 2.5},
      "fear":          {"threshold": -0.3, "capital_multiplier": 1.0},
      "neutral":       {"threshold":  0.3, "capital_multiplier": 1.0},
      "greed":         {"threshold":  0.7, "capital_multiplier": 0.5, "profit_target_pct": 1.0},
      "extreme_greed": {"threshold":  1.0, "capital_multiplier": 0.0}
    },
    "mid_cycle_adjustment": true,
    "mid_cycle_note": "Only applies to adaptive_fifo mode. Ignored in batch mode."
  },
  "position": {
    "capital_per_cycle_pct": 10
  }
}
```

### Per-Asset Tuning

All pairs quoted in USD on Crypto.com (BTC/USD, ETH/USD, SOL/USD, XRP/USD).

| Asset | Grid Spacing Note | Profit Target | Capital |
|-------|------------------|--------------|---------|
| BTC | Lowest volatility, tightest grid | 1.0-1.5% | 10% |
| ETH | Medium volatility | 1.5-2.0% | 10% |
| SOL | High volatility, wider grid | 2.0-2.5% | 8% |
| XRP | High volatility, news-driven | 2.0-3.0% | 8% |

## Implementation Phases

### Phase 1: Batch Grid Engine + BTC Grid
- [ ] Create `strategies/dca_grid.py` — grid level calculation, Batch mode cycle state
- [ ] Create grid cycle manager — handles open/fill/close/cancel lifecycle
- [ ] Update `cli/trade.py` — support placing multiple limit orders (grid levels)
- [ ] Update `cli/trade.py` — support cancel-all-for-cycle
- [ ] Create `btc_dca_grid` strategy with Batch mode defaults
- [ ] Paper test: place grid orders, verify fills detected, batch take-profit works

### Phase 2: Adaptive FIFO Mode + Regime Integration
- [ ] Add FIFO mode to `dca_grid.py` — per-level TP tracking, independent sell orders
- [ ] Auto mode selection: RS 0-30 → Batch, RS 30-60 → FIFO
- [ ] Build regime transition logic — cancel unfilled, keep TPs, activate trend follow
- [ ] Add hysteresis buffer for regime threshold (configurable, default ±5)
- [ ] Handle reverse transition: trend exits via trailing stop, grid resumes
- [ ] Paper test both modes + regime transitions

### Phase 3: Sentiment Integration
- [ ] Add Fear & Greed Index fetch to daily data pipeline (ROB-012)
- [ ] Add funding rate fetch to private poller
- [ ] Build sentiment score computation (FGI + funding + news)
- [ ] Implement grid param adjustments based on sentiment score
- [ ] Robin LLM news sentiment analysis in daily review (ROB-011)
- [ ] Create sentiment skill for Robin
- [ ] Paper test: verify sentiment adjusts grid behavior correctly

### Phase 4: Multi-Asset + Defensive Mode
- [ ] Create grid strategies for ETH, SOL, XRP
- [ ] Implement defensive grid mode (oversold bounce in downtrend)
- [ ] Per-asset param tuning based on volatility characteristics
- [ ] Add volatility regime detection (low/normal/high/extreme)

### Phase 5: Optimization
- [ ] Backtest grid strategy on historical data (simulate fill prices from OHLCV)
- [ ] Optimize grid weights and spacing per asset
- [ ] Compare maker-only grid P&L vs taker-only momentum P&L
- [ ] Analyze sentiment impact on grid performance
- [ ] Add time-of-day analysis (some hours have more mean reversion)

### Phase 6: Live Deployment
- [ ] Review paper results with Boss
- [ ] Switch approved strategies to live
- [ ] Monitor first week closely
- [ ] Adjust grid params based on real fill rates and sentiment accuracy

## Risk Considerations

**Unfilled orders:** Grid levels may not fill if price doesn't drop enough. That's OK — no trade = no loss. But capital sits idle.

**Gap risk:** If price drops through all 5 levels quickly (flash crash), all levels fill at once and the stop-loss may gap below target. Worst case: 5 levels filled + stop-loss at spacing below deepest level.

**Regime transition:** If market transitions from sideways (grid active) to trending (grid should pause) mid-cycle, open grid orders need orderly cancellation.

**Stale orders:** Grid orders sitting on the exchange can fill at any time. If our system loses track (poller down), fills may not be detected immediately.

**Sentiment false signals:** Fear & Greed Index is a lagging indicator of crowd psychology. Extreme fear can get more extreme. Contrarian sizing (1.5×) amplifies losses if the fear is justified. The stop-loss is the safety net.

**LLM news misinterpretation:** Robin may misread news sentiment. A "positive" headline could be sarcastic, outdated, or misleading. Weight news sentiment at only 20% of the composite score to limit impact.

**Sentiment data outage:** If Fear & Greed API is down, fall back to regime score only (no sentiment adjustment). Never block grid operation due to missing sentiment data.

**Exchange rate limits:** Placing 5 orders + 1 take-profit + 1 stop-loss = 7 orders per cycle per asset. With 4 assets: 28 orders. Crypto.com rate limits may need respect.

**Regime whipsaw:** If RS oscillates around 60 (e.g., 58→62→57→63), grid cycles get repeatedly opened and cancelled, burning fees on order churn. Mitigation: add hysteresis buffer — grid pauses at RS 65, resumes at RS 55 (not exactly 60). This is a parameter to tune during paper testing.

## Open Questions (to decide before implementation)

**Q1: ~~Hysteresis buffer for regime transitions?~~ → DECIDED: Yes, use ±5 buffer**
Grid pauses at RS 65, resumes at RS 55. Prevents whipsaw churn. Configurable via strategy params.

**Q2: ~~Exchange-side stop-loss?~~ → DECIDED: Yes, use Crypto.com trigger orders**
Crypto.com supports `createStopOrder` and `createTriggerOrder`. Stop-loss placed as exchange order — executes in milliseconds, works even if our system is down. See "Exchange-Side Stop-Loss" section.

**Q3: ~~Max cycle duration (72h) — what happens on timeout?~~ → DECIDED: Option B with cap**
Cancel unfilled levels, keep filled TPs running on exchange. Max 2 expired_pending cycles per asset — if 3rd would be created, force-close the oldest first.

## Dependencies

- ES-0012 (trading toolkit) — complete ✅
- Private poller (fill detection) — active ✅
- Regime score (daily indicators) — active ✅
- Fee sync from exchange — active ✅

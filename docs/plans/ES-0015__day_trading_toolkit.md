# ES-0015 — Day Trading on Hyperliquid

## Status: DRAFT

## Problem

Current strategies (ES-0012) trade crypto on Crypto.com using daily indicators. Signals are 12-24h stale, resulting in ~1 trade every 2 weeks. In bear markets, Robin sits idle for weeks.

Meanwhile, Hyperliquid offers tokenized stocks (xStocks) and crypto with 0.04-0.07% fees (7-12x cheaper than Crypto.com), enabling profitable day trading that isn't viable elsewhere.

## Goal

Enable Robin to day-trade on Hyperliquid — **1-5 trades per day** across xStocks (AAPL, TSLA, NVDA, SPY) and crypto (BTC, ETH), using intraday indicators from 1m candle data.

## Why Hyperliquid

| Feature | Detail |
|---------|--------|
| **Fees** | 0.04% maker / 0.07% taker spot. 0.015% / 0.045% perps. Round-trip **0.11%** (vs 0.75% Crypto.com) |
| **xStocks** | AAPL, AMZN, GOOGL, META, MSFT, NVDA, TSLA, SPY, QQQ — tokenized stocks |
| **Crypto** | BTC, ETH, SOL + 600+ other pairs |
| **Trading hours** | 24/7 — stocks trade round the clock |
| **Access** | Wallet-based (EVM/Arbitrum), no KYC for most operations |
| **ccxt support** | Full support — `ccxt.hyperliquid()` |

### Fee Math — Why Day Trading Works Here

```
Target: +0.5% per trade, 5 trades/day

Hyperliquid:  5 × 0.5% - 5 × 0.11% = +1.95%/day net
Crypto.com:   5 × 0.5% - 5 × 0.75% = -1.25%/day net  ← loses money

Same strategy, different venue, opposite result.
```

### Available Pairs

**xStocks (spot, /USDC):**

| Pair | Asset | Why Trade It |
|------|-------|-------------|
| AAPL/USDC | Apple | High liquidity, steady trends |
| NVDA/USDC | NVIDIA | AI hype = high volatility |
| TSLA/USDC | Tesla | Most volatile mega-cap |
| SPY/USDC | S&P 500 ETF | Market benchmark, mean-reverts well |
| QQQ/USDC | Nasdaq 100 ETF | Tech-heavy, follows NVDA/AAPL |
| GOOGL/USDC | Google | Steady, good for VWAP reversion |
| META/USDC | Meta | Volatile on news |
| MSFT/USDC | Microsoft | Stable, low-vol day trades |
| AMZN/USDC | Amazon | Mid-volatility |

**Perpetuals (even lower fees):** CASH-NVDA, CASH-TSLA, XYZ-AAPL, etc. — 0.06% round-trip.

**Crypto:** BTC/USDC, ETH/USDC — same assets as Crypto.com but with cheaper fees for day trading.

## Intraday Indicators

Computed by TA poller from 1m candles (same infrastructure as ES-0012). Stored in `indicators_intraday.custom` JSONB — no migration needed.

| Indicator | Formula | Used By |
|-----------|---------|---------|
| `vwap_deviation_pct` | `(close - VWAP) / VWAP × 100` | VWAP Reversion |
| `volume_spike_5m` | `5m_volume / avg_1h_volume` | Volume Breakout |
| `rsi_prev_2h` | RSI(14) value 2 hours ago | RSI Bounce (fresh drop check) |
| `ema_cross_direction` | 1=bullish cross, -1=bearish, 0=none | EMA Crossover |
| `consecutive_candles` | Count of same-direction 1m candles | Volume Breakout, EMA Cross |
| `spread_z_score` | `(spread - avg) / stddev` over 60 bars | All (liquidity guard) |

## Day Trading Strategies

### Strategy 1: VWAP Reversion — "The Snapper"

Buy when price stretches below VWAP, sell the snap-back to mean.

```
Entry:
  - Price < VWAP - (1.5 × intraday ATR)         — stretched below mean
  - Intraday RSI(14) < 30                        — oversold confirmation
  - Spread < 0.15%                               — good liquidity (Hyperliquid has tight spreads)
  - Volume not spiking (< 3x avg)                — drifting, not panic selling
  - No trade in last 30 min                       — cooldown

Exit:
  - Price reaches VWAP                            — mean reached (primary target)
  - OR profit > +0.5%                             — take profit
  - OR loss > -0.3%                               — hard stop
  - OR held > 4 hours                             — time stop

Position: 5% of capital
Expected: 2-5 trades/day in ranging markets
Fee impact: 0.11% round-trip on 0.5% target = 0.39% net profit per trade
```

### Strategy 2: Intraday RSI Bounce — "The Dip Buyer"

Buy extreme RSI oversold on 1h timeframe, sell when recovered.

```
Entry:
  - Intraday RSI(14) < 25                        — extreme oversold
  - RSI was > 35 within last 2 hours              — fresh drop, not stuck
  - Spread < 0.15%

Exit:
  - Intraday RSI > 50                             — momentum recovered
  - OR profit > +0.8%                             — take profit
  - OR loss > -0.5%                               — hard stop
  - OR held > 6 hours                             — time stop

Position: 5% of capital
Expected: 1-3 trades/day during volatile sessions
```

### Strategy 3: EMA Crossover Scalp — "The Surfer"

Trade EMA(9)/EMA(21) crossovers on intraday data.

```
Entry:
  - EMA(9) crosses above EMA(21)                  — bullish crossover
  - Volume ratio > 1.5                             — volume confirms
  - Intraday RSI between 40-65                     — not extreme
  - Spread < 0.15%

Exit:
  - EMA(9) crosses below EMA(21)                   — reverse signal
  - OR profit > +0.8%                              — take profit
  - OR loss > -0.5%                                — hard stop
  - OR held > 8 hours                              — time stop

Position: 3% of capital
Expected: 1-4 trades/day
```

### Strategy 4: Volume Breakout — "The Raider"

Sudden volume spike signals institutional activity. Trade the direction.

```
Entry:
  - 5m volume > 3x average 1h volume               — spike detected
  - Price moving in same direction as volume         — aligned
  - Last 3 candles all same direction               — momentum confirmed
  - Spread < 0.2%

Exit:
  - First candle closes against entry direction     — exhaustion
  - OR profit > +1.0%                               — take profit
  - OR loss > -0.5%                                 — hard stop
  - OR held > 2 hours                               — time stop

Position: 3% of capital
Expected: 0-2 trades/day (rare, high conviction)
```

## xStock-Specific Considerations

Stocks differ from crypto:

| Factor | Crypto | xStocks |
|--------|--------|---------|
| Daily volatility | ~3-5% | ~1-2% |
| Trading volume pattern | Flat 24/7 | Peaks during US hours (14:30-21:00 UTC) |
| Event risk | Protocol upgrades, regulatory | Earnings, Fed, macro data |
| Correlation | BTC dominates | SPY/QQQ dominate, sector-specific |

Strategy adjustments for xStocks:
- **Tighter targets**: 0.3-0.5% (vs 0.5-1.0% for crypto)
- **More trades**: Lower volatility → more mean reversion opportunities
- **Time-of-day filter**: Prioritize US market hours for best liquidity
- **Earnings blackout**: Don't trade individual stocks 1 day before/after earnings

## Scan Frequency

```
Every 5 min (ROB-020 new recurring task):
  Evaluate day trading strategies on indicators_intraday
  Covers both Hyperliquid xStocks and Hyperliquid crypto

Every hour (ROB-010 existing, unchanged):
  Evaluate swing strategies on indicators_daily
  Covers Crypto.com crypto pairs
```

Both run in parallel. Day trades and swing trades tracked separately.

## Day Trading Guardrails

| Guardrail | Value | Notes |
|-----------|-------|-------|
| Position size | 3-5% | Smaller than swing (10-15%) |
| Stop loss | 0.3-0.5% | Tighter than swing (3-8%) |
| Max open day trades | 2 | Plus 3 swing trades allowed separately |
| Max daily trades | 10 | Prevent fee-burning churn |
| Min hold time | 5 min | Prevent rapid-fire |
| Intraday loss limit | 2% | Separate from daily 5% swing limit |
| Min profit after fees | must > 0.11% | Explicit fee check per trade |

All configurable via DB (`guardrail:day_*` prefix).

## Backtesting

**Challenge:** No 1m history for Hyperliquid xStocks yet.

**Approach:**
1. Phase 1: Paper test live (no backtest, strategies are simple enough)
2. Phase 2: After 2 weeks of 1m data, build intraday backtester
3. Alternative: Fetch historical 1m via ccxt (last 1000 candles ≈ 16 hours) for quick validation

## Setup

### Hyperliquid Wallet
1. Create EVM wallet (MetaMask or similar)
2. Bridge USDC to Arbitrum
3. Deposit USDC to Hyperliquid

### System Configuration
```bash
# Add venue
cli.market add-venue --code hyperliquid --name Hyperliquid --type exchange --ccxt-id hyperliquid

# Add xStock assets
cli.market add-asset --symbol AAPL --name Apple
cli.market add-asset --symbol NVDA --name NVIDIA
cli.market add-asset --symbol TSLA --name Tesla
cli.market add-asset --symbol SPY --name "S&P 500 ETF"

# Add trading pairs
cli.market add-trading-pair --venue hyperliquid --base AAPL --quote USDC --pair-symbol "AAPL/USDC" --maker-fee 0.0004 --taker-fee 0.0007
cli.market add-trading-pair --venue hyperliquid --base SPY --quote USDC --pair-symbol "SPY/USDC" --maker-fee 0.0004 --taker-fee 0.0007
# ... repeat for each pair

# Add account
cli.market add-account --venue hyperliquid --name main --type spot --address <wallet-address> --default

# Add credentials to agents/robin/.env
HYPERLIQUID_WALLET_ADDRESS=0x...
HYPERLIQUID_PRIVATE_KEY=...
```

### Exchange Wrapper Update
`core/exchange.py` needs Hyperliquid credential handling:
```python
# In CcxtExchange.__init__:
if eid == "hyperliquid":
    config["walletAddress"] = settings.hyperliquid_wallet_address
    config["privateKey"] = settings.hyperliquid_private_key
```

## Implementation Phases

### Phase 1: Infrastructure + VWAP Reversion (MVP)
- [ ] Add Hyperliquid credential support to `core/exchange.py` + `core/config.py`
- [ ] Update public poller to support multiple exchanges (fetch from both Crypto.com + Hyperliquid)
- [ ] Enhance TA poller: vwap_deviation, volume_spike_5m, rsi_prev_2h, spread_z_score
- [ ] Create `strategies/vwap_reversion.py` — evaluates on indicators_intraday
- [ ] Update signal scanner: support 5-min scan for intraday strategies
- [ ] Add ROB-020 recurring task (5-min scan)
- [ ] Add day trading guardrails to DB
- [ ] Seed Hyperliquid venue + xStock pairs + account
- [ ] Deploy to paper mode

### Phase 2: RSI Bounce + EMA Crossover + xStock Params
- [ ] Create `strategies/intraday_rsi_bounce.py`
- [ ] Create `strategies/ema_crossover_scalp.py`
- [ ] Add 1h RSI aggregation to TA poller
- [ ] Tune params per asset (stocks vs crypto volatility)
- [ ] Add time-of-day filter for US market hours
- [ ] Paper test all strategies

### Phase 3: Volume Breakout + Backtesting
- [ ] Create `strategies/volume_breakout_intraday.py`
- [ ] Build 1m data backtester (different from daily backtester)
- [ ] Backtest on accumulated 1m data (need 2+ weeks)
- [ ] Param sweep per asset
- [ ] Create day trading skill for Robin

### Phase 4: Optimization
- [ ] Compare day trading P&L vs swing trading P&L
- [ ] Optimize scan frequency (5min vs 10min vs 15min)
- [ ] Add earnings calendar blackout for individual stocks
- [ ] Time-of-day performance analysis
- [ ] Tune position sizing per strategy per asset

### Phase 5: Advanced (future)
- [ ] Perpetual futures strategies (funding rate arbitrage)
- [ ] Order book poller + imbalance indicator
- [ ] Cross-venue arbitrage (Hyperliquid vs Crypto.com price differences)
- [ ] On-chain whale detection

## Risk Considerations

**Fee advantage is the edge:** At 0.11% round-trip, strategies that would lose money on Crypto.com are profitable on Hyperliquid. But the edge is thin — slippage, spread widening, or poor timing can erase it.

**Overtrading:** More trades ≠ more profit. Max 10 trades/day guardrail prevents fee-burning churn.

**xStock liquidity:** xStocks are newer than crypto pairs. Liquidity may be thin during off-US-hours. Spread guard is critical.

**DEX risk:** Hyperliquid is a DEX — smart contract risk, bridge risk (USDC on Arbitrum). Not the same custody guarantees as a centralized exchange.

**Poller dependency:** If the poller goes down, intraday indicators go stale. Day trading strategies must detect stale data (> 5min) and halt.

## Dependencies

- ES-0012 (trading toolkit) — complete ✅
- Hyperliquid wallet + USDC funding — required before Phase 1
- Public poller enhanced for multi-exchange — Phase 1
- 1m data accumulation for Hyperliquid pairs — starts in Phase 1

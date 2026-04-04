# ES-0015 — Day Trading Toolkit

## Status: DRAFT

## Problem / Pain Points

Current trading strategies rely entirely on **lagging daily indicators** (RSI, EMA, MACD, BB) computed from CoinGecko's market-wide daily OHLCV. While these work for swing trading (days-weeks), they are too slow for day trading:

- Daily signals are 12-24 hours stale by the time Robin acts
- Miss intraday opportunities (flash crashes, momentum spikes)
- Can't detect real-time market microstructure (volume spikes, order flow)
- No leading indicators — only react to what already happened
- BTC correlation filter blocks during extended bear markets, Robin sits idle

## Suggested Solution

Enhance inotagent-trading with **intraday indicators, leading signals, and day trading strategies** that operate on 1m/5m/1h data from the exchange.

Three layers:
1. **Intraday indicators** — computed from our existing 1m poller data
2. **New data sources** — order book, funding rate, open interest (future)
3. **Day trading strategies** — fast entry/exit, tighter stops, smaller positions

## Layer 1: Intraday Indicators (from existing 1m data)

No new data sources needed — computed by TA poller from `ohlcv_1m`.

### Volume Spike Detector
Detects sudden volume increases that often precede big moves.

```
volume_spike = current_volume / avg_volume_20
If spike > 3.0 AND price direction aligns → momentum signal
If spike > 3.0 AND price reverses → exhaustion signal
```

### VWAP Bands
Price relative to intraday VWAP ± ATR. Mean reversion signal for intraday.

```
vwap_upper = VWAP + (1.5 × intraday_ATR)
vwap_lower = VWAP - (1.5 × intraday_ATR)

Price below vwap_lower → oversold intraday (buy signal)
Price above vwap_upper → overbought intraday (sell signal)
Price crossing VWAP from below → bullish
```

### Momentum Rate of Change (ROC)
Not just RSI level, but how fast it's changing. Detects trend acceleration.

```
rsi_roc = (RSI_now - RSI_5_bars_ago) / 5
If rsi_roc > 2.0 → momentum accelerating (trend strengthening)
If rsi_roc < -2.0 → momentum decelerating (reversal likely)
```

### Candle Pattern Detection
From 1m candles, detect actionable patterns:

- **Engulfing** — current candle fully engulfs previous (reversal)
- **Doji** — open ≈ close with long wicks (indecision → breakout coming)
- **Hammer/Inverted hammer** — long lower/upper wick (reversal after trend)
- **Three soldiers/crows** — 3 consecutive bullish/bearish candles (trend confirmation)

### Multi-Timeframe Confluence
Signal is stronger when multiple timeframes agree.

```
Score each timeframe (1m, 5m, 1h, daily):
  - RSI direction (bullish/bearish)
  - EMA alignment (fast > slow = bullish)
  - VWAP position (above = bullish)

Confluence score = count of timeframes agreeing / total
If confluence >= 0.75 → high conviction signal
```

### Spread & Liquidity Monitor
From bid/ask in `ohlcv_1m`:

```
spread_z_score = (current_spread - avg_spread_60) / stddev_spread_60
If z_score > 2.0 → liquidity drying up (danger, don't trade)
If z_score < -1.0 → tight spread, good execution conditions
```

## Layer 2: New Data Sources (future phases)

### Order Book Depth (requires new poller)
```
poller/public/orderbook.py
- Fetch top 10-20 bid/ask levels every 10s
- Compute: bid_volume, ask_volume, imbalance ratio
- Store in new table: orderbook_snapshots

Indicator: order_book_imbalance = bid_volume / (bid_volume + ask_volume)
> 0.6 = buying pressure building
< 0.4 = selling pressure building
```

### Funding Rate (requires futures API)
```
Crypto.com perpetual futures funding rate
- Positive rate = longs paying shorts (bullish sentiment)
- Negative rate = shorts paying longs (bearish sentiment)
- Extreme positive (> 0.01%) = overleveraged longs (dump likely)
- Extreme negative (< -0.01%) = overleveraged shorts (squeeze likely)
```

### Open Interest (requires futures API)
```
Rising OI + rising price = new money entering (trend continuation)
Rising OI + falling price = new shorts entering (bearish)
Falling OI + rising price = short covering (weak rally)
Falling OI + falling price = long capitulation (bottom forming)
```

### On-Chain Whale Detection (requires block explorer API)
```
Large transfers (> $1M) to exchange = potential sell pressure
Large transfers from exchange = accumulation
Exchange balance decreasing = bullish (supply squeeze)
```

## Layer 3: Day Trading Strategies

### VWAP Reversion — "The Snapper"
Trade price snapping back to VWAP after deviation.

```
Entry: price < VWAP - (1.5 × ATR) AND volume_spike < 3 (not panic selling)
Exit: price reaches VWAP OR +1% profit OR -0.5% stop
Hold time: minutes to hours
Size: 5% (small, frequent trades)
Active: all day when regime 20-60
```

### Momentum Scalper — "The Surfer"
Ride strong momentum candles for quick profit.

```
Entry: 3 consecutive bullish 1m candles AND volume_spike > 2 AND rsi_roc > 2
Exit: first bearish candle close OR +1.5% profit OR -0.8% stop
Hold time: minutes
Size: 5%
Active: when confluence score >= 0.75
```

### Breakout Catcher — "The Raider"
Enter on high/low breakout with volume confirmation.

```
Entry: price > 1h high AND volume_spike > 2.5 AND spread_z_score < 1 (good liquidity)
Exit: trail via 5m EMA OR +2% profit OR -1% stop
Hold time: minutes to 1 hour
Size: 5%
Active: after squeeze detection (from existing volatility_breakout)
```

### Liquidation Momentum — "The Sweeper" (requires futures data)
Trade the momentum created by liquidation cascades.

```
Entry: large liquidation event detected AND price still moving in liquidation direction
Exit: momentum exhaustion (rsi_roc reversal) OR +3% OR -1.5%
Hold time: minutes
Size: 8%
Active: only during high volatility events
```

## Database Changes

### New tables
```sql
-- Intraday indicator snapshots at higher frequency (5m aggregation)
CREATE TABLE trading_platform.indicators_5m (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    timestamp TIMESTAMPTZ NOT NULL,
    rsi_14 NUMERIC(8,4),
    rsi_roc NUMERIC(8,4),           -- rate of change
    ema_9 NUMERIC(20,8),
    ema_21 NUMERIC(20,8),
    vwap NUMERIC(20,8),
    vwap_upper NUMERIC(20,8),
    vwap_lower NUMERIC(20,8),
    volume_spike NUMERIC(10,4),
    spread_z_score NUMERIC(8,4),
    confluence_score NUMERIC(4,2),   -- 0-1
    candle_pattern VARCHAR(32),      -- 'engulfing_bull', 'doji', 'hammer', etc.
    custom JSONB DEFAULT '{}',
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, venue_id, timestamp)
);

-- Order book snapshots (Layer 2)
CREATE TABLE trading_platform.orderbook_snapshots (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    timestamp TIMESTAMPTZ NOT NULL,
    bid_volume NUMERIC(24,2),
    ask_volume NUMERIC(24,2),
    imbalance NUMERIC(6,4),         -- bid / (bid + ask)
    best_bid NUMERIC(20,8),
    best_ask NUMERIC(20,8),
    depth_levels INT,
    UNIQUE (asset_id, venue_id, timestamp)
);
```

### Existing table changes
- `indicators_intraday`: add `rsi_roc`, `vwap_upper`, `vwap_lower`, `volume_spike`, `spread_z_score`, `candle_pattern` to `custom` JSONB (no migration needed)

## Poller Changes

### TA Poller Enhancement
Add to existing `poller/ta`:
- Compute 5m aggregated indicators from 1m data
- Volume spike detection
- VWAP bands
- RSI rate of change
- Candle pattern detection
- Multi-timeframe confluence score

### New: Order Book Poller (Layer 2)
```
poller/public/orderbook.py
- Fetch order book every 10-30 seconds
- Compute imbalance ratio
- Store snapshots (retain 24h)
```

## Implementation Phases

### Phase 1: Intraday Indicators (Layer 1)
- [ ] Add volume spike, VWAP bands, RSI ROC to TA poller
- [ ] Add candle pattern detection
- [ ] Add multi-timeframe confluence scoring
- [ ] Store in indicators_intraday custom JSONB
- [ ] Add 5m aggregation view or table

### Phase 2: Day Trading Strategies
- [ ] Implement VWAP Reversion strategy
- [ ] Implement Momentum Scalper strategy
- [ ] Implement Breakout Catcher strategy
- [ ] Backtest on historical 1m data (need to accumulate first)
- [ ] Create day trading skills for Robin

### Phase 3: Signal Scanner Enhancement
- [ ] Signal scanner checks intraday indicators (not just daily)
- [ ] Sub-hourly scan option for day trading strategies
- [ ] Quick decision mode: evaluate + execute in same cycle

### Phase 4: Order Book & Futures Data (Layer 2)
- [ ] Order book poller (10-30s interval)
- [ ] Order book imbalance indicator
- [ ] Funding rate fetch (if exchange supports)
- [ ] Open interest tracking
- [ ] Migration for new tables

### Phase 5: Advanced Strategies (Layer 2)
- [ ] Liquidation Momentum strategy
- [ ] Order flow strategy
- [ ] On-chain whale detection (external API)

## Guardrail Considerations

Day trading needs different guardrails than swing trading:
- **Smaller position size** (5% vs 10-15%) — more trades, less per trade
- **Tighter stops** (0.5-1.5% vs 3-8%) — quick exit on wrong direction
- **Higher trade frequency** — may need MAX_DAILY_TRADES limit
- **Intraday loss limit** — separate from daily loss (stop after X% intraday loss)
- **Minimum hold time** — prevent rapid-fire trades that rack up fees

## Dependencies

- ES-0012 (trading toolkit) — must be complete
- Sufficient 1m data history (1-2 weeks of poller data for backtesting)
- Public poller running continuously for real-time indicators

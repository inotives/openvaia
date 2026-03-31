# ES-0012 — Robin Trading Toolkit

## Status: DRAFT

## Objective

Create a standalone Python trading toolkit repo (`inotives/robin-trading`) that Robin operates via shell commands. The toolkit provides CLI tools to fetch market data, analyze signals, manage orders, and track performance — all backed by a `trading_platform` schema in the shared Postgres DB.

## Design Principles

- **Agent-first:** Every tool outputs JSON — designed for LLM consumption, not human TUI
- **Robin operates, doesn't build:** The repo ships with working tools. Robin uses them, tunes strategy params, and submits PRs for improvements
- **Same DB, different schema:** Uses the shared Postgres (`inotives` DB) under `trading_platform` schema
- **Strategy as config:** Trading rules live in the DB as JSON params — Robin adjusts via CLI, no code changes for tuning
- **Guardrails in code:** Safety limits are hardcoded in `guardrails.py` — Robin cannot bypass via prompt

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| Package manager | uv |
| Exchange API | ccxt |
| Data analysis | pandas, pandas-ta |
| HTTP client | requests |
| Database | asyncpg (async) + psycopg (sync CLI) |
| Config | pydantic-settings (.env) |
| Migrations | dbmate |

## Architecture

```
GitHub: inotives/robin-trading
├── pyproject.toml                 # uv project config
├── .python-version                # 3.12
├── .env.template                  # credential template
├── Makefile                       # shortcuts
├── guardrails.py                  # HUMAN-AUTHORED safety limits (PR-protected)
├── .github/CODEOWNERS             # protect guardrails, migrations, config
│
├── cli/                           # Robin's CLI tools (all output JSON)
│   ├── market.py                  # Market data commands
│   ├── signals.py                 # Signal detection commands
│   ├── trade.py                   # Order management commands
│   ├── portfolio.py               # Balance + P&L commands
│   └── strategy.py                # Strategy config commands
│
├── core/                          # Shared library
│   ├── config.py                  # pydantic-settings (reads .env)
│   ├── db.py                      # Postgres connection (trading_platform schema)
│   ├── exchange.py                # ccxt wrapper (paper + live mode)
│   ├── indicators.py              # Technical indicator computation
│   └── models.py                  # Data models (TypedDict / dataclass)
│
├── strategies/                    # Strategy implementations
│   ├── base.py                    # Abstract strategy interface
│   ├── dca_grid.py                # DCA grid strategy
│   └── momentum.py                # Momentum / trend following
│
├── db/
│   └── migrations/                # dbmate migrations for trading_platform schema
│       ├── 001_init_trading.sql
│       ├── 002_add_orders.sql
│       └── 003_add_executions.sql
│
├── tests/
│   ├── test_guardrails.py         # Safety limit tests (must pass before any merge)
│   ├── test_indicators.py
│   └── test_signals.py
│
└── README.md
```

## Database Schema (`trading_platform`)

All tables live in the `trading_platform` schema within the shared `inotives` Postgres DB.

### Migration 001: Core Tables

```sql
CREATE SCHEMA IF NOT EXISTS trading_platform;

-- Assets we trade
CREATE TABLE trading_platform.assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL UNIQUE,     -- e.g. 'CRO', 'BTC', 'ETH'
    name VARCHAR(64),
    coingecko_id VARCHAR(64),
    exchange_symbol VARCHAR(32),             -- e.g. 'CRO/USDT'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily OHLCV data
CREATE TABLE trading_platform.ohlcv_daily (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    date DATE NOT NULL,
    open NUMERIC(20,8),
    high NUMERIC(20,8),
    low NUMERIC(20,8),
    close NUMERIC(20,8),
    volume NUMERIC(24,2),
    source VARCHAR(32) DEFAULT 'coingecko',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, date, source)
);

-- Computed technical indicators
CREATE TABLE trading_platform.indicators_daily (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    date DATE NOT NULL,
    rsi_14 NUMERIC(8,4),
    ema_20 NUMERIC(20,8),
    ema_50 NUMERIC(20,8),
    ema_200 NUMERIC(20,8),
    sma_50 NUMERIC(20,8),
    sma_200 NUMERIC(20,8),
    macd NUMERIC(20,8),
    macd_signal NUMERIC(20,8),
    macd_hist NUMERIC(20,8),
    atr_14 NUMERIC(20,8),
    adx_14 NUMERIC(8,4),
    bb_upper NUMERIC(20,8),
    bb_lower NUMERIC(20,8),
    bb_width NUMERIC(8,4),
    volume_sma_20 NUMERIC(24,2),
    regime_score NUMERIC(6,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, date)
);

-- Live price snapshots
CREATE TABLE trading_platform.price_ticks (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    price NUMERIC(20,8) NOT NULL,
    bid NUMERIC(20,8),
    ask NUMERIC(20,8),
    volume_24h NUMERIC(24,2),
    source VARCHAR(32) DEFAULT 'exchange',
    observed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Strategy configurations
CREATE TABLE trading_platform.strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    type VARCHAR(32) NOT NULL,               -- 'dca_grid', 'momentum', etc.
    asset_id INT REFERENCES trading_platform.assets(id),
    params JSONB NOT NULL DEFAULT '{}',      -- strategy-specific parameters
    is_active BOOLEAN DEFAULT FALSE,
    paper_mode BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Migration 002: Orders & Executions

```sql
-- Orders placed (open, filled, cancelled)
CREATE TABLE trading_platform.orders (
    id BIGSERIAL PRIMARY KEY,
    strategy_id INT REFERENCES trading_platform.strategies(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    side VARCHAR(4) NOT NULL,                -- 'buy' or 'sell'
    type VARCHAR(16) NOT NULL,               -- 'limit' or 'market'
    quantity NUMERIC(20,8) NOT NULL,
    price NUMERIC(20,8),                     -- NULL for market orders
    stop_loss NUMERIC(20,8),
    take_profit NUMERIC(20,8),
    status VARCHAR(16) DEFAULT 'open',       -- open, filled, partial, cancelled
    exchange_order_id VARCHAR(64),
    rationale TEXT,                           -- why this trade
    paper BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Execution fills
CREATE TABLE trading_platform.executions (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES trading_platform.orders(id),
    quantity NUMERIC(20,8) NOT NULL,
    price NUMERIC(20,8) NOT NULL,
    fee NUMERIC(20,8) DEFAULT 0,
    fee_currency VARCHAR(8) DEFAULT 'USDT',
    executed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Migration 003: Portfolio & P&L

```sql
-- Daily portfolio snapshots
CREATE TABLE trading_platform.portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_value_usdt NUMERIC(20,2),
    cash_usdt NUMERIC(20,2),
    positions_value_usdt NUMERIC(20,2),
    unrealized_pnl NUMERIC(20,2),
    realized_pnl_day NUMERIC(20,2),
    hodl_value_usdt NUMERIC(20,2),           -- benchmark: what if we just held
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date)
);

-- Trade journal (Robin's notes)
CREATE TABLE trading_platform.trade_journal (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES trading_platform.orders(id),
    entry_reason TEXT,
    exit_reason TEXT,
    lessons_learned TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Open positions (derived view)
CREATE VIEW trading_platform.open_positions AS
SELECT
    o.asset_id, a.symbol, a.exchange_symbol,
    SUM(CASE WHEN o.side = 'buy' THEN e.quantity ELSE -e.quantity END) as net_quantity,
    SUM(CASE WHEN o.side = 'buy' THEN e.quantity * e.price ELSE 0 END) /
        NULLIF(SUM(CASE WHEN o.side = 'buy' THEN e.quantity ELSE 0 END), 0) as avg_entry_price,
    SUM(e.fee) as total_fees
FROM trading_platform.orders o
JOIN trading_platform.executions e ON e.order_id = o.id
JOIN trading_platform.assets a ON a.id = o.asset_id
WHERE o.status IN ('filled', 'partial')
GROUP BY o.asset_id, a.symbol, a.exchange_symbol
HAVING SUM(CASE WHEN o.side = 'buy' THEN e.quantity ELSE -e.quantity END) > 0;
```

## CLI Tools (Robin's Interface)

All CLI tools output JSON and accept `--help`. Robin operates the system entirely through these commands via shell.

### `cli/market.py` — Market Data

```bash
# Fetch and store daily OHLCV for all active assets
python -m cli.market fetch-ohlcv

# Fetch and store latest price tick
python -m cli.market fetch-price --symbol CRO

# Compute and store indicators for a date
python -m cli.market compute-indicators --date 2026-03-31

# Get latest market overview (JSON output)
python -m cli.market overview
# → {"CRO": {"price": 0.085, "rsi_14": 42.3, "regime": 55, ...}, ...}

# Get OHLCV history
python -m cli.market history --symbol CRO --days 30
```

### `cli/signals.py` — Signal Detection

```bash
# Check all active strategies for entry/exit signals
python -m cli.signals scan
# → [{"strategy": "cro_momentum", "signal": "buy", "confidence": 0.78, "reason": "RSI oversold + EMA crossover"}, ...]

# Check specific asset
python -m cli.signals check --symbol CRO
# → {"buy_signals": [...], "sell_signals": [...], "regime": "trending", "score": 62}
```

### `cli/trade.py` — Order Management

```bash
# Place a buy order (validates against guardrails)
python -m cli.trade buy --symbol CRO --amount 100 --price 0.085 --stop-loss 0.081 --rationale "RSI oversold bounce"
# → {"order_id": 42, "status": "open", "guardrail_check": "PASS"}

# Place a sell order
python -m cli.trade sell --symbol CRO --quantity 1000 --price 0.092 --rationale "Take profit at resistance"

# Cancel an order
python -m cli.trade cancel --order-id 42

# List open orders
python -m cli.trade list-orders --status open

# Check order status
python -m cli.trade status --order-id 42

# Sync fills from exchange (check if open orders were filled)
python -m cli.trade sync-fills
```

### `cli/portfolio.py` — Portfolio & P&L

```bash
# Current portfolio snapshot
python -m cli.portfolio balance
# → {"cash_usdt": 850.00, "positions": [{"symbol": "CRO", "qty": 1000, "value": 85.00, "pnl": +2.50}], "total": 935.00}

# Today's P&L
python -m cli.portfolio pnl --period today
# → {"realized": 12.50, "unrealized": -3.20, "fees": 1.80, "net": 7.50}

# Performance vs HODL benchmark
python -m cli.portfolio benchmark --days 30
# → {"strategy_return": "+8.5%", "hodl_return": "+3.2%", "alpha": "+5.3%"}

# Take daily snapshot (run end of day)
python -m cli.portfolio snapshot

# Trade history
python -m cli.portfolio history --days 7
# → [{"date": "...", "side": "buy", "symbol": "CRO", "qty": 500, "price": 0.083, "pnl": null}, ...]
```

### `cli/strategy.py` — Strategy Configuration

```bash
# List strategies
python -m cli.strategy list
# → [{"id": 1, "name": "cro_momentum", "type": "momentum", "active": true, "paper": true, "params": {...}}]

# View strategy params
python -m cli.strategy view --name cro_momentum

# Update strategy params (no code change needed)
python -m cli.strategy update --name cro_momentum --param rsi_buy_threshold=28 --param stop_loss_pct=4.5

# Activate/deactivate
python -m cli.strategy activate --name cro_momentum
python -m cli.strategy deactivate --name cro_momentum

# Switch paper/live mode
python -m cli.strategy set-mode --name cro_momentum --mode live
```

## Guardrails (guardrails.py)

Human-authored, PR-protected. All trade commands import and validate against these limits before executing.

```python
# guardrails.py — HUMAN AUTHORED, CODEOWNERS PROTECTED

MAX_POSITION_PCT = 0.10          # Max 10% of portfolio per trade
MAX_DAILY_LOSS_PCT = 0.05        # Stop trading if daily loss > 5%
MAX_OPEN_POSITIONS = 3           # Max 3 concurrent positions
STOP_LOSS_REQUIRED = True        # Every buy order must have stop-loss
MAX_STOP_LOSS_PCT = 0.08         # Stop-loss can't be wider than 8%
MIN_TRADE_SIZE_USDT = 5.0        # Minimum trade size
HUMAN_APPROVAL_THRESHOLD = 0.20  # Trades > 20% of portfolio need human approval
ALLOWED_SYMBOLS = ["CRO/USDT"]   # Only trade approved pairs
PAPER_MODE_DEFAULT = True         # Default to paper trading

def validate_order(balance_usdt, trade_amount_usdt, open_positions,
                   daily_pnl, symbol, has_stop_loss):
    """Validate order against guardrails. Returns (ok, reason)."""
    if symbol not in ALLOWED_SYMBOLS:
        return False, f"Symbol not allowed: {symbol}"
    if trade_amount_usdt < MIN_TRADE_SIZE_USDT:
        return False, f"Trade too small: {trade_amount_usdt} < {MIN_TRADE_SIZE_USDT}"
    if trade_amount_usdt > balance_usdt * MAX_POSITION_PCT:
        return False, f"Position too large: {trade_amount_usdt} > {MAX_POSITION_PCT*100}% of {balance_usdt}"
    if STOP_LOSS_REQUIRED and not has_stop_loss:
        return False, "Stop-loss required on every buy order"
    if abs(daily_pnl) > balance_usdt * MAX_DAILY_LOSS_PCT:
        return False, f"Daily loss limit reached: {daily_pnl}"
    if open_positions >= MAX_OPEN_POSITIONS:
        return False, f"Max positions reached: {open_positions}/{MAX_OPEN_POSITIONS}"
    if trade_amount_usdt > balance_usdt * HUMAN_APPROVAL_THRESHOLD:
        return False, f"Needs human approval: {trade_amount_usdt} > {HUMAN_APPROVAL_THRESHOLD*100}% of portfolio"
    return True, "OK"
```

## Robin's Code Access

| Area | Can Modify? | How |
|------|------------|-----|
| `strategies/*.py` | Yes | Via PR, human reviews |
| `core/indicators.py` | Yes | Via PR, human reviews |
| `cli/*.py` | Yes | Via PR, human reviews |
| Strategy params (DB) | Yes, freely | Via `cli/strategy.py update` — no code change |
| `tests/` | Yes | Via PR |
| `guardrails.py` | **NO** | CODEOWNERS: requires human approval |
| `core/exchange.py` | **NO** | CODEOWNERS: core infra |
| `core/db.py` | **NO** | CODEOWNERS: core infra |
| `core/config.py` | **NO** | CODEOWNERS: security |
| `db/migrations/` | **NO** | CODEOWNERS: schema changes |

## Robin's Trading Workflow

```
Every hour (recurring task ROB-010):
1. python -m cli.market fetch-price --symbol CRO
2. python -m cli.signals scan
3. If signal detected:
   a. python -m cli.portfolio balance (check available capital)
   b. python -m cli.trade buy --symbol CRO --amount X --stop-loss Y --rationale "..."
   c. Store rationale in memory
   d. Report trade to Discord
4. python -m cli.trade sync-fills (check if open orders filled)
5. Check open positions for stop-loss / take-profit triggers

Every day (recurring task ROB-012):
1. python -m cli.market fetch-ohlcv
2. python -m cli.market compute-indicators
3. python -m cli.portfolio snapshot
4. python -m cli.portfolio pnl --period today
5. Report daily summary to Discord

Weekly (recurring task ROB-013):
1. python -m cli.portfolio benchmark --days 7
2. Review strategy performance
3. If strategy underperforming → adjust params or create PR with improvement
```

## Implementation Steps

- [ ] Phase 1: Create `inotives/robin-trading` repo with structure
- [ ] Phase 1: Write `pyproject.toml`, `core/config.py`, `core/db.py`
- [ ] Phase 1: Write DB migrations (3 files)
- [ ] Phase 1: Write `guardrails.py` + `tests/test_guardrails.py`
- [ ] Phase 1: Add `.github/CODEOWNERS` + branch protection
- [ ] Phase 2: Write `core/exchange.py` (ccxt wrapper with paper mode)
- [ ] Phase 2: Write `core/indicators.py` (pandas-ta computation)
- [ ] Phase 2: Write `cli/market.py` (fetch OHLCV, prices, compute indicators)
- [ ] Phase 2: Write `cli/signals.py` (signal detection)
- [ ] Phase 3: Write `cli/trade.py` (order placement with guardrail validation)
- [ ] Phase 3: Write `cli/portfolio.py` (balance, P&L, benchmark, snapshot)
- [ ] Phase 3: Write `cli/strategy.py` (strategy CRUD)
- [ ] Phase 4: Write `strategies/momentum.py` (initial strategy)
- [ ] Phase 4: Register repo for Robin: `make repo-add`
- [ ] Phase 4: Create trading skills for Robin (operations, safety, tracking)
- [ ] Phase 4: Equip skills to Robin
- [ ] Phase 5: Paper trading for 1-2 weeks
- [ ] Phase 5: Human review paper trading results
- [ ] Phase 5: Switch to live mode
- [ ] Phase 6: Add recurring trading tasks (hourly scan, daily report, weekly review)

## Guardrails & Safety

| Guardrail | Level | Details |
|-----------|-------|---------|
| Position size limit | Code | Max 10% of portfolio per trade |
| Daily loss limit | Code | Max 5% daily loss, auto-stop |
| Stop-loss mandatory | Code | Every buy must have stop-loss |
| Max open positions | Code | Max 3 concurrent positions |
| Human approval gate | Code | Trades > 20% need human approval |
| Allowed symbols | Code | Only trade approved pairs |
| Paper mode default | Code | New strategies start in paper mode |
| PR gate for code | Git | Strategy changes require human PR review |
| Protected guardrails | Git | `guardrails.py` requires CODEOWNERS approval |
| Trade journal | DB | Every trade logged with rationale |
| Discord reporting | Skill | Every trade reported immediately |
| Weekly review | Task | Mandatory weekly performance review |
| Kill switch | Config | `paper_mode=true` on strategy stops live trades |

## Risk Acknowledgment

- This is **real money** (1000 CRO). Robin can lose it.
- Crypto markets are volatile. 1000 CRO can go to 0.
- LLM trading strategies are experimental — no guarantees.
- Guardrails prevent catastrophic loss but not gradual losses.
- Human should review weekly and adjust strategy/limits as needed.
- Paper trading MUST run for 1-2 weeks before live.

## Dependencies

- Python 3.12, uv
- ccxt, pandas, pandas-ta, requests, asyncpg, psycopg, pydantic-settings
- dbmate (migrations)
- Shared Postgres DB (`inotives` DB, `trading_platform` schema)
- crypto.com Exchange account with API access
- ES-0009 (proactive behavior) for recurring task execution

## Success Criteria

- Robin can operate the full trading lifecycle via CLI commands
- All trades validated against `guardrails.py` before execution
- Paper trading runs for 1-2 weeks with documented results
- Portfolio performance tracked daily, compared against HODL benchmark
- All trades logged with rationale and reportable
- Robin can tune strategy params without code changes
- Robin can submit PRs for strategy improvements
- Human can enable/disable any strategy with one command

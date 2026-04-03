# ES-0012 — inotagent-trading

## Status: DRAFT (project spec)

> This document is the project specification for `inotagent-trading/` — a trading toolkit subfolder within the openvaia monorepo. Robin interacts with it purely via CLI (shell tool calls) and strategy param tuning (DB-level). All code changes are human-authored.

## Overview

**inotagent-trading** is a Python sub-project within the openvaia repo (`inotagent-trading/`) that provides two things:

1. **Data Poller** — continuously fetches market data (price, ticker, spread, OHLCV) every 1 minute, computes intraday technical analysis metrics, and stores in Postgres
2. **CLI Tools** — agent-invokable commands (all JSON output) for market data queries, signal detection, order management, and portfolio tracking

Agents (primarily Robin) interact with the toolkit via `shell` tool calls. The poller runs as a background process alongside the agent.

## Architecture

```
openvaia repo
└── inotagent-trading/              ← subfolder, not separate repo
    │
    ┌─────────────────────────────────────────────────────┐
    │                  inotagent-trading                    │
    │                                                       │
    │  ┌─────────────────────┐  ┌─────────────────────────┐│
    │  │   Data Pollers       │  │   CLI Tools (agent use) ││
    │  │   (Docker services)  │  │                         ││
    │  │                      │  │  cli/market.py           ││
    │  │  poller-public:      │  │  cli/signals.py          ││
    │  │  • fetch ticker      │  │  cli/trade.py            ││
    │  │  • fetch OHLCV 1m    │  │  cli/portfolio.py        ││
    │  │                      │  │  cli/strategy.py         ││
    │  │  poller-private:     │  │  cli/backtest.py         ││
    │  │  • sync balances     │  │                         ││
    │  │  • sync fills        │  │  (all output JSON)       ││
    │  │                      │  │                         ││
    │  │  poller-ta:          │  │                         ││
    │  │  • compute TA        │  │                         ││
    │  └──────────┬───────────┘  └──────────┬──────────────┘│
    │             │                         │                │
    │             ▼                         ▼                │
    │  ┌─────────────────────────────────────────────────┐  │
    │  │              core/ (shared library)               │  │
    │  │                                                   │  │
    │  │  exchange.py     — ccxt wrapper (paper + live)    │  │
    │  │  indicators.py   — TA computation (pandas-ta)     │  │
    │  │  models.py       — data models                    │  │
    │  │  config.py       — pydantic-settings              │  │
    │  │  db.py           — Postgres (trading_platform)    │  │
    │  └──────────────────────┬────────────────────────────┘  │
    │                         │                                │
    │                         ▼                                │
    │  ┌─────────────────────────────────────────────────────┐│
    │  │  Postgres (trading_platform schema)                  ││
    │  │  Same DB as openvaia, different schema                ││
    │  └─────────────────────────────────────────────────────┘│
    │                                                          │
    │  ┌─────────────────────────────────────────────────────┐│
    │  │  guardrails.py (HUMAN-AUTHORED, CODEOWNERS)          ││
    │  └─────────────────────────────────────────────────────┘│
    └──────────────────────────────────────────────────────────┘

Agent (Robin) interaction — CLI only, no git operations:
  # Baked into image at /opt/inotagent-trading (or volume-mounted in dev)
  shell("cd /opt/inotagent-trading && python -m cli.market overview")
  shell("cd /opt/inotagent-trading && python -m cli.signals scan")
  shell("cd /opt/inotagent-trading && python -m cli.trade buy --symbol CRO --amount 100 ...")
  shell("cd /opt/inotagent-trading && python -m cli.strategy update --param entry.rsi_buy=25")
```

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python 3.12 |
| Package manager | uv |
| Exchange API | ccxt |
| Data analysis | pandas, pandas-ta |
| HTTP client | requests |
| Database | asyncpg (poller — async), psycopg (CLI — sync). `core/db.py` provides both `async_pool()` and `sync_connect()` |
| Config | pydantic-settings (.env) |
| Migrations | dbmate (`inotagent-trading/db/migrations/`) |
| Scheduling | asyncio (poller loop) |

## Project Structure

Lives under `inotagent-trading/` in the openvaia monorepo root. Migrations are self-contained in `inotagent-trading/db/migrations/` (separate schema, separate lifecycle). CODEOWNERS rules are in the repo-level `.github/CODEOWNERS`.

```
openvaia/                              ← monorepo root
├── .github/CODEOWNERS                 ← add inotagent-trading/guardrails.py, core/exchange.py, core/db.py
│
├── inotagent-trading/                 ← trading toolkit subfolder
│   ├── pyproject.toml                 # separate Python package (uv managed)
│   ├── Dockerfile                     # for poller services + baked into agent image
│   ├── .dockerignore
│   ├── .python-version               # 3.12
│   ├── .env.template
│   ├── guardrails.py                  # HUMAN-AUTHORED, CODEOWNERS-PROTECTED
│   │
│   ├── poller/                        # Background pollers (Docker services)
│   │   ├── public/                    # Public market data (no API key needed)
│   │   │   ├── __main__.py            # Entry point: python -m poller.public
│   │   │   ├── ohlcv.py              # Fetch 1m candles + ticker (bid/ask/spread)
│   │   │   └── orderbook.py          # Fetch order book depth (future)
│   │   ├── private/                   # Private account data (API key required)
│   │   │   ├── __main__.py            # Entry point: python -m poller.private
│   │   │   ├── balances.py            # Sync exchange + wallet balances
│   │   │   ├── orders.py             # Sync open orders, detect fills
│   │   │   └── positions.py          # Sync open positions
│   │   └── ta/                        # TA computation (DB only, no exchange calls)
│   │       ├── __main__.py            # Entry point: python -m poller.ta
│   │       ├── intraday.py            # Compute intraday TA from 1m candles
│   │       ├── aggregate.py           # Aggregate 1m → 1h, 4h candles
│   │       └── daily.py              # Compute daily TA from OHLCV
│   │
│   ├── cli/                           # Agent CLI tools (all JSON output)
│   │   ├── market.py                  # Market data queries + seeding + setup
│   │   ├── signals.py                # Signal detection (rules engine)
│   │   ├── trade.py                  # Order management
│   │   ├── portfolio.py              # Balance, P&L, transfers, reconciliation
│   │   ├── strategy.py              # Strategy CRUD + version history
│   │   └── backtest.py              # Backtesting + param sweep
│   │
│   ├── core/                          # Shared library
│   │   ├── config.py                  # pydantic-settings
│   │   ├── db.py                     # Postgres connection (trading_platform)
│   │   ├── exchange.py               # ccxt wrapper (paper + live)
│   │   ├── indicators.py            # TA indicator computation
│   │   └── models.py                # Data models
│   │
│   ├── strategies/                    # Strategy implementations (human-authored)
│   │   ├── base.py                    # Abstract interface
│   │   └── momentum.py              # Initial strategy
│   │
│   ├── db/migrations/                 # trading_platform schema migrations
│   │   ├── 001_trading_core.sql       # schema, venues, networks, network_mappings, assets, asset_mappings,
│   │   │                              #   trading_pairs, ohlcv_1m, ohlcv_daily, indicators_intraday,
│   │   │                              #   indicators_daily, ohlcv_1h/4h views, strategies, ext_coingecko_*
│   │   ├── 002_trading_orders.sql     # orders, order_events, executions
│   │   ├── 003_trading_portfolio.sql  # portfolio_snapshots, portfolio_asset_snapshots,
│   │   │                              #   portfolio_strategy_snapshots, pnl_realized, cost_basis,
│   │   │                              #   paper_balances, trade_journal, open_positions view
│   │   ├── 004_trading_accounts.sql   # accounts, balances, balances_ledger, transfers,
│   │   │                              #   total_balances view, balance_reconciliation view
│   │   └── 005_trading_backtest.sql   # backtest_runs, backtest_trades, backtest_equity
│   │
│   ├── data/seeds/                    # CSV files for historical data (gitignored)
│   │
│   └── tests/
│       ├── test_guardrails.py         # guardrail validation rules
│       ├── test_indicators.py        # TA computation correctness
│       ├── test_signals.py           # signal detection + confidence scoring
│       ├── test_poller.py            # poller cycle + error handling
│       ├── test_exchange.py          # paper vs live exchange wrapper
│       ├── test_cost_basis.py        # FIFO lot consumption + P&L
│       └── test_backtest.py          # backtest fill logic + guardrail enforcement
```

## Pollers

Three independent background processes, separated by data source and auth requirements.

### Public Data Poller (`poller.public`)

**Job:** Collect public market data. No API key needed. Fast, must not fail.

Every cycle (default 60s):
1. **Fetch 1m candles** — OHLCV for all active assets
2. **Fetch ticker** — bid, ask, spread, 24h volume (merged into `ohlcv_1m`)
3. **Store to DB** — `ohlcv_1m` (enriched with bid/ask/spread)

```bash
python -m poller.public --pairs CRO/USDT,BTC/USDT --interval 60
```

### Private Data Poller (`poller.private`)

**Job:** Sync account data from exchange. Requires API key. Handles auth separately.

Every cycle (default 60s):
1. **Sync balances** — fetch from exchange (ccxt `fetch_balance()`), update `balances` table
2. **Sync open orders** — detect fills, update `orders` + `executions`
3. **Sync positions** — update `open_positions` data

Future: DeFi wallet balances via RPC/block explorer APIs.

```bash
python -m poller.private --exchange cryptocom --interval 60
```

### TA Compute Poller (`poller.ta`)

**Job:** Compute technical analysis. No exchange calls — reads from DB only.

Every cycle (default 60s):
1. **Compute intraday TA** from 1m candles (1h/4h aggregation handled by DB views):
   - RSI (14-period), EMA (9, 21), VWAP
   - Spread % (from bid/ask in ohlcv_1m)
   - Volatility (1h rolling standard deviation)
   - Volume ratio (current vs 20-period average)
2. **Compute daily TA** (once per day, after `cli/market.py fetch-daily` has run) from `ohlcv_daily`:
   - RSI(14), EMA(20/50/200), SMA(50/200), MACD
   - ATR(14), ADX(14), Bollinger Bands
   - Regime score (trend strength)
   - Skips if `ohlcv_daily` data is stale (no new rows since last computation)
3. **Store to DB** — `indicators_intraday`, `indicators_daily`

```bash
python -m poller.ta --interval 60
```

### Why three pollers?

| Concern | Public | Private | TA |
|---------|--------|---------|-----|
| **Auth** | No API key | API key required | No exchange calls |
| **Speed** | Fast (<5s) | Medium (<10s) | Slow (10-30s) |
| **Failure** | Exchange down → retry | Auth expired → only this breaks | Compute error → data still flows |
| **Rate limits** | Public limits | Private limits (separate) | N/A (DB only) |
| **Credentials** | None | Sensitive (API key + secret) | None |
| **Dependencies** | Exchange API | Exchange API | DB tables only |

### Running all three

```bash
# Via Docker Compose (production — from repo root)
make trading-start              # docker compose up -d poller-public poller-private poller-ta
make trading-stop               # stop all poller services
make trading-status             # check health of all pollers

# Local development (without Docker)
cd inotagent-trading
python -m poller.public --pairs CRO/USDT,BTC/USDT --interval 60 &
python -m poller.private --exchange cryptocom --interval 60 &
python -m poller.ta --interval 60 &
```

### Error Handling & Health

Each poller implements:
- **Retry with backoff:** On exchange/DB errors, retry 3x with exponential backoff (1s, 4s, 16s). After 3 failures, skip cycle and log error.
- **Health heartbeat:** Each poller writes to a `poller_status` file at `/opt/inotagent-trading/.poller_status.json` (JSON, one key per poller). Agent queries via `cli/market.py poller-status`. No DB table needed — file is simpler and works even when DB is down.
- **Graceful degradation:** If public poller fails, TA poller uses stale data (logs warning). If private poller fails, stop-loss monitoring pauses (logs CRITICAL alert to Discord).
- **Cycle timing:** Each cycle measures duration. If cycle takes longer than interval, skip next cycle (don't queue up).

```bash
python -m cli.market poller-status            # health of all 3 pollers (JSON)
# → {"public": {"status": "ok", "last_success": "2s ago", "errors_1h": 0},
#    "private": {"status": "ok", "last_success": "5s ago", "errors_1h": 1},
#    "ta": {"status": "ok", "last_success": "12s ago", "errors_1h": 0}}
```

### Poller tables

```sql
-- 1-minute OHLCV + ticker data (public poller, every 60s)
CREATE TABLE trading_platform.ohlcv_1m (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    timestamp TIMESTAMPTZ NOT NULL,
    open NUMERIC(20,8),
    high NUMERIC(20,8),
    low NUMERIC(20,8),
    close NUMERIC(20,8),
    volume NUMERIC(24,8),
    bid NUMERIC(20,8),               -- from ticker, same poll cycle
    ask NUMERIC(20,8),               -- from ticker, same poll cycle
    spread_pct NUMERIC(10,6),        -- computed: (ask-bid)/mid * 100
    volume_24h NUMERIC(24,2),        -- from ticker
    UNIQUE (asset_id, venue_id, timestamp)
);

-- Aggregated candles as VIEWS (computed on-the-fly from ohlcv_1m)
-- No separate tables to manage — retention controlled by ohlcv_1m only

CREATE VIEW trading_platform.ohlcv_1h AS
SELECT
    asset_id,
    venue_id,
    date_trunc('hour', timestamp) AS timestamp,
    (array_agg(open ORDER BY timestamp ASC))[1] AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    (array_agg(close ORDER BY timestamp DESC))[1] AS close,
    SUM(volume) AS volume
FROM trading_platform.ohlcv_1m
GROUP BY asset_id, venue_id, date_trunc('hour', timestamp);

CREATE VIEW trading_platform.ohlcv_4h AS
SELECT
    asset_id,
    venue_id,
    date_trunc('hour', timestamp) - (EXTRACT(hour FROM timestamp)::int % 4) * INTERVAL '1 hour' AS timestamp,
    (array_agg(open ORDER BY timestamp ASC))[1] AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    (array_agg(close ORDER BY timestamp DESC))[1] AS close,
    SUM(volume) AS volume
FROM trading_platform.ohlcv_1m
GROUP BY asset_id, venue_id, date_trunc('hour', timestamp) - (EXTRACT(hour FROM timestamp)::int % 4) * INTERVAL '1 hour';

-- Indexes defined in "Database Indexes" section below

-- Intraday TA (computed from 1m candles)
-- Standard columns + custom JSONB for extensibility
CREATE TABLE trading_platform.indicators_intraday (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    timestamp TIMESTAMPTZ NOT NULL,          -- candle period this represents
    -- Momentum
    rsi_14 NUMERIC(8,4),
    rsi_7 NUMERIC(8,4),
    stoch_rsi_k NUMERIC(8,4),
    stoch_rsi_d NUMERIC(8,4),
    -- Trend
    ema_9 NUMERIC(20,8),
    ema_21 NUMERIC(20,8),
    ema_55 NUMERIC(20,8),                    -- medium-term intraday
    -- Volume & Price
    vwap NUMERIC(20,8),
    volume_ratio NUMERIC(10,4),
    obv NUMERIC(24,2),
    -- Volatility
    spread_pct NUMERIC(10,6),
    volatility_1h NUMERIC(10,6),
    atr_14 NUMERIC(20,8),
    -- Extensible
    custom JSONB DEFAULT '{}',
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, venue_id, timestamp)
);

-- Exchange + wallet balances (private poller, every 60s)
-- Accounts on venues (exchange sub-accounts, wallet addresses)
CREATE TABLE trading_platform.accounts (
    id SERIAL PRIMARY KEY,
    venue_id INT REFERENCES trading_platform.venues(id),
    name VARCHAR(64) NOT NULL,               -- 'main', 'trading', 'earn', 'margin'
    account_type VARCHAR(16) NOT NULL,       -- 'spot', 'margin', 'futures', 'earn', 'wallet'
    address VARCHAR(128),                    -- wallet address (for DeFi/self-custody)
    network_id INT REFERENCES trading_platform.networks(id),  -- chain (for wallets)
    is_default BOOLEAN DEFAULT FALSE,        -- default account for this venue
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64),
    UNIQUE (venue_id, name, COALESCE(address, ''), COALESCE(network_id, 0))
);
-- Examples:
-- (cryptocom, 'main',    'spot',    NULL,            NULL,     true)
-- (cryptocom, 'earn',    'earn',    NULL,            NULL,     false)
-- (metamask,  'hot-1',   'wallet',  '0xabc...def',  ethereum, true)
-- (metamask,  'hot-1',   'wallet',  '0xabc...def',  cronos,   false)  -- same address, different chain
-- (phantom,   'main',    'wallet',  'ABC...xyz',    solana,   true)

-- Asset balances per account (live source — synced from exchanges by private poller)
CREATE TABLE trading_platform.balances (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES trading_platform.accounts(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    balance NUMERIC(20,8) NOT NULL DEFAULT 0,
    available NUMERIC(20,8),                 -- available for trading (balance minus locked)
    locked NUMERIC(20,8) DEFAULT 0,          -- in open orders, staking, etc.
    balance_usdt NUMERIC(20,2),              -- estimated USDT value at sync
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (account_id, asset_id)
);

-- Balance ledger: append-only audit trail of all balance-affecting events
-- Not the source of truth (balances table is) — used for reconciliation and anomaly detection
CREATE TABLE trading_platform.balances_ledger (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES trading_platform.accounts(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    amount NUMERIC(20,8) NOT NULL,           -- positive = credit (inflow), negative = debit (outflow)
    balance_after NUMERIC(20,8),             -- snapshot of balance after this event
    entry_type VARCHAR(16) NOT NULL,         -- 'trade', 'fee', 'deposit', 'withdrawal', 'transfer', 'bridge', 'reward', 'external'
    reference_type VARCHAR(16),              -- 'order', 'execution', 'transfer'
    reference_id BIGINT,                     -- FK to orders.id, executions.id, or transfers.id
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Index: idx_ledger_account_asset — see "Database Indexes" section

-- Examples:
-- Buy 1000 CRO with USDT:
--   (cryptocom:main, USDT, -85.00,  915.00,  'trade',  'execution', 101)
--   (cryptocom:main, CRO,  +1000,   6000.00, 'trade',  'execution', 101)
--   (cryptocom:main, USDT, -0.21,   914.79,  'fee',    'execution', 101)
-- Deposit:
--   (cryptocom:main, USDT, +1000,   1914.79, 'deposit', 'transfer', 50)
-- Internal transfer:
--   (cryptocom:main, CRO,  -1000,   5000.00, 'transfer', 'transfer', 51)
--   (cryptocom:earn, CRO,  +1000,   1000.00, 'transfer', 'transfer', 51)

-- Reconciliation view: compare live balance vs ledger-computed balance
CREATE VIEW trading_platform.balance_reconciliation AS
SELECT
    b.account_id, b.asset_id, a.symbol,
    b.balance AS live_balance,
    COALESCE(SUM(l.amount), 0) AS ledger_balance,
    b.balance - COALESCE(SUM(l.amount), 0) AS discrepancy
FROM trading_platform.balances b
JOIN trading_platform.assets a ON a.id = b.asset_id
LEFT JOIN trading_platform.balances_ledger l
    ON l.account_id = b.account_id AND l.asset_id = b.asset_id
GROUP BY b.account_id, b.asset_id, a.symbol, b.balance
HAVING b.balance != COALESCE(SUM(l.amount), 0);
-- Example output (only rows WITH discrepancy are shown — HAVING clause filters):
-- account_id | asset_id | symbol | live_balance | ledger_balance | discrepancy
-- 1          | 1        | BTC    | 0.50000000   | 0.45000000     | 0.05000000   ← 0.05 BTC in open order not yet in ledger
-- 1          | 3        | USDT   | 1000.00      | 850.00         | 150.00       ← 150 USDT locked in staking

-- Transfers: all money movement (deposits, withdrawals, internal transfers)
CREATE TABLE trading_platform.transfers (
    id BIGSERIAL PRIMARY KEY,
    transfer_type VARCHAR(16) NOT NULL,      -- 'deposit', 'withdrawal', 'internal'

    -- Source (NULL for deposits from external)
    from_account_id INT REFERENCES trading_platform.accounts(id),
    from_address VARCHAR(128),               -- external sender address (for on-chain deposits)

    -- Destination (NULL for withdrawals to external)
    to_account_id INT REFERENCES trading_platform.accounts(id),
    to_address VARCHAR(128),                 -- external recipient address (for withdrawals)

    -- What was transferred
    asset_id INT REFERENCES trading_platform.assets(id),
    amount NUMERIC(20,8) NOT NULL,
    amount_usdt NUMERIC(20,2),               -- estimated USDT value at transfer time

    -- On-chain details (NULL for off-chain / internal)
    network_id INT REFERENCES trading_platform.networks(id),
    tx_hash VARCHAR(128),                    -- blockchain transaction hash

    -- Off-chain details (bank transfers, fiat deposits)
    method VARCHAR(32),                      -- 'onchain', 'bank_wire', 'card', 'internal', 'ach', 'sepa'
    reference VARCHAR(128),                  -- bank reference, venue transfer ID

    -- Fees
    fee NUMERIC(20,8) DEFAULT 0,
    fee_asset VARCHAR(16),                   -- fee currency (may differ from transfer asset)

    -- Status
    status VARCHAR(16) DEFAULT 'pending',    -- 'pending', 'completed', 'failed', 'cancelled'

    -- Audit
    initiated_by VARCHAR(64),                -- 'robin', 'boss', 'system'
    initiated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    notes TEXT
);
-- Examples:
--
-- Deposit (bank → crypto.com):
--   type='deposit', from_account=NULL,
--   to_account=cryptocom:main, asset=USDT, amount=1000,
--   method='bank_wire', reference='TXN-123', status='completed'
--
-- Deposit (on-chain → metamask):
--   type='deposit', from_account=NULL, from_address='0xsender...',
--   to_account=metamask:hot-1, asset=ETH, amount=0.5,
--   network=ethereum, tx_hash='0xabc...', method='onchain', status='completed'
--
-- Withdrawal (crypto.com → external wallet):
--   type='withdrawal', from_account=cryptocom:main,
--   to_account=NULL, to_address='0xrecipient...',
--   asset=CRO, amount=500, network=cronos, tx_hash='0xdef...',
--   method='onchain', fee=0.1, fee_asset='CRO', status='completed'
--
-- Internal transfer (crypto.com main → earn):
--   type='internal', from_account=cryptocom:main,
--   to_account=cryptocom:earn, asset=CRO, amount=1000,
--   method='internal', reference='INT-456', status='completed'
--
-- Cross-chain bridge (cronos → ethereum):
--   Two rows linked by reference:
--   Row 1: type='withdrawal', from_account=metamask:hot-1,
--          asset=CRO, amount=500, network=cronos, tx_hash='0x111...',
--          method='bridge', reference='bridge-20260402-001', status='completed'
--   Row 2: type='deposit', to_account=metamask:hot-1,
--          asset=CRO, amount=499.5, network=ethereum, tx_hash='0x222...',
--          method='bridge', reference='bridge-20260402-001', status='completed',
--          fee=0.5, fee_asset='CRO'
--
-- DeFi wallet to wallet (same chain):
--   type='internal', from_account=metamask:hot-1, to_account=metamask:hot-2,
--   asset=ETH, amount=0.5, network=ethereum, tx_hash='0x333...',
--   method='onchain', status='completed'

-- Aggregated view: total balance per asset across all accounts
CREATE VIEW trading_platform.total_balances AS
SELECT
    a.id AS asset_id,
    a.symbol,
    SUM(b.balance) AS total_balance,
    SUM(b.available) AS total_available,
    SUM(b.locked) AS total_locked,
    SUM(b.balance_usdt) AS total_usdt,
    COUNT(DISTINCT acc.venue_id) AS venue_count
FROM trading_platform.balances b
JOIN trading_platform.accounts acc ON acc.id = b.account_id
JOIN trading_platform.assets a ON a.id = b.asset_id
WHERE acc.deleted_at IS NULL AND acc.is_active = true
GROUP BY a.id, a.symbol;
```

### Data Retention & Archival

| Table/View | Type | Live Retention | Archive |
|------------|------|---------------|---------|
| `ohlcv_1m` | Table | 30 days | Daily parquet: `archive/ohlcv_1m/YYYY-MM-DD.parquet` |
| `ohlcv_1h` | **View** | Derived from 1m | N/A — computed on-the-fly |
| `ohlcv_4h` | **View** | Derived from 1m | N/A — computed on-the-fly |
| `ohlcv_daily` | Table | Forever | No prune |
| `indicators_intraday` | Table | 30 days | No archive |
| `indicators_daily` | Table | Forever | No prune |
| `balances` | Table | Latest per platform+asset | No prune (upsert) |

Only `ohlcv_1m` needs retention management — everything else is either permanent or derived.

Pruning + archival runs on TA poller startup and daily at 00:00 UTC.

## Auditability & SCD

### Audit Columns

All mutable tables include:
```sql
created_at    TIMESTAMPTZ DEFAULT NOW(),
created_by    VARCHAR(64),        -- 'system', 'robin', 'boss'
updated_at    TIMESTAMPTZ DEFAULT NOW(),
updated_by    VARCHAR(64),
deleted_at    TIMESTAMPTZ,        -- soft delete (NULL = active)
deleted_by    VARCHAR(64),
```

Query pattern: `WHERE deleted_at IS NULL` for active records.

### SCD Type 2 (Full History)

For tables where past values affect trade analysis. Tracks every version:
```sql
version         INT NOT NULL DEFAULT 1,
valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
valid_to        TIMESTAMPTZ,        -- NULL = current version
is_current      BOOLEAN DEFAULT TRUE,
```

On update: set old row `is_current=false, valid_to=NOW()`, insert new row with `version+1`.

**Note:** SCD Type 2 tables use `valid_to`/`is_current` instead of `updated_at`/`deleted_at` — rows are never mutated or soft-deleted, only superseded by new versions. They only need `created_at`/`created_by`.

| Table | Audit Level | Why |
|-------|------------|-----|
| `strategies` | **SCD Type 2** | Must know what params were active for each trade |
| `trading_pairs` | **SCD Type 2** | Fees, precision, min order can change |
| `venues` | Audit + soft delete | Credentials, capabilities change |
| `networks` | Audit + soft delete | RPC URLs change |
| `assets` | Audit + soft delete | Rarely changes |
| `asset_mappings` | Audit + soft delete | Rarely changes |
| `network_mappings` | Audit + soft delete | Rarely changes |
| Append-only tables | Already auditable | `ohlcv_*`, `indicators_*`, `executions`, `portfolio_snapshots`, `trade_journal` |

### SCD Type 2 Foreign Key Pattern

Tables with SCD Type 2 versioning (`strategies`, `trading_pairs`) have multiple rows per logical entity. Foreign keys from other tables reference the `id` (row-level), not the `name` (entity-level):

```sql
-- orders.strategy_id → strategies.id (references the SPECIFIC version row)
-- orders.trading_pair_id → trading_pairs.id (references the SPECIFIC version row)
-- This means: "order was placed using strategy v2" — immutable historical link
--
-- To find the current version:  WHERE name = 'cro_momentum' AND is_current = true
-- To find version at order time: JOIN strategies ON strategies.id = orders.strategy_id
```

**Update flow for SCD Type 2:**
```sql
-- cli/strategy.py update sets old row is_current=false, valid_to=NOW()
UPDATE strategies SET is_current = false, valid_to = NOW()
WHERE name = 'cro_momentum' AND is_current = true;
-- Then inserts new row with version+1
INSERT INTO strategies (name, type, ..., version, valid_from, is_current)
VALUES ('cro_momentum', 'momentum', ..., 3, NOW(), true);
```

### Order Event Log

Track order status transitions via `order_events` table (defined in Migration 002).

### Order Audit Snapshots

Each order captures the state at creation time — immutable proof of what rules applied:

```sql
-- Added to orders table:
strategy_version INT,                -- which strategy version was active
guardrails_snapshot JSONB,           -- guardrail values at time of order
```

This answers: "Order #42 was placed with strategy v2 params and these guardrail limits."

## Database Schema (`trading_platform`)

### Migration 001: Core Tables

```sql
CREATE SCHEMA IF NOT EXISTS trading_platform;

-- Venues: exchanges, data sources, wallets, block explorers
-- Audit: soft delete
CREATE TABLE trading_platform.venues (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64),
    type VARCHAR(16) NOT NULL,               -- 'exchange', 'data', 'wallet', 'explorer'
    ccxt_id VARCHAR(32),
    capabilities JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    credentials_env JSONB,                   -- {"api_key": "CRYPTOCOM_API_KEY", "secret": "CRYPTOCOM_API_SECRET"}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(64),
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64)
);
-- Examples:
-- ('cryptocom',     'Crypto.com',     'exchange', 'cryptocom', '["spot"]',            true, '{"api_key":"CRYPTOCOM_API_KEY","secret":"CRYPTOCOM_API_SECRET"}')
-- ('kraken',        'Kraken',         'exchange', 'kraken',    '["spot","futures"]',   false, '{"api_key":"KRAKEN_API_KEY","secret":"KRAKEN_API_SECRET"}')
-- ('coingecko',     'CoinGecko',      'data',     NULL,        '["ohlcv","ticker"]',  true,  '{"api_key":"COINGECKO_API_KEY"}')
-- ('coinmarketcap', 'CoinMarketCap',  'data',     NULL,        '["ohlcv","metadata"]',true,  '{"api_key":"CMC_API_KEY"}')
-- ('metamask',      'MetaMask',       'wallet',   NULL,        '["evm"]',             true,  NULL)
-- ('phantom',       'Phantom',        'wallet',   NULL,        '["solana"]',          false, NULL)

-- Networks / chains
-- Audit: soft delete
CREATE TABLE trading_platform.networks (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(64),
    chain_id INT,                            -- EVM chain ID: 1 (eth), 25 (cronos), NULL (non-EVM)
    native_asset VARCHAR(16),
    rpc_url VARCHAR(256),
    explorer_url VARCHAR(256),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(64),
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64)
);
-- Examples:
-- ('ethereum', 'Ethereum Mainnet', 1,    'ETH', 'https://eth.llamarpc.com',     'https://etherscan.io')
-- ('cronos',   'Cronos Chain',     25,   'CRO', 'https://evm.cronos.org',       'https://cronoscan.com')
-- ('solana',   'Solana',           NULL, 'SOL', 'https://api.mainnet-beta.solana.com', 'https://solscan.io')
-- ('bitcoin',  'Bitcoin',          NULL, 'BTC', NULL,                             'https://mempool.space')

-- Network identity mappings (how each venue identifies a network)
-- Audit: soft delete
CREATE TABLE trading_platform.network_mappings (
    id SERIAL PRIMARY KEY,
    network_id INT REFERENCES trading_platform.networks(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    external_id VARCHAR(128) NOT NULL,       -- venue's identifier for this network
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(64),
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64),
    UNIQUE (network_id, venue_id)
);
-- Examples:
-- (ethereum, coingecko,     'ethereum')
-- (ethereum, coinmarketcap, 'Ethereum')
-- (ethereum, cryptocom,     'ETH')           -- crypto.com's network code for withdrawals
-- (cronos,   coingecko,     'cronos')
-- (cronos,   cryptocom,     'CRO')
-- (solana,   coingecko,     'solana')
-- (solana,   phantom,       'mainnet-beta')

-- Assets we trade (canonical symbols)
-- Audit: soft delete
CREATE TABLE trading_platform.assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(16) NOT NULL UNIQUE,
    name VARCHAR(64),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(64),
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64)
);

-- Asset identity mappings (how each venue identifies an asset)
-- Audit: soft delete
CREATE TABLE trading_platform.asset_mappings (
    id SERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    external_id VARCHAR(128) NOT NULL,       -- venue's identifier for this asset
    network_id INT REFERENCES trading_platform.networks(id),  -- for on-chain assets (DeFi)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(64),
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64),
    UNIQUE (asset_id, venue_id, COALESCE(network_id, 0))
);
-- Examples:
-- (BTC, coingecko,     'bitcoin',     NULL)    -- CoinGecko calls it 'bitcoin'
-- (BTC, coinmarketcap, '1',           NULL)    -- CMC uses numeric id '1'
-- (BTC, cryptocom,     'BTC',         NULL)    -- Crypto.com calls it 'BTC'
-- (BTC, kraken,        'XBT',         NULL)    -- Kraken calls it 'XBT'
-- (CRO, metamask,      '0x123...abc', cronos)  -- contract address on cronos network
-- (USDC, metamask,     '0xabc...def', ethereum) -- USDC on ethereum (different contract per network)

-- Trading pairs per venue — fees, precision can change over time
-- Audit: SCD Type 2
CREATE TABLE trading_platform.trading_pairs (
    id SERIAL PRIMARY KEY,
    venue_id INT REFERENCES trading_platform.venues(id),
    base_asset_id INT REFERENCES trading_platform.assets(id),
    quote_asset_id INT REFERENCES trading_platform.assets(id),
    pair_symbol VARCHAR(32) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    min_order_size NUMERIC(20,8),
    price_precision INT,
    qty_precision INT,
    maker_fee NUMERIC(10,6),
    taker_fee NUMERIC(10,6),
    -- SCD Type 2
    version INT NOT NULL DEFAULT 1,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE,
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64),
    UNIQUE (venue_id, base_asset_id, quote_asset_id, version)
);
-- Examples:
-- (cryptocom, BTC, USDT, 'BTC/USDT',  true, 0.0001, 2, 6, 0.0025, 0.0050)
-- (kraken,    BTC, USD,  'XBT/USD',   true, 0.0001, 1, 8, 0.0016, 0.0026)
-- (binance,   BTC, USDT, 'BTCUSDT',   true, 0.00001, 2, 5, 0.0010, 0.0010)
-- (cryptocom, CRO, USDT, 'CRO/USDT',  true, 1.0,    6, 2, 0.0025, 0.0050)

-- Daily OHLCV data
CREATE TABLE trading_platform.ohlcv_daily (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),  -- data source venue (coingecko, coinmarketcap, etc.)
    date DATE NOT NULL,
    open NUMERIC(20,8),
    high NUMERIC(20,8),
    low NUMERIC(20,8),
    close NUMERIC(20,8),
    volume NUMERIC(24,2),
    market_cap NUMERIC(24,2),                -- from CoinMarketCap seed data (NULL for exchange sources)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, venue_id, date)
);

-- Daily technical indicators (one row per asset per day — no venue_id)
-- Unlike ohlcv_daily which tracks source venue, daily TA is computed once from the
-- best available source and represents canonical indicator values for that asset.
-- Standard columns for common indicators (typed, indexed, fast)
-- custom JSONB for strategy-specific indicators (no migration needed to add new ones)
CREATE TABLE trading_platform.indicators_daily (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES trading_platform.assets(id),
    date DATE NOT NULL,
    -- Momentum
    rsi_14 NUMERIC(8,4),
    rsi_7 NUMERIC(8,4),                      -- short-term momentum
    stoch_rsi_k NUMERIC(8,4),               -- stochastic RSI %K
    stoch_rsi_d NUMERIC(8,4),               -- stochastic RSI %D
    -- Trend (moving averages)
    ema_9 NUMERIC(20,8),
    ema_12 NUMERIC(20,8),                    -- MACD fast component
    ema_20 NUMERIC(20,8),
    ema_26 NUMERIC(20,8),                    -- MACD slow component
    ema_50 NUMERIC(20,8),
    ema_200 NUMERIC(20,8),
    sma_50 NUMERIC(20,8),
    sma_200 NUMERIC(20,8),
    -- MACD
    macd NUMERIC(20,8),
    macd_signal NUMERIC(20,8),
    macd_hist NUMERIC(20,8),
    -- Volatility
    atr_14 NUMERIC(20,8),
    bb_upper NUMERIC(20,8),
    bb_lower NUMERIC(20,8),
    bb_width NUMERIC(10,6),                  -- bandwidth %
    -- Trend strength
    adx_14 NUMERIC(8,4),
    -- Volume
    obv NUMERIC(24,2),                       -- on-balance volume
    volume_sma_20 NUMERIC(24,2),
    volume_ratio NUMERIC(10,4),              -- current / sma_20
    -- Composite
    regime_score NUMERIC(6,2),
    -- Extensible: strategy-specific indicators (no migration needed)
    custom JSONB DEFAULT '{}',
    -- e.g. {"rsi_30": 62.1, "supertrend": 84500.0, "ichimoku_base": 83200.0}
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, date)
);

-- Price ticks + intraday indicators (see Poller section above)

-- External reference data (from CoinGecko, prefixed ext_)
CREATE TABLE trading_platform.ext_coingecko_assets (
    id SERIAL PRIMARY KEY,
    coingecko_id VARCHAR(128) NOT NULL UNIQUE,
    symbol VARCHAR(32),
    name VARCHAR(128),
    platforms JSONB,                          -- {"ethereum": "0x...", "cronos": "0x..."}
    market_cap_rank INT,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trading_platform.ext_coingecko_platforms (
    id SERIAL PRIMARY KEY,
    platform_id VARCHAR(128) NOT NULL UNIQUE,
    name VARCHAR(128),
    chain_identifier VARCHAR(64),
    native_coin_id VARCHAR(128),
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- Strategy configurations
-- Audit: SCD Type 2 — full version history (must know params at time of each trade)
-- params JSONB is fully flexible per strategy type
CREATE TABLE trading_platform.strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    type VARCHAR(32) NOT NULL,               -- 'momentum', 'dca_grid', 'mean_reversion', etc.
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    params JSONB NOT NULL DEFAULT '{}',      -- strategy-specific (see below)
    is_active BOOLEAN DEFAULT FALSE,
    paper_mode BOOLEAN DEFAULT TRUE,
    -- SCD Type 2
    version INT NOT NULL DEFAULT 1,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMPTZ,                    -- NULL = current version
    is_current BOOLEAN DEFAULT TRUE,
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64),
    UNIQUE (name, version)
);

-- Strategy params JSONB structure:
--
-- All strategies share this top-level structure:
-- {
--   "indicators_required": {        ← which indicators the signal scanner needs
--     "daily": ["rsi_14", "ema_50", "ema_200", "adx_14"],
--     "intraday": ["rsi_14", "ema_9", "ema_21", "vwap"],
--     "custom": ["rsi_30"]          ← reads from custom JSONB column in indicators_*
--   },
--   "entry": { ... },               ← strategy-specific entry rules
--   "exit": { ... },                ← strategy-specific exit rules
--   "position": { ... },            ← position sizing rules
--   "timeframe": { ... }            ← which timeframes to analyze
-- }
--
-- Example: Momentum strategy
-- {
--   "indicators_required": {
--     "daily": ["rsi_14", "ema_50", "ema_200", "adx_14", "regime_score"],
--     "intraday": ["rsi_14", "ema_9", "ema_21", "vwap", "volume_ratio"],
--     "custom": []
--   },
--   "entry": {
--     "rsi_buy_threshold": 30,
--     "rsi_sell_threshold": 70,
--     "ema_fast": 9,
--     "ema_slow": 21,
--     "min_adx": 25,
--     "min_regime_score": 61,
--     "volume_ratio_min": 1.5
--   },
--   "exit": {
--     "take_profit_pct": 8.0,
--     "stop_loss_pct": 5.0,
--     "trailing_stop_atr_mult": 3.0
--   },
--   "position": {
--     "capital_per_trade_pct": 10.0,
--     "max_open_positions": 3,
--     "reserve_capital_pct": 20.0
--   },
--   "timeframe": {
--     "signal_tf": "1h",
--     "trend_tf": "daily",
--     "entry_tf": "1m"
--   }
-- }
--
-- Example: DCA Grid strategy
-- {
--   "indicators_required": {
--     "daily": ["atr_14", "rsi_14", "regime_score"],
--     "intraday": ["rsi_14", "spread_pct"],
--     "custom": []
--   },
--   "grid": {
--     "levels": 5,
--     "spacing_atr_mult": 0.5,
--     "weights": [1, 1, 2, 3, 3],
--     "profit_target_pct": 1.5
--   },
--   "volatility_regimes": {
--     "low": {"atr_mult": 0.4, "profit_target": 1.0},
--     "normal": {"atr_mult": 0.5, "profit_target": 1.5},
--     "high": {"atr_mult": 0.7, "profit_target": 2.5}
--   },
--   "guards": {
--     "circuit_breaker_atr_mult": 2.0,
--     "rsi_overbought_block": 75,
--     "max_capital_pct": 30.0
--   }
-- }
--
-- Example: Strategy using custom indicators
-- {
--   "indicators_required": {
--     "daily": ["rsi_14", "bb_lower", "bb_upper"],
--     "intraday": ["rsi_7", "volume_ratio"],
--     "custom": ["rsi_30", "mfi_14"]       ← read from indicators_*.custom JSONB
--   },
--   "entry": {
--     "rsi_30_oversold": 25,
--     "bb_lower_touch": true,
--     "mfi_14_threshold": 20
--   },
--   ...
-- }
```

### Migration 002: Orders & Executions

```sql
CREATE TABLE trading_platform.orders (
    id BIGSERIAL PRIMARY KEY,
    strategy_id INT REFERENCES trading_platform.strategies(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    account_id INT REFERENCES trading_platform.accounts(id),
    trading_pair_id INT REFERENCES trading_platform.trading_pairs(id),  -- SCD Type 2: references specific version row
    side VARCHAR(4) NOT NULL,                -- 'buy' or 'sell'
    type VARCHAR(16) NOT NULL,               -- 'limit' or 'market'
    quantity NUMERIC(20,8) NOT NULL,
    price NUMERIC(20,8),
    stop_loss NUMERIC(20,8),
    take_profit NUMERIC(20,8),
    status VARCHAR(16) DEFAULT 'open',       -- open, filled, partial, cancelled
    exchange_order_id VARCHAR(64),
    rationale TEXT,
    paper BOOLEAN DEFAULT TRUE,
    -- Audit snapshots (immutable — captured at order creation)
    strategy_version INT,                    -- which strategy version was active
    guardrails_snapshot JSONB,               -- guardrail values at time of order
    pair_snapshot JSONB,                     -- {pair_symbol, maker_fee, taker_fee, precision}
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Order status change audit trail
CREATE TABLE trading_platform.order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES trading_platform.orders(id),
    from_status VARCHAR(16),
    to_status VARCHAR(16) NOT NULL,
    reason TEXT,
    changed_by VARCHAR(64),                  -- 'robin', 'system', 'exchange'
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

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

### Migration 003: Portfolio & Journal

```sql
-- ============================================================
-- Portfolio, P&L & Cost Basis
-- ============================================================

-- Daily portfolio headline (aggregated across all assets/strategies)
CREATE TABLE trading_platform.portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_value_usdt NUMERIC(20,2),          -- cash + positions value
    cash_usdt NUMERIC(20,2),                 -- stablecoins + fiat
    positions_value_usdt NUMERIC(20,2),      -- non-cash asset value
    unrealized_pnl_usdt NUMERIC(20,2),       -- open positions P&L
    realized_pnl_day_usdt NUMERIC(20,2),     -- closed trades P&L today
    total_fees_day_usdt NUMERIC(20,2),       -- fees paid today
    hodl_value_usdt NUMERIC(20,2),           -- benchmark: if just held
    net_deposits_usdt NUMERIC(20,2),         -- cumulative deposits - withdrawals
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date)
);

-- Daily per-asset breakdown
CREATE TABLE trading_platform.portfolio_asset_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    asset_id INT REFERENCES trading_platform.assets(id),
    quantity NUMERIC(20,8),                   -- total holdings
    avg_cost_usdt NUMERIC(20,8),             -- average cost per unit
    market_price_usdt NUMERIC(20,8),         -- current price
    value_usdt NUMERIC(20,2),                -- quantity * market_price
    cost_basis_usdt NUMERIC(20,2),           -- quantity * avg_cost
    unrealized_pnl_usdt NUMERIC(20,2),       -- value - cost_basis
    unrealized_pnl_pct NUMERIC(10,4),        -- % gain/loss
    realized_pnl_day_usdt NUMERIC(20,2),     -- closed trades today for this asset
    hodl_value_usdt NUMERIC(20,2),           -- if just held initial quantity
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, asset_id)
);

-- Daily per-strategy performance
CREATE TABLE trading_platform.portfolio_strategy_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    strategy_id INT REFERENCES trading_platform.strategies(id),
    total_value_usdt NUMERIC(20,2),          -- strategy's current value
    capital_deployed_usdt NUMERIC(20,2),     -- capital allocated
    unrealized_pnl_usdt NUMERIC(20,2),
    realized_pnl_day_usdt NUMERIC(20,2),
    realized_pnl_cumulative_usdt NUMERIC(20,2),
    total_trades INT,
    win_rate NUMERIC(6,4),                   -- wins / total
    avg_trade_pnl_usdt NUMERIC(20,2),
    max_drawdown_pct NUMERIC(10,4),          -- worst peak-to-trough
    sharpe_ratio NUMERIC(10,4),              -- risk-adjusted return
    hodl_comparison_pct NUMERIC(10,4),       -- strategy return vs HODL
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, strategy_id)
);

-- Realized P&L per trade (immutable — created when sell closes position)
CREATE TABLE trading_platform.pnl_realized (
    id BIGSERIAL PRIMARY KEY,
    sell_order_id BIGINT REFERENCES trading_platform.orders(id),
    sell_execution_id BIGINT REFERENCES trading_platform.executions(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    strategy_id INT REFERENCES trading_platform.strategies(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    quantity NUMERIC(20,8) NOT NULL,          -- quantity sold
    cost_basis_usdt NUMERIC(20,2) NOT NULL,  -- what we paid (from cost lots)
    proceeds_usdt NUMERIC(20,2) NOT NULL,    -- what we received
    fees_usdt NUMERIC(20,2) DEFAULT 0,       -- buy + sell fees
    pnl_usdt NUMERIC(20,2) NOT NULL,         -- proceeds - cost_basis - fees
    pnl_pct NUMERIC(10,4),                   -- % return
    hold_duration_hours INT,                 -- how long held
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost basis lots (FIFO — for accurate realized P&L and tax)
CREATE TABLE trading_platform.cost_basis (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES trading_platform.accounts(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    strategy_id INT REFERENCES trading_platform.strategies(id),
    buy_order_id BIGINT REFERENCES trading_platform.orders(id),
    buy_execution_id BIGINT REFERENCES trading_platform.executions(id),
    quantity_original NUMERIC(20,8) NOT NULL, -- original buy quantity
    quantity_remaining NUMERIC(20,8) NOT NULL,-- reduced on sells (FIFO)
    cost_per_unit_usdt NUMERIC(20,8) NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- FIFO ordering is by (account_id, asset_id, acquired_at) — strategy_id is informational
-- (tracks which strategy bought the lot, but FIFO is account-wide per asset)
-- FIFO: on sell, consume oldest lots first
-- Lot 1: 100 CRO @ $0.08, Lot 2: 200 CRO @ $0.09
-- Sell 150 → consume Lot 1 (100), then 50 from Lot 2
-- Lot 1: remaining=0, is_closed=true
-- Lot 2: remaining=150

-- Paper trading balances
CREATE TABLE trading_platform.paper_balances (
    id SERIAL PRIMARY KEY,
    strategy_id INT REFERENCES trading_platform.strategies(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    balance NUMERIC(20,8) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (strategy_id, asset_id)
);

-- Trade journal
CREATE TABLE trading_platform.trade_journal (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES trading_platform.orders(id),
    strategy_id INT REFERENCES trading_platform.strategies(id),
    entry_reason TEXT,
    exit_reason TEXT,
    market_conditions TEXT,                   -- TA snapshot at time of trade
    lessons_learned TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Open positions view — separate paper from live to avoid mixing
CREATE VIEW trading_platform.open_positions AS
SELECT
    o.asset_id, a.symbol, o.venue_id, o.account_id, o.paper,
    SUM(CASE WHEN o.side = 'buy' THEN e.quantity ELSE -e.quantity END) as net_quantity,
    SUM(CASE WHEN o.side = 'buy' THEN e.quantity * e.price ELSE 0 END) /
        NULLIF(SUM(CASE WHEN o.side = 'buy' THEN e.quantity ELSE 0 END), 0) as avg_entry_price,
    SUM(e.fee) as total_fees
FROM trading_platform.orders o
JOIN trading_platform.executions e ON e.order_id = o.id
JOIN trading_platform.assets a ON a.id = o.asset_id
WHERE o.status IN ('filled', 'partial')
GROUP BY o.asset_id, a.symbol, o.venue_id, o.account_id, o.paper
HAVING SUM(CASE WHEN o.side = 'buy' THEN e.quantity ELSE -e.quantity END) > 0;
-- Query: WHERE paper = false for live positions, WHERE paper = true for paper
```

### Migration 004: Accounts, Balances & Transfers

Accounts, balances, ledger, and transfers tables — defined in the "Poller tables" section above.
Tables included:
- `accounts` — sub-accounts per venue
- `balances` — live balance per account per asset
- `balances_ledger` — append-only audit trail
- `transfers` — deposits, withdrawals, internal transfers, bridges
- `total_balances` view — aggregated per asset
- `balance_reconciliation` view — live vs ledger discrepancy

## CLI Tools

All commands output JSON. Agent invokes via `shell("python -m cli.<module> <command> [args]")`.

### `cli/market.py`

```bash
# Reference data setup
python -m cli.market add-asset --symbol BTC --name Bitcoin
python -m cli.market add-venue --code cryptocom --name "Crypto.com" --type exchange --ccxt-id cryptocom
python -m cli.market add-mapping --asset BTC --venue coinmarketcap --external-id 1
python -m cli.market add-network --code ethereum --name "Ethereum Mainnet" --chain-id 1 --native-asset ETH
python -m cli.market add-network-mapping --network ethereum --venue coingecko --external-id ethereum
python -m cli.market add-trading-pair --venue cryptocom --base CRO --quote USDT --pair-symbol "CRO/USDT" \
  --min-order 1.0 --price-precision 6 --qty-precision 2 --maker-fee 0.0025 --taker-fee 0.005
python -m cli.market add-account --venue cryptocom --name main --type spot --default
python -m cli.market add-account --venue metamask --name hot-1 --type wallet \
  --address 0xabc...def --network ethereum

# Data sync & query
python -m cli.market sync-coingecko           # sync ext_coingecko_assets + ext_coingecko_platforms
python -m cli.market fetch-daily              # fetch + store daily OHLCV for all active assets
python -m cli.market compute-daily-ta         # compute + store daily indicators
python -m cli.market overview                 # latest price, TA, regime for all assets (JSON)
python -m cli.market price --symbol CRO       # latest price tick (JSON)
python -m cli.market ta --symbol CRO          # latest intraday + daily TA (JSON)
python -m cli.market history --symbol CRO --days 30  # OHLCV history (JSON)
python -m cli.market poller-status                   # health of all 3 pollers (JSON)
python -m cli.market coverage                        # data coverage per asset (JSON)
```

### `cli/signals.py`

```bash
python -m cli.signals scan                    # check all active strategies for entry/exit signals (JSON)
python -m cli.signals check --symbol CRO      # detailed signal analysis for one asset (JSON)

# Signal scan flow:
# 1. Load active strategies (WHERE is_active=true AND is_current=true)
# 2. For each strategy, read params.indicators_required
# 3. Fetch required indicators from indicators_daily + indicators_intraday
#    - Standard columns: SELECT rsi_14, ema_50 FROM indicators_daily
#    - Custom indicators: SELECT custom->>'rsi_30' FROM indicators_daily
# 4. Run strategy entry/exit logic against indicator values
# 5. Return signals as JSON
```

### `cli/trade.py`

```bash
python -m cli.trade buy --symbol CRO --venue cryptocom --amount 100 --price 0.085 --stop-loss 0.081 --rationale "RSI oversold"
python -m cli.trade sell --symbol CRO --venue cryptocom --quantity 1000 --price 0.092 --rationale "Take profit"
python -m cli.trade cancel --order-id 42
python -m cli.trade list-orders --status open
python -m cli.trade sync-fills               # check if open orders were filled on exchange
```

### `cli/portfolio.py`

```bash
python -m cli.portfolio balance                          # total balance across all venues (JSON)
python -m cli.portfolio balance --venue cryptocom        # balance on specific venue
python -m cli.portfolio balance --account cryptocom:main # balance on specific account
python -m cli.portfolio accounts                         # list all accounts + balances (JSON)
python -m cli.portfolio transfers --days 30               # transfer history (JSON)
python -m cli.portfolio transfers --type deposit          # filter by type
python -m cli.portfolio transfer --type internal --from cryptocom:main --to cryptocom:earn \
  --asset CRO --amount 1000                              # record internal transfer
python -m cli.portfolio transfer --type deposit --to cryptocom:main --asset USDT --amount 1000 \
  --method bank_wire --reference TXN-123                  # record deposit
python -m cli.portfolio transfer --type withdrawal --from cryptocom:main --to-address 0xabc... \
  --asset CRO --amount 500 --network cronos               # record withdrawal
python -m cli.portfolio reconcile-orders --venue cryptocom # compare our orders vs exchange
python -m cli.portfolio reconcile-pnl --days 30           # check P&L vs balance changes
python -m cli.portfolio pnl --period today               # today's P&L (JSON)
python -m cli.portfolio benchmark --days 30              # strategy vs HODL comparison (JSON)
python -m cli.portfolio snapshot                         # take daily snapshot
python -m cli.portfolio history --days 7                 # trade history (JSON)
```

### `cli/strategy.py`

```bash
python -m cli.strategy list                  # all strategies (JSON)
python -m cli.strategy create --name cro_momentum --type momentum --asset CRO --venue cryptocom \
  --params '{"indicators_required":{"daily":["rsi_14","ema_50"],"intraday":["rsi_14","ema_9"]}, ...}'
python -m cli.strategy view --name cro_momentum
python -m cli.strategy history --name cro_momentum  # SCD Type 2 version history
python -m cli.strategy update --name cro_momentum --param entry.rsi_buy=28 --param exit.stop_loss_pct=4.5
python -m cli.strategy activate --name cro_momentum
python -m cli.strategy deactivate --name cro_momentum
python -m cli.strategy set-mode --name cro_momentum --mode live
```

## Guardrails (guardrails.py)

Human-authored, CODEOWNERS protected. All trade commands validate against these:

```python
MAX_POSITION_PCT = 0.10          # Max 10% of portfolio per trade
MAX_DAILY_LOSS_PCT = 0.05        # Stop trading if daily loss > 5%
MAX_OPEN_POSITIONS = 3           # Max 3 concurrent positions
STOP_LOSS_REQUIRED = True        # Every buy must have stop-loss
MAX_STOP_LOSS_PCT = 0.08         # Stop-loss can't be wider than 8%
MIN_TRADE_SIZE_USDT = 5.0        # Minimum trade size
HUMAN_APPROVAL_THRESHOLD = 0.20  # Trades > 20% need human approval
ALLOWED_SYMBOLS = ["CRO/USDT"]   # Only approved pairs
PAPER_MODE_DEFAULT = True         # Default to paper trading
```

## Paper Trading

Paper trading uses the same code path as live — guardrails, order creation, portfolio tracking — but fills are simulated without touching the real exchange.

### How It Works

```
cli/trade.py buy ...
    → guardrails.validate_order()     ← same validation as live
    → strategy.paper_mode == True?
        YES → Paper Engine (no API call)
            → fill at ask price (buy) or bid price (sell) from latest ohlcv_1m
            → deduct simulated fees
            → update paper_balances
            → create order (paper=true) + execution in DB
        NO  → Real Exchange (ccxt API call)
            → real fill, real fees
            → create order (paper=false) + execution in DB
```

### Paper Mode Scope

Per-strategy, not global. Strategies can be mixed:
```
cro_momentum: paper_mode=true    ← testing
btc_dca:      paper_mode=false   ← live
```

### Fill Simulation

| Order Side | Fill Price | Source |
|-----------|-----------|--------|
| Buy | `ask` from latest `ohlcv_1m` | Realistic — you pay the ask |
| Sell | `bid` from latest `ohlcv_1m` | Realistic — you receive the bid |

Simulated fees (configurable per strategy):
- Maker: 0.10%
- Taker: 0.25%

### Paper Balances

Virtual balance per strategy — seeded on strategy creation:

Defined in Migration 003 (see `paper_balances` table — uses `asset_id` FK, not raw string).

Seeded: `INSERT INTO paper_balances (strategy_id, asset_id, balance) VALUES (1, <USDT_id>, 1000);`

### Paper vs Live in CLI

```bash
python -m cli.portfolio balance                        # real balances only
python -m cli.portfolio balance --include-paper        # real + paper
python -m cli.portfolio pnl --strategy cro_momentum    # paper strategy P&L
```

### Switching to Live

```bash
python -m cli.strategy set-mode --name cro_momentum --mode live
```

- Sets `strategies.paper_mode = false`
- Paper orders stay as history (not migrated)
- New orders from this point are real
- Agent can compare: paper P&L vs live P&L after switch

### Implementation

Paper engine lives in `core/exchange.py`:
- `PaperExchange` wraps `CcxtExchange`
- Market data calls (fetch_ticker, fetch_ohlcv) pass through to real exchange
- Order calls (create_order, cancel_order) are simulated locally
- `get_exchange(paper_mode=True)` returns PaperExchange, `False` returns CcxtExchange

## Signal Detection (Hybrid: Rules + Agent Judgment)

Signal detection uses a hybrid approach: a rules engine generates signal candidates, then the agent reviews and makes the final decision.

### Step 1: Rules Engine (`cli/signals.py scan`)

Evaluates each active strategy's conditions mechanically against current indicators:

```bash
python -m cli.signals scan
```

Output:
```json
{
  "signals": [
    {
      "strategy": "cro_momentum",
      "asset": "CRO",
      "venue": "cryptocom",
      "signal": "buy",
      "confidence": 0.82,
      "reasons": [
        "RSI(14) = 28.5 < 30 (oversold)",
        "EMA(9) crossed above EMA(21) (bullish crossover)",
        "ADX(14) = 32 > 25 (strong trend)",
        "volume_ratio = 1.8 > 1.5 (above average)"
      ],
      "failed_conditions": [
        "regime_score = 55 < 61 (weak trend)"
      ],
      "indicators": {
        "rsi_14": 28.5, "ema_9": 0.0842, "ema_21": 0.0838,
        "adx_14": 32, "regime_score": 55, "volume_ratio": 1.8
      },
      "suggested_action": {
        "side": "buy",
        "amount_usdt": 100,
        "price": 0.0845,
        "stop_loss": 0.0803,
        "take_profit": 0.0912
      }
    }
  ],
  "no_signal": [
    {"strategy": "btc_dca_grid", "asset": "BTC", "reason": "No grid levels hit"}
  ]
}
```

**How the scanner works:**
1. Load active strategies (`WHERE is_active=true AND is_current=true`)
2. For each strategy, read `params.indicators_required`
3. Fetch required indicators (standard columns + custom JSONB)
4. Evaluate each entry/exit condition against indicator values
5. Calculate confidence score
6. Output signal candidates with reasons + suggested action

### Step 2: Agent Reviews and Decides

Robin receives scan output and applies judgment — context the rules engine can't see:

```
Robin's reasoning:
- Signal: CRO buy, confidence 0.82
- regime_score only 55 (threshold is 61) — not all conditions met
- Memory: yesterday's research shows Iran conflict escalating → market uncertainty
- Decision: Take smaller position (5% instead of 10%) given partial conditions

shell("python -m cli.trade buy --symbol CRO --venue cryptocom --amount 50
       --price 0.0845 --stop-loss 0.0803
       --rationale 'Partial signal: RSI oversold + EMA cross, but weak regime + geopolitical risk. Halved position.'")
```

**What agent adds beyond rules:**
- News / sentiment context (from research, memory)
- Cross-asset correlation ("BTC is dumping, don't buy alts")
- Portfolio-level risk ("already have 3 positions, skip this one")
- Pattern recognition from past trades (from trade journal)

### Step 3: Auto-Execute Mode (optional, future)

For proven strategies, agent can enable auto-execution:

```json
{
  "params": {
    "auto_execute": true,
    "min_confidence": 0.90,
    "require_all_conditions": true
  }
}
```

If `auto_execute=true` AND confidence >= threshold AND all conditions met → signal scanner executes trade directly, no agent review. Agent still gets notified via Discord.

### Confidence Scoring

```
Base:     conditions_met / total_conditions
Weighted: sum(met * weight) / sum(all weights)
```

Example (momentum, 6 conditions with weights):
```
✅ RSI < 30          (weight 2)  →  2
✅ EMA crossover     (weight 2)  →  2
✅ ADX > 25          (weight 1)  →  1
✅ Volume > 1.5x     (weight 1)  →  1
❌ Regime > 61       (weight 3)  →  0
✅ ATR% < 6          (weight 1)  →  1

Weighted confidence = 7 / 10 = 0.70
```

Weights are stored in strategy params — Robin tunes via CLI:
```bash
python -m cli.strategy update --name cro_momentum \
  --param entry.condition_weights='{"rsi": 2, "ema_cross": 2, "adx": 1, "volume": 1, "regime": 3, "atr": 1}'
```

### Decision Matrix

| Confidence | All Conditions Met? | Agent Action |
|-----------|-------------------|--------------|
| >= 0.90 | Yes | Execute full position (or auto-execute if enabled) |
| 0.70 - 0.89 | Partial | Agent reviews: reduce position, check context, or skip |
| 0.50 - 0.69 | Partial | Agent likely skips, logs for monitoring |
| < 0.50 | No | No signal — scanner doesn't output it |

## Data Seeding & Backfill

TA indicators need history to converge (SMA200 needs 200+ days, EMA200 needs ~200 days to stabilize). Without historical data, signals are unreliable.

### Seed Sources

| Source | Data | Format | Coverage |
|--------|------|--------|----------|
| [CoinMarketCap](https://coinmarketcap.com/currencies/bitcoin/historical-data/) | Daily OHLCV + market cap | CSV download | Full history per asset |
| CoinGecko API | Daily OHLCV | JSON (`/coins/{id}/market_chart?days=max`) | Free tier: ~365 days |
| Exchange API (ccxt) | 1m/1h candles | JSON (`fetch_ohlcv`) | Varies: 30-1000 candles |

### Seed CLI Commands

```bash
# Import historical daily OHLCV from CoinMarketCap CSV
python -m cli.market seed-daily --asset BTC --file data/seeds/btc_daily.csv --venue coinmarketcap

# Import historical daily OHLCV from CoinGecko API (max available)
python -m cli.market seed-daily --asset BTC --venue coingecko --days max

# Batch seed multiple assets
python -m cli.market seed-daily --assets BTC,ETH,CRO,SOL --venue coingecko --days 365

# Backfill daily TA indicators from seeded OHLCV
python -m cli.market backfill-daily-ta --asset BTC
python -m cli.market backfill-daily-ta --all

# Seed 1m candles from exchange (limited history, for intraday TA warmup)
python -m cli.market seed-1m --asset BTC --venue cryptocom --days 7

# Check data coverage
python -m cli.market coverage
# → {"BTC": {"ohlcv_daily": {"from": "2013-04-28", "to": "2026-04-03", "rows": 4724},
#            "indicators_daily": {"from": "2013-12-01", "to": "2026-04-03", "rows": 4524},
#            "ohlcv_1m": {"from": "2026-03-27", "to": "2026-04-03", "rows": 10080}}}
```

### CoinMarketCap CSV Format

Downloaded from `https://coinmarketcap.com/currencies/<asset>/historical-data/`:

```csv
timeOpen,timeClose,timeHigh,timeLow,name,open,high,low,close,volume,marketCap,timestamp
"2026-04-02T00:00:00.000Z","2026-04-02T23:59:59.999Z",...,"Bitcoin",83000.50,84200.00,82100.00,83500.25,28500000000,1650000000000,"2026-04-02T23:59:59.999Z"
```

The seed command resolves to internal IDs then inserts:

```
--asset BTC  → SELECT id FROM assets WHERE symbol='BTC'      → asset_id=1
--venue coinmarketcap → SELECT id FROM venues WHERE code='coinmarketcap' → venue_id=5
```

Maps to `ohlcv_daily`:
- `asset_id` → resolved from `--asset` flag (must exist in `assets` table)
- `venue_id` → resolved from `--venue` flag (must exist in `venues` table)
- `open, high, low, close, volume` → direct mapping from CSV
- Deduplication: `ON CONFLICT (asset_id, venue_id, date) DO NOTHING`

**Prerequisites:** Asset and venue must exist before seeding:
```bash
python -m cli.market add-asset --symbol BTC --name Bitcoin
python -m cli.market add-venue --code coinmarketcap --name CoinMarketCap --type data
python -m cli.market add-mapping --asset BTC --venue coinmarketcap --external-id bitcoin
```

### Seed Data Directory

```
inotagent-trading/
└── data/
    └── seeds/                     # CSV files for historical data (gitignored)
        ├── btc_daily.csv          # downloaded from CoinMarketCap
        ├── eth_daily.csv
        ├── cro_daily.csv
        └── README.md              # instructions for downloading
```

### Backfill Order

1. **Seed assets** — `cli/market.py` add-asset for each asset
2. **Seed venues** — add CoinMarketCap, CoinGecko as data venues
3. **Seed daily OHLCV** — import CSV or fetch from API
4. **Backfill daily TA** — compute indicators from OHLCV history
5. **Start pollers** — begin live 1m data collection
6. **Wait 24h** — 1m data accumulates for intraday TA
7. **Ready to trade** — all indicators converged

### Minimum Data Requirements

| Indicator | Minimum History | Why |
|-----------|----------------|-----|
| RSI(14) | 14 days | 14-period lookback |
| EMA(20) | 40 days | ~2x period to converge |
| EMA(50) | 100 days | ~2x period |
| SMA(200) | 200 days | Exact lookback |
| EMA(200) | 400 days | ~2x period to fully converge |
| MACD(12,26,9) | 60 days | 26 + 9 + buffer |
| ATR(14) | 14 days | 14-period lookback |
| ADX(14) | 28 days | 2x period (smoothed) |
| Regime score | 200 days | Depends on EMA200 |

**Recommendation:** Seed at least 400 days of daily OHLCV for each traded asset.

## Strategy Lifecycle Workflow

The complete journey from idea to live trading:

```
┌─────────────────────────────────────────────────────────────┐
│                   STRATEGY LIFECYCLE                         │
│                                                              │
│  1. RESEARCH                                                 │
│     └─ Agent researches market conditions, patterns          │
│        └─ Uses inotagent research_store (not trading DB)     │
│                                                              │
│  2. DESIGN                                                   │
│     └─ Agent creates strategy with initial params            │
│        └─ cli/strategy.py create --name cro_momentum ...     │
│        └─ Adds indicators_required + entry/exit/position     │
│                                                              │
│  3. BACKTEST                                                 │
│     └─ Test against historical data                          │
│        └─ cli/backtest.py run --strategy cro_momentum ...    │
│        └─ Param sweep to find optimal settings               │
│        └─ Evaluate: Sharpe, drawdown, win rate               │
│        └─ If poor results → back to step 2 (adjust params)  │
│                                                              │
│  4. PAPER TRADE                                              │
│     └─ Run with live data, simulated fills (1-2 weeks)      │
│        └─ cli/strategy.py set-mode --name cro_momentum       │
│           --mode paper                                       │
│        └─ Pollers running, signals scanning every hour       │
│        └─ Compare paper results vs backtest prediction       │
│        └─ If divergence too high → back to step 2            │
│                                                              │
│  5. HUMAN REVIEW                                             │
│     └─ Present: backtest results + paper results             │
│        └─ Human approves → go live                           │
│        └─ Human rejects → back to step 2 or kill strategy   │
│                                                              │
│  6. LIVE TRADE                                               │
│     └─ cli/strategy.py set-mode --name cro_momentum          │
│        --mode live                                           │
│     └─ Real money, real fills, guardrails enforced           │
│     └─ Daily P&L snapshots, Discord reports                  │
│                                                              │
│  7. MONITOR & OPTIMIZE                                       │
│     └─ Weekly review: actual vs backtest vs paper            │
│     └─ If underperforming → pause, re-backtest with new data│
│     └─ If improvement found → Robin recommends, human implements│
│     └─ Cycle continues                                       │
└─────────────────────────────────────────────────────────────┘
```

### Robin's Recurring Tasks

| Task | Schedule | Phase |
|------|----------|-------|
| Start pollers | On boot | Always |
| Scan signals | Hourly | Live/Paper |
| Sync fills | Every 60s (private poller) | Live/Paper |
| Daily OHLCV fetch | daily@02:00 UTC | Always |
| Daily TA compute | daily@02:30 UTC | Always |
| Post-trade analysis | On every sell execution | Live/Paper |
| Daily portfolio snapshot | daily@18:00 SGT | Live/Paper |
| Daily P&L review + Discord report | daily@18:30 SGT | Live/Paper |
| Weekly performance review | weekly@SUN:20:00 SGT | Live/Paper |
| Weekly backtest re-run | weekly@SUN:21:00 SGT | Live |
| Monthly strategy evaluation | monthly@1st:10:00 SGT | Live |

## Strategy Improvement Feedback Loops

Five feedback loops at different time horizons. All triggered by recurring tasks (inotagent heartbeat scheduler), reviewed by agent (LLM reasoning), finalized by human approval.

### Flow: Recurring Task → Agent Review → Human Approval

```
Heartbeat scheduler triggers recurring task
    ↓
Robin picks up task
    ↓
Robin runs CLI commands to gather data (P&L, metrics, backtest)
    ↓
Robin analyzes using LLM reasoning (context from memory, research, trade journal)
    ↓
Robin writes review report → research_store("REVIEW: Weekly Performance ...")
    ↓
If changes recommended:
    ├─ Minor (param tune): Robin submits via cli/strategy.py update (paper mode first)
    │   └─ Posts to Discord: "Adjusted RSI threshold from 30→25 in paper mode. Will evaluate for 1 week."
    │
    ├─ Major (strategy change): Robin posts recommendation to Discord
    │   └─ Posts to Discord: "Recommending new exit logic. Details in research report."
    │   └─ Human implements code change if approved
    │
    └─ Critical (pause/kill): Robin pauses strategy immediately
        └─ Posts to Discord: "⚠️ Strategy paused — 3 consecutive losses, drawdown -15%. Awaiting review."
        └─ Human decides: resume, adjust, or kill
```

### Loop 1: Post-Trade Analysis (per trade)

**Trigger:** Every sell execution detected by private poller
**What Robin does:**
```
1. cli/portfolio.py history --last 1         → get the completed trade
2. Compare: actual exit vs expected exit (stop-loss? take-profit? signal exit?)
3. Check: was entry timing good? (price moved favorably after entry?)
4. Check: was position size appropriate? (too much risk? too conservative?)
5. Write to trade_journal: entry_reason, exit_reason, lessons_learned
6. Store learning in memory: memory_store("Trade CRO: RSI bounce worked but regime was weak...")
```

**Output:** Trade journal entry + memory. No human approval needed.

### Loop 2: Daily P&L Review (daily@18:30 SGT)

**Trigger:** Recurring task `ROB-DAILY-PNL`
**What Robin does:**
```
1. cli/portfolio.py pnl --period today       → today's P&L
2. cli/portfolio.py balance                  → current state
3. cli/trade.py list-orders --status filled --today  → trades today
4. Compare: daily P&L vs expected (based on signals and market move)
5. Check: any anomalies? (unexpected balance changes, failed orders)
6. Write daily report → research_store("REVIEW: Daily P&L 2026-04-03 ...")
7. Post summary to Discord
```

**Output:** Daily report + Discord notification. No human approval unless anomaly detected.

### Loop 3: Weekly Performance Review (weekly@SUN:20:00 SGT)

**Trigger:** Recurring task `ROB-WEEKLY-REVIEW`
**What Robin does:**
```
1. cli/portfolio.py pnl --period week        → weekly P&L
2. cli/portfolio.py benchmark --days 7       → strategy vs HODL
3. Analyze: win rate trend (improving or degrading?)
4. Analyze: drawdown (approaching limits?)
5. Analyze: compare actual vs backtest prediction
6. Check trade journal: any recurring patterns in losses?
7. Write weekly report → research_store("REVIEW: Weekly Performance 2026-W14 ...")
8. Post to Discord with recommendations
```

**If changes recommended:**
```
Robin: "Win rate dropped from 62% to 48% this week. RSI signals firing in weak regime.
       Recommendation: Increase min_regime_score from 55 to 65."

Option A (minor): Robin adjusts param in paper mode first
  → cli/strategy.py update --name cro_momentum --param entry.min_regime_score=65
  → Posts: "Adjusted regime threshold in paper mode. Evaluating for 1 week."
  → After 1 week → compare paper vs live → human approves → apply to live

Option B (needs code change): Robin posts recommendation to Discord
  → "Weekly review flagged consistent RSI false signals in low-regime markets.
     Recommend adding regime filter to signal scanner. Details in research report."
  → Human implements code change if approved

Option C (pause/discuss): Robin posts to Discord and waits
  → "Recommend pausing momentum strategy until regime improves. Approve?"
  → Human responds: "approved" or "keep running with smaller position"
```

**Output:** Weekly report + recommendations. Minor param changes auto-applied to paper mode. Code changes and major decisions need human action.

### Loop 4: Weekly Backtest Re-run (weekly@SUN:21:00 SGT)

**Trigger:** Recurring task `ROB-WEEKLY-BACKTEST`
**What Robin does:**
```
1. Re-run backtest with latest 12 months data (includes last week):
   cli/backtest.py run --strategy cro_momentum --from <12mo_ago> --to today

2. Compare with previous backtest:
   cli/backtest.py compare --id <previous> --id <new>

3. Check for strategy decay:
   - Sharpe ratio declining?
   - Win rate dropping?
   - Drawdown increasing?

4. If decay detected → run param sweep:
   cli/backtest.py sweep --strategy cro_momentum --from <12mo_ago> --to today \
     --sweep entry.rsi_buy_threshold=20,25,30,35

5. Write report → research_store("REVIEW: Backtest Re-evaluation 2026-W14 ...")
```

**If better params found:**
```
Robin: "Backtest re-run shows current params Sharpe 1.42, but RSI=25 yields Sharpe 1.78.
       Recommend: update RSI threshold. Testing in paper mode first."

→ cli/strategy.py update --name cro_momentum --param entry.rsi_buy_threshold=25
  (paper mode, evaluate for 1 week)
→ Posts findings to Discord
→ Human reviews report → approves or rejects
```

**Output:** Backtest comparison report + param recommendations. Applied to paper first, then human approves for live.

### Loop 5: Monthly Strategy Evaluation (monthly@1st:10:00 SGT)

**Trigger:** Recurring task `ROB-MONTHLY-EVAL`
**What Robin does:**
```
1. Full performance review: last 30 days actual trading
   cli/portfolio.py pnl --period month
   cli/portfolio.py benchmark --days 30

2. Full re-backtest: latest 12 months
   cli/backtest.py run --strategy cro_momentum --from <12mo_ago> --to today

3. Comprehensive param sweep (wider range than weekly)
   cli/backtest.py sweep ... (more combinations)

4. Evaluate: should this strategy continue?
   - Positive alpha vs HODL? → Continue
   - Negative alpha for 2+ months? → Consider killing
   - Market regime changed fundamentally? → Redesign

5. Compare all active strategies: which is performing best?

6. Write comprehensive report → research_store("REVIEW: Monthly Strategy Eval April 2026 ...")

7. Post to Discord with clear recommendation:
   "CONTINUE / PAUSE / ADJUST PARAMS / KILL / REDESIGN"
```

**Human approval required for:**
- Killing a strategy
- Switching from paper to live
- Major param overhaul (>3 params changed)
- Creating a new strategy

**Robin can auto-apply (paper mode only):**
- Single param adjustments
- Activating/deactivating a strategy in paper mode
- Position size changes within guardrails

### Anomaly Trigger (immediate)

**Detection:** The private poller runs anomaly checks after each fill sync cycle. It queries:
- `orders WHERE status='filled'` — check for consecutive losses
- `portfolio_snapshots` + `pnl_realized` — check daily loss
- `portfolio_strategy_snapshots` — check drawdown and win rate

When any threshold is breached, the poller writes an anomaly event to `balances_ledger` (type='anomaly') and the signal scanner's next run picks it up. Alternatively, Robin detects anomalies during the hourly signal scan cycle via `cli/signals.py scan` which includes anomaly checks in its output.

**Thresholds:**
- 3 consecutive losing trades
- Daily loss exceeds 3% of portfolio
- Drawdown exceeds 50% of `MAX_DAILY_LOSS_PCT` guardrail
- Strategy win rate drops below 30% over last 10 trades

**What Robin does:**
```
1. Immediately pause the strategy:
   cli/strategy.py deactivate --name cro_momentum

2. Alert on Discord:
   "⚠️ ALERT: cro_momentum paused — 3 consecutive losses.
    Last trades: -2.1%, -1.8%, -3.4%
    Portfolio impact: -$73.00 (-7.3%)
    Awaiting human review before resuming."

3. Run emergency backtest on last 30 days:
   cli/backtest.py run --strategy cro_momentum --from <30d_ago> --to today

4. Write incident report → research_store("ALERT: Strategy Pause — cro_momentum ...")

5. Wait for human:
   - Human: "resume" → Robin reactivates
   - Human: "adjust" → Robin runs param sweep, suggests changes
   - Human: "kill" → Strategy permanently deactivated
```

### Review Report Tags

All reviews stored via inotagent `research_store` with consistent tags:

| Report Type | Title Prefix | Tags |
|------------|-------------|------|
| Post-trade | — | `["trading", "trade-analysis"]` |
| Daily P&L | `REVIEW: Daily P&L YYYY-MM-DD` | `["trading", "daily-review"]` |
| Weekly | `REVIEW: Weekly Performance YYYY-WNN` | `["trading", "weekly-review"]` |
| Backtest re-run | `REVIEW: Backtest Re-eval YYYY-WNN` | `["trading", "backtest"]` |
| Monthly | `REVIEW: Monthly Eval YYYY-MM` | `["trading", "monthly-review"]` |
| Anomaly alert | `ALERT: Strategy Pause — <name>` | `["trading", "alert", "anomaly"]` |

## Backtesting

Replay a strategy against historical data to evaluate performance before paper/live trading. Uses the same strategy code as live — no divergence.

### Architecture

```
Historical data (ohlcv_daily + indicators_daily)
    ↓
Backtester iterates day-by-day
    ↓
For each day:
    ├─ Load indicators for that date
    ├─ Run strategy.evaluate_signal(indicators)  ← SAME code as live signals.py
    ├─ If signal → simulate fill (close price + slippage + fees)
    ├─ Track positions, cost basis (FIFO), P&L
    └─ Record to backtest results
    ↓
Output: metrics + trade log + equity curve
```

**Key principle:** `strategies/momentum.py` has `evaluate_signal(indicators) → Signal` used by:
- `cli/signals.py scan` — live: reads latest indicators from DB
- `cli/backtest.py run` — historical: iterates past indicators day by day

Same logic, different data source.

### CLI Commands

```bash
# Run backtest for a strategy over date range
python -m cli.backtest run --strategy cro_momentum --from 2025-01-01 --to 2026-03-31
# → JSON: metrics summary + trade log

# Run with param override (test different settings without modifying strategy)
python -m cli.backtest run --strategy cro_momentum --from 2025-01-01 --to 2026-03-31 \
  --override entry.rsi_buy_threshold=25 --override exit.stop_loss_pct=3.0

# Compare multiple param sets (grid search)
python -m cli.backtest sweep --strategy cro_momentum --from 2025-01-01 --to 2026-03-31 \
  --sweep entry.rsi_buy_threshold=20,25,30,35 \
  --sweep exit.stop_loss_pct=3,4,5,6
# → JSON: comparison table of all param combinations

# List saved backtest results
python -m cli.backtest list --strategy cro_momentum

# View a specific backtest result
python -m cli.backtest view --id 42

# Compare backtest vs actual performance
python -m cli.backtest compare --id 42 --actual-from 2026-04-01 --actual-to 2026-04-30
```

### Backtest Tables

```sql
-- Backtest run metadata
CREATE TABLE trading_platform.backtest_runs (
    id BIGSERIAL PRIMARY KEY,
    sweep_id UUID,                           -- groups runs from same param sweep (NULL for single runs)
    strategy_name VARCHAR(64) NOT NULL,
    strategy_type VARCHAR(32) NOT NULL,
    strategy_params JSONB NOT NULL,          -- full params snapshot (including overrides)
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    -- Date range
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    -- Config
    initial_capital_usdt NUMERIC(20,2) NOT NULL,
    slippage_pct NUMERIC(6,4) DEFAULT 0.10,  -- simulated slippage
    maker_fee NUMERIC(6,4),
    taker_fee NUMERIC(6,4),
    -- Results (summary metrics)
    total_return_pct NUMERIC(10,4),
    total_return_usdt NUMERIC(20,2),
    hodl_return_pct NUMERIC(10,4),           -- benchmark: just hold the asset
    alpha_pct NUMERIC(10,4),                 -- strategy return - hodl return
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate NUMERIC(6,4),
    avg_win_pct NUMERIC(10,4),
    avg_loss_pct NUMERIC(10,4),
    profit_factor NUMERIC(10,4),             -- gross profit / gross loss
    max_drawdown_pct NUMERIC(10,4),
    max_drawdown_duration_days INT,
    sharpe_ratio NUMERIC(10,4),
    sortino_ratio NUMERIC(10,4),             -- downside risk only
    calmar_ratio NUMERIC(10,4),              -- return / max drawdown
    avg_hold_duration_hours NUMERIC(10,2),
    -- Metadata
    run_duration_ms INT,                     -- how long the backtest took
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64)
);

-- Backtest trade log (every simulated trade)
CREATE TABLE trading_platform.backtest_trades (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES trading_platform.backtest_runs(id) ON DELETE CASCADE,
    trade_num INT NOT NULL,                  -- sequential trade number
    -- Entry
    entry_date DATE NOT NULL,
    entry_price NUMERIC(20,8) NOT NULL,
    entry_signal_confidence NUMERIC(6,4),
    entry_reasons JSONB,                     -- ["RSI oversold", "EMA cross"]
    -- Exit
    exit_date DATE,
    exit_price NUMERIC(20,8),
    exit_reason VARCHAR(32),                 -- 'take_profit', 'stop_loss', 'signal_exit', 'end_of_period'
    -- Position
    side VARCHAR(4) NOT NULL,                -- 'buy' or 'sell'
    quantity NUMERIC(20,8) NOT NULL,
    cost_basis_usdt NUMERIC(20,2),
    proceeds_usdt NUMERIC(20,2),
    fees_usdt NUMERIC(20,2),
    slippage_usdt NUMERIC(20,2),
    -- P&L
    pnl_usdt NUMERIC(20,2),
    pnl_pct NUMERIC(10,4),
    hold_duration_days INT,
    -- Portfolio state at this point
    portfolio_value_usdt NUMERIC(20,2),
    drawdown_pct NUMERIC(10,4),              -- from peak at this point
    UNIQUE (run_id, trade_num)
);

-- Backtest equity curve (daily portfolio value for charting)
CREATE TABLE trading_platform.backtest_equity (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES trading_platform.backtest_runs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    portfolio_value_usdt NUMERIC(20,2),
    cash_usdt NUMERIC(20,2),
    positions_value_usdt NUMERIC(20,2),
    hodl_value_usdt NUMERIC(20,2),           -- benchmark comparison
    drawdown_pct NUMERIC(10,4),
    UNIQUE (run_id, date)
);
```

### Example Backtest Run

```bash
python -m cli.backtest run --strategy cro_momentum --from 2025-04-01 --to 2026-03-31 \
  --capital 1000 --slippage 0.1
```

Output:
```json
{
  "run_id": 42,
  "strategy": "cro_momentum",
  "period": "2025-04-01 to 2026-03-31 (365 days)",
  "initial_capital": 1000.00,

  "performance": {
    "total_return_pct": 34.5,
    "total_return_usdt": 345.00,
    "hodl_return_pct": 12.3,
    "alpha_pct": 22.2,
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.41,
    "calmar_ratio": 1.72,
    "max_drawdown_pct": -20.1,
    "max_drawdown_duration_days": 18,
    "profit_factor": 2.3
  },

  "trades": {
    "total": 47,
    "winning": 29,
    "losing": 18,
    "win_rate": 0.617,
    "avg_win_pct": 5.2,
    "avg_loss_pct": -3.1,
    "avg_hold_duration_hours": 72
  },

  "best_trade": {
    "entry": "2025-07-14 @ $0.065",
    "exit": "2025-07-28 @ $0.089",
    "pnl_pct": 36.9,
    "reason": "RSI bounce from 22 + strong EMA cross"
  },

  "worst_trade": {
    "entry": "2025-11-02 @ $0.112",
    "exit": "2025-11-03 @ $0.098",
    "pnl_pct": -12.5,
    "reason": "Stop-loss hit — flash crash"
  },

  "monthly_returns": {
    "2025-04": 4.2, "2025-05": -1.8, "2025-06": 7.1,
    "2025-07": 12.3, "2025-08": -3.4, "2025-09": 2.1,
    "2025-10": 5.5, "2025-11": -8.2, "2025-12": 6.8,
    "2026-01": 3.9, "2026-02": 1.4, "2026-03": 4.6
  }
}
```

### Param Sweep Example

```bash
python -m cli.backtest sweep --strategy cro_momentum --from 2025-04-01 --to 2026-03-31 \
  --sweep entry.rsi_buy_threshold=20,25,30,35 \
  --sweep exit.stop_loss_pct=3,4,5,6
```

Output (16 combinations):
```json
{
  "sweep_results": [
    {"rsi": 20, "stop": 3, "return_pct": 28.1, "drawdown": -25.3, "sharpe": 1.42, "trades": 62},
    {"rsi": 20, "stop": 4, "return_pct": 31.2, "drawdown": -22.1, "sharpe": 1.58, "trades": 62},
    {"rsi": 25, "stop": 4, "return_pct": 34.5, "drawdown": -20.1, "sharpe": 1.85, "trades": 47},
    {"rsi": 25, "stop": 5, "return_pct": 32.8, "drawdown": -18.4, "sharpe": 1.79, "trades": 47},
    {"rsi": 30, "stop": 5, "return_pct": 29.3, "drawdown": -15.2, "sharpe": 1.91, "trades": 35},
    "..."
  ],
  "best_return": {"rsi": 25, "stop": 4, "return_pct": 34.5},
  "best_sharpe": {"rsi": 30, "stop": 5, "sharpe": 1.91},
  "best_drawdown": {"rsi": 35, "stop": 3, "drawdown": -10.8}
}
```

**Robin's workflow after sweep:**
```
Robin: "RSI=25, stop=4% has best absolute return but RSI=30, stop=5% has best risk-adjusted (Sharpe 1.91).
       Going with RSI=30, stop=5% — prioritize risk management over raw return."

shell("python -m cli.strategy update --name cro_momentum --param entry.rsi_buy_threshold=30 --param exit.stop_loss_pct=5.0")
```

### Fill Simulation in Backtest

| Aspect | Backtest | Paper Trading | Live |
|--------|----------|---------------|------|
| Data source | Historical (DB) | Live (exchange) | Live (exchange) |
| Fill price | Close of signal candle | Bid/ask from ohlcv_1m | Actual exchange fill |
| Slippage | Configurable (default 0.1%) | Real spread | Real spread |
| Fees | From strategy config or trading_pairs | From trading_pairs | Actual exchange fees |
| Fill timing | Instant (next candle open) | 60s poller cycle | Exchange latency |

**Backtest fill logic:**
```
Signal on Day N (using Day N close indicators):
  → Entry price = Day N+1 open * (1 + slippage_pct)  (buy: pay more, sell: receive less)
  → Fees deducted from proceeds
  → Stop-loss/take-profit checked against Day N+1 high/low
```

### Backtest vs Actual Comparison

After paper/live trading, compare against the backtest prediction:

```bash
python -m cli.backtest compare --id 42 --actual-from 2026-04-01 --actual-to 2026-04-30
```

```json
{
  "backtest": {
    "period": "same params, historical data",
    "return_pct": 4.6,
    "trades": 5,
    "win_rate": 0.60
  },
  "actual": {
    "period": "2026-04-01 to 2026-04-30",
    "return_pct": 3.2,
    "trades": 4,
    "win_rate": 0.50
  },
  "divergence": {
    "return_gap": -1.4,
    "trade_count_gap": -1,
    "notes": "Actual underperformed by 1.4% — likely due to higher real slippage and missed signals during poller downtime"
  }
}
```

### Backtest Guardrails

- **No lookahead bias**: signals evaluated using only data available up to that date
- **No survivorship bias**: if an asset was delisted during the period, it's included
- **Slippage is mandatory**: default 0.1%, prevents unrealistic fills
- **Fees are mandatory**: uses trading_pairs fee rates (or `--maker-fee`/`--taker-fee` overrides)
- **Fill at next candle open**: not at signal candle close (realistic execution delay)
- **Max 1 entry per signal**: no pyramiding unless strategy explicitly allows
- **Results are saved**: every run stored in `backtest_runs` for comparison
- **Guardrails enforced**: backtester applies `guardrails.py` rules (position limits, max positions, stop-loss required). This ensures backtest results are achievable with the same safety constraints as live trading
- **Stop-loss checked intraday**: on each candle, check if high/low breached stop-loss before evaluating signals

## Stop-Loss Execution

Stop-loss is mandatory on every buy order (enforced by guardrails). Three approaches by venue capability:

| Venue Supports | Method | How |
|---------------|--------|-----|
| OCO orders | Exchange-side | Place OCO (One-Cancels-Other) with take-profit + stop-loss at order time. Exchange auto-executes. |
| Stop-limit orders | Exchange-side | Place separate stop-limit order. Exchange monitors and triggers. |
| Neither | Poller-monitored | `poller.private` checks price vs stop-loss every 60s. If triggered, CLI places market sell. |

**Default flow:**
1. Agent places buy → `cli/trade.py` records `stop_loss` on order
2. If exchange supports stop-limit → place exchange-side stop order → record as linked order
3. If not → `poller.private` monitors: `latest_price <= order.stop_loss` → auto-trigger sell
4. Stop-loss trigger creates: sell order (created_by='system', rationale='stop-loss triggered')

**Paper mode stop-loss:** Since paper orders don't go to an exchange, all paper stop-losses are poller-monitored. The TA poller (not private poller — no auth needed) checks latest `ohlcv_1m.low` against open paper orders' `stop_loss`. If triggered, paper engine simulates fill at the stop-loss price.

**Risk:** Poller-monitored stop-loss has 60s latency. In fast-moving markets, actual exit price may differ from stop-loss level. Exchange-side stops are preferred.

## Record Keeping & Reconciliation

### Who Records What

Two sources create records — the CLI (agent-initiated) and the private poller (exchange-detected):

| Action | Recorder | How |
|--------|----------|-----|
| Robin places order | `cli/trade.py` | Direct INSERT into orders + order_events |
| Order gets filled | `poller.private` | Detects fill → INSERT execution + UPDATE order status |
| Stop-loss triggered by exchange | `poller.private` | Detects new order + fill → INSERT orders + executions |
| Manual trade on exchange website | `poller.private` | Detects unknown order → INSERT (created_by='exchange') |
| Deposit / withdrawal | `poller.private` | Detects balance change → INSERT balances_ledger + transfers |
| Internal transfer | `cli/portfolio.py` or `poller.private` | Agent-initiated or detected |
| Staking reward | `poller.private` | Detects balance increase → INSERT balances_ledger (type='reward') |
| Paper trade | `cli/trade.py` | Paper engine fills instantly, records all tables |
| Cost basis lot created | `cli/trade.py` | On buy execution → INSERT cost_basis |
| Cost basis lot consumed | `cli/trade.py` | On sell execution → UPDATE cost_basis (FIFO), INSERT pnl_realized |
| Daily snapshots | `cli/portfolio.py snapshot` | Recurring task → INSERT portfolio_*_snapshots |

### Agent-Initiated Flow (cli/trade.py)

```
Robin: python -m cli.trade buy --symbol CRO --venue cryptocom --amount 100 ...
  │
  ├─ guardrails.validate_order()
  ├─ INSERT orders (status='open', exchange_order_id=NULL)
  ├─ exchange.create_order() via ccxt → returns exchange_order_id
  ├─ UPDATE orders SET exchange_order_id='EX-123'
  └─ INSERT order_events (NULL → open)

Later, poller.private detects fill:
  │
  ├─ ccxt.fetch_orders() → EX-123 status=filled
  ├─ CHECK: orders WHERE exchange_order_id='EX-123' → EXISTS, status='open'
  ├─ UPDATE orders SET status='filled'
  ├─ INSERT executions (qty, price, fee)
  ├─ INSERT order_events (open → filled)
  ├─ INSERT balances_ledger entries (debit USDT, credit CRO, debit fee)
  ├─ If buy: INSERT cost_basis lot (created only after confirmed fill)
  └─ If sell: consume cost_basis lots (FIFO) → INSERT pnl_realized
```

### Exchange-Detected Flow (poller.private)

For orders created outside our system (manual trades, exchange auto-actions):

```
poller.private sync cycle:
  │
  ├─ ccxt.fetch_orders(since=last_sync)
  ├─ For each order from exchange:
  │   ├─ CHECK: orders WHERE exchange_order_id='EX-456' → NOT FOUND
  │   ├─ INSERT orders (created_by='exchange', status from exchange)
  │   ├─ INSERT order_events (reason='detected by poller — external trade')
  │   ├─ INSERT executions (if already filled)
  │   ├─ INSERT balances_ledger entries
  │   └─ Flag for agent review (unknown trade detected)
  │
  ├─ ccxt.fetch_balance()
  │   ├─ Compare with balances table
  │   ├─ If discrepancy and no matching order/transfer:
  │   │   INSERT balances_ledger (type='external', notes='unmatched balance change')
  │   └─ UPDATE balances table
  │
  └─ Log: "Detected X external orders, Y unmatched balance changes"
```

### Deduplication

The `exchange_order_id` is the deduplication key between CLI and poller:

| Scenario | CLI | Poller | Result |
|----------|-----|--------|--------|
| Robin places order | INSERT (exchange_order_id=EX-123) | Finds EX-123 → already exists → only sync fill status | No duplicate |
| Exchange auto-order | — | Finds EX-456 → not in DB → INSERT as external | New record |
| Robin places, fill detected | INSERT as open | UPDATE to filled + INSERT execution | Correct lifecycle |

### Reconciliation

Three levels of reconciliation:

**1. Balance reconciliation** (live vs ledger):
```sql
SELECT * FROM trading_platform.balance_reconciliation;
-- Shows: asset, live_balance, ledger_balance, discrepancy
```

**2. Order reconciliation** (our orders vs exchange):
```bash
python -m cli.portfolio reconcile-orders --venue cryptocom
# Compares our orders table with ccxt.fetch_orders()
# Flags: missing locally, missing on exchange, status mismatch
```

**3. P&L reconciliation** (realized P&L vs actual balance change):
```bash
python -m cli.portfolio reconcile-pnl --days 30
# Compares: starting_balance + deposits - withdrawals + realized_pnl = current_balance?
# Flags any unexplained differences
```

## Robin's Access Model

Robin does **not** modify code. All code changes are human-authored. Robin's interaction is purely CLI → DB:

| What Robin Does | How | Code Change? |
|-----------------|-----|-------------|
| Read market data | `cli/market.py overview`, `price`, `ta` | No |
| Scan signals | `cli/signals.py scan` | No |
| Place/cancel orders | `cli/trade.py buy`, `sell`, `cancel` | No |
| Tune strategy params | `cli/strategy.py update --param ...` | No (DB only) |
| Activate/deactivate strategy | `cli/strategy.py activate/deactivate` | No (DB only) |
| Switch paper → live | `cli/strategy.py set-mode --mode live` | No (DB only) |
| Run backtest | `cli/backtest.py run`, `sweep` | No |
| Check portfolio | `cli/portfolio.py balance`, `pnl` | No |
| Record transfer | `cli/portfolio.py transfer` | No |

**All code is human-authored:**

| Area | Modified By |
|------|------------|
| `strategies/*.py` | Human (direct commit) |
| `core/*.py` | Human (CODEOWNERS protected) |
| `cli/*.py` | Human |
| `poller/*.py` | Human |
| `guardrails.py` | Human (CODEOWNERS protected) |
| `db/migrations/` | Human (CODEOWNERS protected) |

## Robin's Trading Workflow

All CLI calls use `shell("cd /opt/inotagent-trading && python -m cli.<module> <command>")`.

```
Every 1 min (poller containers — run automatically):
  → fetch ticker, 1m candles → compute intraday TA → store to DB

Every hour (recurring task ROB-010):
  1. cli.market ta --symbol CRO                    # get latest TA
  2. cli.signals scan                              # check for signals
  3. If signal detected:
     a. cli.portfolio balance                      # check capital
     b. cli.trade buy --symbol CRO ...             # execute (guardrails validate)
     c. Store rationale in memory, report to Discord
  4. cli.trade sync-fills                          # check fills

Every day (recurring task ROB-012):
  1. cli.market fetch-daily                        # fetch daily OHLCV
  2. cli.market compute-daily-ta                   # compute daily indicators
  3. cli.portfolio snapshot                        # daily portfolio snapshot
  4. cli.portfolio pnl --period today              # report P&L to Discord

Weekly (recurring task ROB-013):
  1. cli.portfolio benchmark --days 7              # strategy vs HODL
  2. Review performance, adjust params if needed (via cli.strategy update)
  3. If strategy underperforming → report to Discord, recommend param changes or pause
```

## Deployment

Since inotagent-trading lives in the monorepo, pollers run as Docker services alongside the agents. The CLI toolkit is made available to Robin via volume mount (development) or baked into the image (production).

### How Robin accesses the toolkit

**Development: Volume mount** — mount `inotagent-trading/` into Robin's container. Deps installed at startup via entrypoint script. Live code updates without image rebuild.

**Production: Baked into image** — copy `inotagent-trading/` into the agent image at build time, pre-install deps. Immutable, no startup delay. `.env` mounted at runtime (secrets never baked into image).

```dockerfile
# inotagent Dockerfile — add trading toolkit (code only, no .env)
COPY inotagent-trading/ /opt/inotagent-trading/
RUN cd /opt/inotagent-trading && uv sync --no-dev
```

```yaml
# docker-compose.yml
robin:
  volumes:
    # Development: mount code for live editing (overrides baked-in copy)
    - ./inotagent-trading:/opt/inotagent-trading
    # Production: only mount .env (code is baked in)
    # - ./inotagent-trading/.env:/opt/inotagent-trading/.env:ro
```

Robin invokes via shell tool (same path in both modes):
```bash
shell("cd /opt/inotagent-trading && python -m cli.market overview")
shell("cd /opt/inotagent-trading && python -m cli.signals scan")
shell("cd /opt/inotagent-trading && python -m cli.trade buy --symbol CRO ...")
shell("cd /opt/inotagent-trading && python -m cli.strategy update --param entry.rsi_buy=25")
```

### Environment files — separation of concerns

Three `.env` files, each with its own scope:

| File | Scope | Used By | Contains |
|------|-------|---------|----------|
| `agents/robin/.env` | Agent identity | Robin's agent process | LLM API keys, Discord token, channels, agent name |
| `agents/ino/.env` | Agent identity | Ino's agent process | LLM API keys, Discord token, channels, agent name |
| `inotagent-trading/.env` | Trading toolkit | Pollers + Robin's CLI calls | Exchange API keys, DB, poller config, trading schema |

**Robin's CLI** picks up `inotagent-trading/.env` automatically — pydantic-settings loads `.env` from CWD, and Robin always `cd /opt/inotagent-trading` before running CLI commands.

**Pollers** read `inotagent-trading/.env` via Docker Compose `env_file`.

**Ino** never touches `inotagent-trading/.env` — no overlap, no leakage.

### Poller Docker Compose services

Pollers run as separate containers (own Dockerfile in `inotagent-trading/`):

```yaml
  poller-public:
    build:
      context: ./inotagent-trading
    command: python -m poller.public
    env_file: ./inotagent-trading/.env
    networks: [platform]
    restart: unless-stopped
    mem_limit: 256m

  poller-private:
    build:
      context: ./inotagent-trading
    command: python -m poller.private
    env_file: ./inotagent-trading/.env
    networks: [platform]
    restart: unless-stopped
    mem_limit: 256m

  poller-ta:
    build:
      context: ./inotagent-trading
    command: python -m poller.ta
    env_file: ./inotagent-trading/.env
    networks: [platform]
    restart: unless-stopped
    mem_limit: 256m
```

### Makefile targets (added to root Makefile)

```bash
make trading-start           # start all 3 pollers
make trading-stop            # stop all pollers
make trading-status          # check poller health
make trading-logs            # tail poller logs
make trading-migrate         # run inotagent-trading/db/migrations/ (001-005)
make trading-seed            # seed assets, venues, mappings, historical OHLCV
make trading-build           # build trading toolkit Docker image
```

### Local development (without Docker)

```bash
cd inotagent-trading
uv sync
cp .env.template .env  # edit with credentials

# Migrate trading schema
make trading-migrate  # runs inotagent-trading/db/migrations/

# Start pollers locally
python -m poller.public &
python -m poller.private &
python -m poller.ta &

# Agent uses CLI tools
python -m cli.market overview
python -m cli.signals scan
```

## Configuration

### `inotagent-trading/.env` — trading toolkit config

Used by pollers (via `env_file`) and Robin's CLI (via pydantic-settings CWD loading). Gitignored. Created from `.env.template`.

```env
# Database (same Postgres instance as openvaia, different schema)
POSTGRES_HOST=localhost
POSTGRES_PORT=5445
POSTGRES_USER=inotives
POSTGRES_PASSWORD=<password>
POSTGRES_DB=inotives
TRADING_SCHEMA=trading_platform

# Exchange credentials (only needed by private poller + cli/trade.py)
CRYPTOCOM_API_KEY=<key>
CRYPTOCOM_API_SECRET=<secret>
TRADING_MODE=paper                # paper | live

# Public data poller
PUBLIC_POLLER_INTERVAL=60         # seconds
PUBLIC_POLLER_PAIRS=CRO/USDT,BTC/USDT

# Private data poller
PRIVATE_POLLER_INTERVAL=60        # seconds
PRIVATE_POLLER_EXCHANGE=cryptocom

# TA compute poller
TA_POLLER_INTERVAL=60             # seconds
TA_DAILY_HOUR=2                   # UTC hour to compute daily TA

# Archival
ARCHIVE_DIR=./archive             # parquet archive location
OHLCV_1M_RETENTION_DAYS=30
```

### `agents/robin/.env` — Robin agent config (unchanged)

Robin's agent process uses this for LLM, Discord, and platform config. **No trading vars here** — the CLI gets them from `inotagent-trading/.env` via CWD.

### `agents/ino/.env` — Ino agent config (unchanged)

Ino has no trading config. Even though the toolkit code exists at `/opt/inotagent-trading` in the shared image, Ino has no trading skills and no `inotagent-trading/.env` mounted — so the CLI would fail gracefully if ever called.

## Database Indexes

Beyond the UNIQUE constraints (which create indexes), these indexes are needed for query performance:

```sql
-- ohlcv_1m: poller inserts + TA queries
CREATE INDEX idx_ohlcv_1m_asset_ts ON trading_platform.ohlcv_1m(asset_id, timestamp);
CREATE INDEX idx_ohlcv_1m_venue_asset_ts ON trading_platform.ohlcv_1m(venue_id, asset_id, timestamp DESC);

-- ohlcv_daily: TA backfill + history queries
CREATE INDEX idx_ohlcv_daily_asset_date ON trading_platform.ohlcv_daily(asset_id, date DESC);

-- indicators: signal scanner queries
CREATE INDEX idx_indicators_daily_asset_date ON trading_platform.indicators_daily(asset_id, date DESC);
CREATE INDEX idx_indicators_intraday_asset_ts ON trading_platform.indicators_intraday(asset_id, venue_id, timestamp DESC);

-- orders: fill sync + portfolio queries
CREATE INDEX idx_orders_status ON trading_platform.orders(status) WHERE status IN ('open', 'partial');
CREATE INDEX idx_orders_exchange_id ON trading_platform.orders(exchange_order_id) WHERE exchange_order_id IS NOT NULL;
CREATE INDEX idx_orders_strategy ON trading_platform.orders(strategy_id, created_at DESC);
CREATE INDEX idx_orders_asset_venue ON trading_platform.orders(asset_id, venue_id, created_at DESC);

-- executions: P&L computation
CREATE INDEX idx_executions_order ON trading_platform.executions(order_id);

-- cost_basis: FIFO lot consumption
CREATE INDEX idx_cost_basis_fifo ON trading_platform.cost_basis(account_id, asset_id, acquired_at)
    WHERE is_closed = false;

-- strategies: active strategy lookup
CREATE INDEX idx_strategies_active ON trading_platform.strategies(name)
    WHERE is_active = true AND is_current = true;

-- balances_ledger: reconciliation
CREATE INDEX idx_ledger_account_asset ON trading_platform.balances_ledger(account_id, asset_id, created_at);

-- backtest: sweep grouping
CREATE INDEX idx_backtest_sweep ON trading_platform.backtest_runs(sweep_id) WHERE sweep_id IS NOT NULL;
```

## Implementation Phases

- [ ] Phase 1: Create `inotagent-trading/` subfolder + `pyproject.toml` + `Dockerfile` + `.dockerignore`
- [ ] Phase 1: Write `core/config.py`, `core/db.py`, `core/models.py`
- [ ] Phase 1: Write DB migrations in `inotagent-trading/db/migrations/` (001-005)
- [ ] Phase 1: Write `guardrails.py` + `tests/test_guardrails.py`
- [ ] Phase 1: Update `.github/CODEOWNERS` with protected paths
- [ ] Phase 2: Write `core/exchange.py` (ccxt wrapper with paper mode) + `tests/test_exchange.py`
- [ ] Phase 2: Write `core/indicators.py` (pandas-ta daily + intraday) + `tests/test_indicators.py`
- [ ] Phase 3: Write public poller (`poller/public/` — OHLCV 1m + ticker)
- [ ] Phase 3: Write private poller (`poller/private/` — balances + orders + fills + anomaly checks)
- [ ] Phase 3: Write TA poller (`poller/ta/` — aggregate + intraday + daily TA + paper stop-loss monitoring)
- [ ] Phase 3: Add error handling/retry + health heartbeat to all pollers
- [ ] Phase 3: Add Docker Compose services (poller-public, poller-private, poller-ta) + Makefile targets
- [ ] Phase 3: Add ohlcv_1m archival to parquet + pruning
- [ ] Phase 3: Test pollers — verify data flows, TA computed, balances synced
- [ ] Phase 4: Write `cli/market.py` (setup commands: add-asset, add-venue, add-mapping, add-network, add-account, add-trading-pair + data commands)
- [ ] Phase 4: Write `cli/signals.py` (scan with anomaly checks + confidence scoring)
- [ ] Phase 4: Write `cli/trade.py` (with guardrail validation) + `tests/test_cost_basis.py`
- [ ] Phase 4: Write `cli/portfolio.py` (balance, pnl, transfers, reconciliation commands)
- [ ] Phase 4: Write `cli/strategy.py` (create, list, view, history, update, activate, deactivate, set-mode)
- [ ] Phase 5: Write `cli/backtest.py` (run, sweep, list, view, compare) + `tests/test_backtest.py`
- [ ] Phase 5: Write `strategies/base.py` + `strategies/momentum.py` (initial strategy)
- [ ] Phase 5: Seed initial data: assets, venues, mappings, historical OHLCV, backfill TA
- [ ] Phase 5: Bake toolkit into agent Docker image + volume mount for dev (update inotagent Dockerfile + docker-compose.yml)
- [ ] Phase 5: Create trading skills for Robin
- [ ] Phase 6: Paper trading for 1-2 weeks
- [ ] Phase 6: Human review results → switch to live

## Safety & Risk

| Guardrail | Level | Details |
|-----------|-------|---------|
| Position size limit | Code | Max 10% per trade |
| Daily loss limit | Code | Max 5%, auto-stop |
| Stop-loss mandatory | Code | Every buy must have stop-loss |
| Max open positions | Code | Max 3 concurrent |
| Human approval | Code | Trades > 20% need approval |
| Allowed symbols | Code | Only approved pairs |
| Paper mode default | Code | New strategies start paper |
| Code changes | Human | All code is human-authored (CODEOWNERS enforced) |
| Protected guardrails | Git | CODEOWNERS on guardrails.py |
| Trade journal | DB | Every trade logged with rationale |
| Discord reporting | Skill | Every trade reported |
| Weekly review | Task | Mandatory performance review |

**Risk acknowledgment:** This is real money (1000 CRO). LLM trading is experimental. Guardrails prevent catastrophic loss but not gradual losses.

## Dependencies

- Python 3.12, uv
- ccxt, pandas, pandas-ta, requests, asyncpg, psycopg, pydantic-settings
- Shared Postgres (`inotives` DB, `trading_platform` schema — own migrations in `db/migrations/`)
- crypto.com Exchange API access
- ES-0009 (proactive behavior) for recurring task execution
- ES-0014 (dynamic skill equipping) for trading skill chains

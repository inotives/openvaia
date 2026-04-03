-- migrate:up

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
    deleted_by VARCHAR(64)
);

CREATE UNIQUE INDEX idx_asset_mappings_unique
    ON trading_platform.asset_mappings (asset_id, venue_id, COALESCE(network_id, 0));

-- Trading pairs per venue -- fees, precision can change over time
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

-- ohlcv_1m indexes
CREATE INDEX idx_ohlcv_1m_asset_ts ON trading_platform.ohlcv_1m(asset_id, timestamp);
CREATE INDEX idx_ohlcv_1m_venue_asset_ts ON trading_platform.ohlcv_1m(venue_id, asset_id, timestamp DESC);

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

-- ohlcv_daily indexes
CREATE INDEX idx_ohlcv_daily_asset_date ON trading_platform.ohlcv_daily(asset_id, date DESC);

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

-- indicators_intraday indexes
CREATE INDEX idx_indicators_intraday_asset_ts ON trading_platform.indicators_intraday(asset_id, venue_id, timestamp DESC);

-- Daily technical indicators (one row per asset per day -- no venue_id)
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (asset_id, date)
);

-- indicators_daily indexes
CREATE INDEX idx_indicators_daily_asset_date ON trading_platform.indicators_daily(asset_id, date DESC);

-- Aggregated candles as VIEWS (computed on-the-fly from ohlcv_1m)
-- No separate tables to manage -- retention controlled by ohlcv_1m only

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

-- Strategy configurations
-- Audit: SCD Type 2 -- full version history (must know params at time of each trade)
CREATE TABLE trading_platform.strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    type VARCHAR(32) NOT NULL,               -- 'momentum', 'dca_grid', 'mean_reversion', etc.
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    params JSONB NOT NULL DEFAULT '{}',      -- strategy-specific
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

-- strategies indexes
CREATE INDEX idx_strategies_active ON trading_platform.strategies(name)
    WHERE is_active = true AND is_current = true;

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

-- migrate:down
DROP TABLE IF EXISTS trading_platform.ext_coingecko_platforms CASCADE;
DROP TABLE IF EXISTS trading_platform.ext_coingecko_assets CASCADE;
DROP TABLE IF EXISTS trading_platform.strategies CASCADE;
DROP VIEW IF EXISTS trading_platform.ohlcv_4h CASCADE;
DROP VIEW IF EXISTS trading_platform.ohlcv_1h CASCADE;
DROP TABLE IF EXISTS trading_platform.indicators_daily CASCADE;
DROP TABLE IF EXISTS trading_platform.indicators_intraday CASCADE;
DROP TABLE IF EXISTS trading_platform.ohlcv_daily CASCADE;
DROP TABLE IF EXISTS trading_platform.ohlcv_1m CASCADE;
DROP TABLE IF EXISTS trading_platform.trading_pairs CASCADE;
DROP TABLE IF EXISTS trading_platform.asset_mappings CASCADE;
DROP TABLE IF EXISTS trading_platform.assets CASCADE;
DROP TABLE IF EXISTS trading_platform.network_mappings CASCADE;
DROP TABLE IF EXISTS trading_platform.networks CASCADE;
DROP TABLE IF EXISTS trading_platform.venues CASCADE;
DROP SCHEMA IF EXISTS trading_platform CASCADE;

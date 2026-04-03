-- migrate:up

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
    -- Audit snapshots (immutable -- captured at order creation)
    strategy_version INT,                    -- which strategy version was active
    guardrails_snapshot JSONB,               -- guardrail values at time of order
    pair_snapshot JSONB,                     -- {pair_symbol, maker_fee, taker_fee, precision}
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64),
    filled_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- orders indexes
CREATE INDEX idx_orders_status ON trading_platform.orders(status) WHERE status IN ('open', 'partial');
CREATE INDEX idx_orders_exchange_id ON trading_platform.orders(exchange_order_id) WHERE exchange_order_id IS NOT NULL;
CREATE INDEX idx_orders_strategy ON trading_platform.orders(strategy_id, created_at DESC);
CREATE INDEX idx_orders_asset_venue ON trading_platform.orders(asset_id, venue_id, created_at DESC);

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

-- executions indexes
CREATE INDEX idx_executions_order ON trading_platform.executions(order_id);

-- migrate:down
DROP TABLE IF EXISTS trading_platform.executions CASCADE;
DROP TABLE IF EXISTS trading_platform.order_events CASCADE;
DROP TABLE IF EXISTS trading_platform.orders CASCADE;

-- migrate:up

-- Daily portfolio headline
CREATE TABLE trading_platform.portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_value_usd NUMERIC(20,2),
    cash_usd NUMERIC(20,2),
    positions_value_usd NUMERIC(20,2),
    unrealized_pnl_usd NUMERIC(20,2),
    realized_pnl_day_usd NUMERIC(20,2),
    total_fees_day_usd NUMERIC(20,2),
    hodl_value_usd NUMERIC(20,2),
    net_deposits_usd NUMERIC(20,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date)
);

-- Daily per-asset breakdown
CREATE TABLE trading_platform.portfolio_asset_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    asset_id INT REFERENCES trading_platform.assets(id),
    quantity NUMERIC(20,8),
    avg_cost_usd NUMERIC(20,8),
    market_price_usd NUMERIC(20,8),
    value_usd NUMERIC(20,2),
    cost_basis_usd NUMERIC(20,2),
    unrealized_pnl_usd NUMERIC(20,2),
    unrealized_pnl_pct NUMERIC(10,4),
    realized_pnl_day_usd NUMERIC(20,2),
    hodl_value_usd NUMERIC(20,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, asset_id)
);

-- Daily per-strategy performance
CREATE TABLE trading_platform.portfolio_strategy_snapshots (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    strategy_id INT REFERENCES trading_platform.strategies(id),
    total_value_usd NUMERIC(20,2),
    capital_deployed_usd NUMERIC(20,2),
    unrealized_pnl_usd NUMERIC(20,2),
    realized_pnl_day_usd NUMERIC(20,2),
    realized_pnl_cumulative_usd NUMERIC(20,2),
    total_trades INT,
    win_rate NUMERIC(6,4),
    avg_trade_pnl_usd NUMERIC(20,2),
    max_drawdown_pct NUMERIC(10,4),
    sharpe_ratio NUMERIC(10,4),
    hodl_comparison_pct NUMERIC(10,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (date, strategy_id)
);

-- Realized P&L per trade
CREATE TABLE trading_platform.pnl_realized (
    id BIGSERIAL PRIMARY KEY,
    sell_order_id BIGINT REFERENCES trading_platform.orders(id),
    sell_execution_id BIGINT REFERENCES trading_platform.executions(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    strategy_id INT REFERENCES trading_platform.strategies(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    quantity NUMERIC(20,8) NOT NULL,
    cost_basis_usd NUMERIC(20,2) NOT NULL,
    proceeds_usd NUMERIC(20,2) NOT NULL,
    fees_usd NUMERIC(20,2) DEFAULT 0,
    pnl_usd NUMERIC(20,2) NOT NULL,
    pnl_pct NUMERIC(10,4),
    hold_duration_hours INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cost basis lots (FIFO)
-- FIFO ordering is by (account_id, asset_id, acquired_at) — strategy_id is informational
CREATE TABLE trading_platform.cost_basis (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES trading_platform.accounts(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    strategy_id INT REFERENCES trading_platform.strategies(id),
    buy_order_id BIGINT REFERENCES trading_platform.orders(id),
    buy_execution_id BIGINT REFERENCES trading_platform.executions(id),
    quantity_original NUMERIC(20,8) NOT NULL,
    quantity_remaining NUMERIC(20,8) NOT NULL,
    cost_per_unit_usd NUMERIC(20,8) NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cost_basis_fifo ON trading_platform.cost_basis(account_id, asset_id, acquired_at)
    WHERE is_closed = false;

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
    market_conditions TEXT,
    lessons_learned TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Open positions view (separate paper from live)
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

-- migrate:down
DROP VIEW IF EXISTS trading_platform.open_positions CASCADE;
DROP TABLE IF EXISTS trading_platform.trade_journal CASCADE;
DROP TABLE IF EXISTS trading_platform.paper_balances CASCADE;
DROP TABLE IF EXISTS trading_platform.cost_basis CASCADE;
DROP TABLE IF EXISTS trading_platform.pnl_realized CASCADE;
DROP TABLE IF EXISTS trading_platform.portfolio_strategy_snapshots CASCADE;
DROP TABLE IF EXISTS trading_platform.portfolio_asset_snapshots CASCADE;
DROP TABLE IF EXISTS trading_platform.portfolio_snapshots CASCADE;

-- migrate:up

-- Backtest run metadata
CREATE TABLE trading_platform.backtest_runs (
    id BIGSERIAL PRIMARY KEY,
    sweep_id UUID,
    strategy_name VARCHAR(64) NOT NULL,
    strategy_type VARCHAR(32) NOT NULL,
    strategy_params JSONB NOT NULL,
    asset_id INT REFERENCES trading_platform.assets(id),
    venue_id INT REFERENCES trading_platform.venues(id),
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    initial_capital_usd NUMERIC(20,2) NOT NULL,
    slippage_pct NUMERIC(6,4) DEFAULT 0.10,
    maker_fee NUMERIC(6,4),
    taker_fee NUMERIC(6,4),
    total_return_pct NUMERIC(10,4),
    total_return_usd NUMERIC(20,2),
    hodl_return_pct NUMERIC(10,4),
    alpha_pct NUMERIC(10,4),
    total_trades INT,
    winning_trades INT,
    losing_trades INT,
    win_rate NUMERIC(6,4),
    avg_win_pct NUMERIC(10,4),
    avg_loss_pct NUMERIC(10,4),
    profit_factor NUMERIC(10,4),
    max_drawdown_pct NUMERIC(10,4),
    max_drawdown_duration_days INT,
    sharpe_ratio NUMERIC(10,4),
    sortino_ratio NUMERIC(10,4),
    calmar_ratio NUMERIC(10,4),
    avg_hold_duration_hours NUMERIC(10,2),
    run_duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64)
);

CREATE INDEX idx_backtest_sweep ON trading_platform.backtest_runs(sweep_id) WHERE sweep_id IS NOT NULL;

-- Backtest trade log
CREATE TABLE trading_platform.backtest_trades (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES trading_platform.backtest_runs(id) ON DELETE CASCADE,
    trade_num INT NOT NULL,
    entry_date DATE NOT NULL,
    entry_price NUMERIC(20,8) NOT NULL,
    entry_signal_confidence NUMERIC(6,4),
    entry_reasons JSONB,
    exit_date DATE,
    exit_price NUMERIC(20,8),
    exit_reason VARCHAR(32),
    side VARCHAR(4) NOT NULL,
    quantity NUMERIC(20,8) NOT NULL,
    cost_basis_usd NUMERIC(20,2),
    proceeds_usd NUMERIC(20,2),
    fees_usd NUMERIC(20,2),
    slippage_usd NUMERIC(20,2),
    pnl_usd NUMERIC(20,2),
    pnl_pct NUMERIC(10,4),
    hold_duration_days INT,
    portfolio_value_usd NUMERIC(20,2),
    drawdown_pct NUMERIC(10,4),
    UNIQUE (run_id, trade_num)
);

-- Backtest equity curve (daily portfolio value)
CREATE TABLE trading_platform.backtest_equity (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES trading_platform.backtest_runs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    portfolio_value_usd NUMERIC(20,2),
    cash_usd NUMERIC(20,2),
    positions_value_usd NUMERIC(20,2),
    hodl_value_usd NUMERIC(20,2),
    drawdown_pct NUMERIC(10,4),
    UNIQUE (run_id, date)
);

-- migrate:down
DROP TABLE IF EXISTS trading_platform.backtest_equity CASCADE;
DROP TABLE IF EXISTS trading_platform.backtest_trades CASCADE;
DROP TABLE IF EXISTS trading_platform.backtest_runs CASCADE;

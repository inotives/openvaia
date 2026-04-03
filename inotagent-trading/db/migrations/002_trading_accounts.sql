-- migrate:up

-- Accounts on venues (exchange sub-accounts, wallet addresses)
CREATE TABLE trading_platform.accounts (
    id SERIAL PRIMARY KEY,
    venue_id INT REFERENCES trading_platform.venues(id),
    name VARCHAR(64) NOT NULL,
    account_type VARCHAR(16) NOT NULL,
    address VARCHAR(128),
    network_id INT REFERENCES trading_platform.networks(id),
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(64) DEFAULT 'system',
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR(64),
    UNIQUE (venue_id, name, COALESCE(address, ''), COALESCE(network_id, 0))
);

-- Asset balances per account (live — synced from exchanges by private poller)
CREATE TABLE trading_platform.balances (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES trading_platform.accounts(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    balance NUMERIC(20,8) NOT NULL DEFAULT 0,
    available NUMERIC(20,8),
    locked NUMERIC(20,8) DEFAULT 0,
    balance_usd NUMERIC(20,2),
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (account_id, asset_id)
);

-- Balance ledger: append-only audit trail
CREATE TABLE trading_platform.balances_ledger (
    id BIGSERIAL PRIMARY KEY,
    account_id INT REFERENCES trading_platform.accounts(id),
    asset_id INT REFERENCES trading_platform.assets(id),
    amount NUMERIC(20,8) NOT NULL,
    balance_after NUMERIC(20,8),
    entry_type VARCHAR(16) NOT NULL,
    reference_type VARCHAR(16),
    reference_id BIGINT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ledger_account_asset ON trading_platform.balances_ledger(account_id, asset_id, created_at);

-- Transfers: deposits, withdrawals, internal transfers
CREATE TABLE trading_platform.transfers (
    id BIGSERIAL PRIMARY KEY,
    transfer_type VARCHAR(16) NOT NULL,
    from_account_id INT REFERENCES trading_platform.accounts(id),
    from_address VARCHAR(128),
    to_account_id INT REFERENCES trading_platform.accounts(id),
    to_address VARCHAR(128),
    asset_id INT REFERENCES trading_platform.assets(id),
    amount NUMERIC(20,8) NOT NULL,
    amount_usd NUMERIC(20,2),
    network_id INT REFERENCES trading_platform.networks(id),
    tx_hash VARCHAR(128),
    method VARCHAR(32),
    reference VARCHAR(128),
    fee NUMERIC(20,8) DEFAULT 0,
    fee_asset VARCHAR(16),
    status VARCHAR(16) DEFAULT 'pending',
    initiated_by VARCHAR(64),
    initiated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    notes TEXT
);

-- Aggregated view: total balance per asset across all accounts
CREATE VIEW trading_platform.total_balances AS
SELECT
    a.id AS asset_id,
    a.symbol,
    SUM(b.balance) AS total_balance,
    SUM(b.available) AS total_available,
    SUM(b.locked) AS total_locked,
    SUM(b.balance_usd) AS total_usd,
    COUNT(DISTINCT acc.venue_id) AS venue_count
FROM trading_platform.balances b
JOIN trading_platform.accounts acc ON acc.id = b.account_id
JOIN trading_platform.assets a ON a.id = b.asset_id
WHERE acc.deleted_at IS NULL AND acc.is_active = true
GROUP BY a.id, a.symbol;

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

-- migrate:down
DROP VIEW IF EXISTS trading_platform.balance_reconciliation CASCADE;
DROP VIEW IF EXISTS trading_platform.total_balances CASCADE;
DROP TABLE IF EXISTS trading_platform.transfers CASCADE;
DROP TABLE IF EXISTS trading_platform.balances_ledger CASCADE;
DROP TABLE IF EXISTS trading_platform.balances CASCADE;
DROP TABLE IF EXISTS trading_platform.accounts CASCADE;

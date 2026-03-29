-- migrate:up

-- Curated resource directory
CREATE TABLE IF NOT EXISTS platform.resources (
    id          SERIAL PRIMARY KEY,
    url         TEXT NOT NULL,
    name        VARCHAR(128) NOT NULL,
    description TEXT,
    tags        TEXT[] NOT NULL DEFAULT '{}',
    notes       TEXT,
    priority    INT NOT NULL DEFAULT 50 CHECK (priority >= 1 AND priority <= 100),
    status      VARCHAR(16) NOT NULL DEFAULT 'active'
                CHECK (status IN ('draft', 'active', 'rejected', 'inactive')),
    created_by  VARCHAR(64),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resources_tags
    ON platform.resources USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_resources_status
    ON platform.resources (status);

-- Seed curated API resources
INSERT INTO platform.resources (url, name, description, tags, priority, status, created_by) VALUES
    ('https://api.geckoterminal.com/api/v2', 'GeckoTerminal API',
     'DEX trading data — pools, tokens, OHLCV, trades across Solana, Ethereum, and 100+ chains',
     ARRAY['crypto','dex','solana','ethereum','api'], 50, 'active', 'system'),
    ('https://api.llama.fi', 'DeFiLlama API',
     'DeFi analytics — TVL, yields, protocol revenue, stablecoin flows, bridge volumes',
     ARRAY['crypto','defi','tvl','yield','api'], 50, 'active', 'system'),
    ('https://api.coingecko.com/api/v3', 'CoinGecko API',
     'Crypto market data — prices, market caps, volume, trending, historical charts',
     ARRAY['crypto','market','price','api'], 50, 'active', 'system')
ON CONFLICT DO NOTHING;

-- migrate:down

DROP TABLE IF EXISTS platform.resources;

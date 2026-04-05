-- migrate:up

-- Allow spot + perp pairs for same base/quote/venue by including pair_symbol in unique constraint
ALTER TABLE trading_platform.trading_pairs
    DROP CONSTRAINT trading_pairs_venue_id_base_asset_id_quote_asset_id_version_key;

ALTER TABLE trading_platform.trading_pairs
    ADD CONSTRAINT trading_pairs_venue_pair_version_key
    UNIQUE (venue_id, pair_symbol, version);

-- migrate:down

ALTER TABLE trading_platform.trading_pairs
    DROP CONSTRAINT IF EXISTS trading_pairs_venue_pair_version_key;

ALTER TABLE trading_platform.trading_pairs
    ADD CONSTRAINT trading_pairs_venue_id_base_asset_id_quote_asset_id_version_key
    UNIQUE (venue_id, base_asset_id, quote_asset_id, version);

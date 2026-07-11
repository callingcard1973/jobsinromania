-- CEREALE commodity price benchmark (keystone for grain trading).
-- SEPARATE from F&V price-book / trading_offers (read-only on those).
-- Internal/gated: never exposed externally, no scores published.

CREATE TABLE IF NOT EXISTS cereale_price_benchmark (
    id            BIGSERIAL PRIMARY KEY,
    product       TEXT NOT NULL,              -- grau|porumb|orz|floarea-soarelui|rapita
    source        TEXT NOT NULL,              -- euronext_matif|brm|constanta_fob|apia_madr|manual
    price_eur_ton DOUBLE PRECISION,
    price_ron_ton DOUBLE PRECISION,
    ref_date      DATE NOT NULL,
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    note          TEXT,
    UNIQUE (product, source, ref_date)
);

CREATE INDEX IF NOT EXISTS idx_cereale_bench_product ON cereale_price_benchmark (product, ref_date DESC);
CREATE INDEX IF NOT EXISTS idx_cereale_bench_source  ON cereale_price_benchmark (source);

-- De-dup ledger for spread alerts (so the same offer does not re-alert).
CREATE TABLE IF NOT EXISTS cereale_spread_alerts (
    id           BIGSERIAL PRIMARY KEY,
    offer_id     TEXT NOT NULL,
    product      TEXT,
    offered_eur_ton DOUBLE PRECISION,
    benchmark_eur_ton DOUBLE PRECISION,
    benchmark_source  TEXT,
    spread_pct   DOUBLE PRECISION,
    direction    TEXT,                        -- below|above
    alerted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (offer_id)
);

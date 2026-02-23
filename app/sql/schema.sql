-- ─── Rastera Engine — PostGIS Schema ─────────────────────────────────────────
-- Executed automatically by docker-compose on first DB start.
-- Safe to re-run (CREATE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────────────────────
-- tenants
-- Multi-tenant anchor. Each demo client gets their own slug.
-- TODO: add plan/tier column for billing segmentation in V2.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT        NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- sites
-- Candidate locations evaluated by the scoring engine.
-- geom: centroid point of the proposed site.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sites (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    address     TEXT,
    geom        GEOMETRY(Point, 4326) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sites_geom      ON sites USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_sites_tenant_id ON sites (tenant_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- pois
-- Points of Interest in the competitive landscape (competitors, anchors, etc.).
-- Scoped per-tenant so demo data doesn't bleed across accounts.
-- TODO: add source column (osm, google, esri, custom) for data provenance.
-- TODO: add scraped_at TIMESTAMPTZ for freshness tracking.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pois (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    category    TEXT        NOT NULL,
    brand       TEXT,
    geom        GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pois_geom      ON pois USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_pois_tenant_id ON pois (tenant_id);
CREATE INDEX IF NOT EXISTS idx_pois_category  ON pois (category);

-- ─────────────────────────────────────────────────────────────────────────────
-- scores
-- Immutable scoring snapshots.  New analysis = new row; history is preserved.
-- drivers_json / competitor_summary / market_summary: JSONB for flexibility.
-- ai_summary: nullable JSONB — absent if AI was disabled or unavailable.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    site_id             UUID        NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    score_total         NUMERIC(5, 2) NOT NULL,
    drivers_json        JSONB       NOT NULL DEFAULT '[]',
    competitor_summary  JSONB       NOT NULL DEFAULT '{}',
    market_summary      JSONB       NOT NULL DEFAULT '{}',
    ai_summary          JSONB,
    radius_m            INTEGER     NOT NULL DEFAULT 1600,
    industry_template   TEXT        NOT NULL DEFAULT 'coffee',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scores_site_id    ON scores (site_id);
CREATE INDEX IF NOT EXISTS idx_scores_created_at ON scores (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_template   ON scores (industry_template);

-- ─────────────────────────────────────────────────────────────────────────────
-- tenant_api_keys
-- Per-tenant API credentials.  Only the SHA-256 hex digest is stored; the raw
-- key is shown once at creation time and never persisted.
-- revoked_at IS NULL  → active key.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    id           UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL DEFAULT 'default',
    key_hash     TEXT        NOT NULL UNIQUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash  ON tenant_api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant_id ON tenant_api_keys (tenant_id);

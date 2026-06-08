-- CivicOS: Initial Schema Migration
-- ===================================
-- This is the foundational schema. Every table, index, and constraint here
-- supports the core extraction → storage → API pipeline.
--
-- Design decisions:
--   - UUIDs for all public-facing IDs (not serial) — prevents enumeration,
--     enables distributed ID generation if we ever shard.
--   - JSONB for eligibility_json and diff columns — flexible schema for
--     heterogeneous government data without requiring schema migrations
--     every time a new program type is added.
--   - program_versions as a full snapshot + computed diff table — this is
--     more storage-intensive than an event sourcing model, but far simpler
--     to query. Storage is cheap; developer time is not.
--   - TIMESTAMPTZ everywhere — always store UTC, let the API layer convert
--     to the client's timezone.

-- Extension for full-text search and UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- Cities that CivicOS covers
-- ============================================================
CREATE TABLE cities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        VARCHAR(50) UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    state       CHAR(2) NOT NULL,
    timezone    VARCHAR(50) NOT NULL DEFAULT 'America/New_York',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Program categories (housing, food, healthcare, etc.)
-- ============================================================
CREATE TABLE categories (
    id      SERIAL PRIMARY KEY,
    slug    VARCHAR(50) UNIQUE NOT NULL,
    name    VARCHAR(100) NOT NULL,
    icon    VARCHAR(50)  -- optional: emoji or icon name for UI rendering
);

-- ============================================================
-- Government benefit/resource programs — the core table
-- ============================================================
CREATE TABLE programs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id           UUID NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    category_id       INTEGER NOT NULL REFERENCES categories(id),
    name              VARCHAR(200) NOT NULL,
    description       TEXT,
    eligibility       TEXT,
    eligibility_json  JSONB,
    benefit_amount    VARCHAR(200),
    how_to_apply      TEXT,
    application_url   TEXT,
    phone             VARCHAR(20),
    email             VARCHAR(200),
    address           TEXT,
    languages         TEXT[] DEFAULT '{en}',
    deadline          DATE,
    is_ongoing        BOOLEAN DEFAULT TRUE,
    status            VARCHAR(20) NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active', 'inactive', 'unknown')),
    source_url        TEXT NOT NULL,
    source_type       VARCHAR(20) NOT NULL
                      CHECK (source_type IN ('web', 'pdf', 'rss')),
    raw_text          TEXT,
    raw_html          TEXT,
    extracted_at      TIMESTAMPTZ DEFAULT NOW(),
    last_checked_at   TIMESTAMPTZ,
    last_modified_at  TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    -- Full-text search vector (populated by trigger)
    search_vector     tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(eligibility, '')), 'C')
    ) STORED
);

-- ============================================================
-- Tracks every version of a program record (for change detection)
-- ============================================================
CREATE TABLE program_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id  UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    snapshot    JSONB NOT NULL,
    diff        JSONB,
    changed_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Data sources — URLs to scrape or monitor
-- ============================================================
CREATE TABLE sources (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city_id          UUID NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    url              TEXT NOT NULL,
    source_type      VARCHAR(20) NOT NULL
                     CHECK (source_type IN ('web', 'pdf', 'rss')),
    scrape_frequency VARCHAR(20) DEFAULT 'weekly'
                     CHECK (scrape_frequency IN ('daily', 'weekly', 'monthly', 'manual')),
    last_scraped_at  TIMESTAMPTZ,
    last_status      VARCHAR(20) DEFAULT 'pending'
                     CHECK (last_status IN ('pending', 'success', 'error')),
    last_error       TEXT,
    is_active        BOOLEAN DEFAULT TRUE,
    notes            TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Ingestion run log — audit trail of every scraping + extraction job
-- ============================================================
CREATE TABLE ingestion_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   UUID REFERENCES sources(id) ON DELETE SET NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'started'
                CHECK (status IN ('started', 'scraped', 'extracted', 'stored', 'error')),
    programs_found   INTEGER DEFAULT 0,
    programs_new     INTEGER DEFAULT 0,
    programs_updated INTEGER DEFAULT 0,
    error_message    TEXT,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- Indexes
-- ============================================================

-- Programs: common filter patterns
CREATE INDEX idx_programs_city ON programs(city_id);
CREATE INDEX idx_programs_category ON programs(category_id);
CREATE INDEX idx_programs_status ON programs(status);
CREATE INDEX idx_programs_languages ON programs USING GIN (languages);
CREATE INDEX idx_programs_eligibility ON programs USING GIN (eligibility_json);
CREATE INDEX idx_programs_search ON programs USING GIN (search_vector);
CREATE INDEX idx_programs_source_url ON programs(source_url);

-- Program versions: fast history lookups
CREATE INDEX idx_program_versions_program ON program_versions(program_id, changed_at DESC);

-- Sources: find due-for-scrape sources efficiently
CREATE INDEX idx_sources_city ON sources(city_id);
CREATE INDEX idx_sources_next_scrape ON sources(is_active, last_scraped_at)
    WHERE is_active = TRUE;

-- Ingestion runs: audit queries
CREATE INDEX idx_ingestion_runs_source ON ingestion_runs(source_id, started_at DESC);

-- ============================================================
-- Trigger: auto-update updated_at on programs
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_programs_updated_at
    BEFORE UPDATE ON programs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Trigger: create program_version on program insert/update
-- ============================================================
CREATE OR REPLACE FUNCTION capture_program_version()
RETURNS TRIGGER AS $$
DECLARE
    prev_snapshot JSONB;
    computed_diff JSONB;
BEGIN
    -- Build a snapshot of the current row
    IF TG_OP = 'UPDATE' THEN
        -- Compute what changed between OLD and NEW
        SELECT row_to_json(OLD.*)::jsonb INTO prev_snapshot;

        computed_diff := jsonb_build_object();
        IF OLD.name IS DISTINCT FROM NEW.name THEN
            computed_diff := jsonb_set(computed_diff, '{name}', to_jsonb(NEW.name));
        END IF;
        IF OLD.description IS DISTINCT FROM NEW.description THEN
            computed_diff := jsonb_set(computed_diff, '{description}', to_jsonb(NEW.description));
        END IF;
        IF OLD.eligibility IS DISTINCT FROM NEW.eligibility THEN
            computed_diff := jsonb_set(computed_diff, '{eligibility}', to_jsonb(NEW.eligibility));
        END IF;
        IF OLD.eligibility_json IS DISTINCT FROM NEW.eligibility_json THEN
            computed_diff := jsonb_set(computed_diff, '{eligibility_json}', NEW.eligibility_json);
        END IF;
        IF OLD.benefit_amount IS DISTINCT FROM NEW.benefit_amount THEN
            computed_diff := jsonb_set(computed_diff, '{benefit_amount}', to_jsonb(NEW.benefit_amount));
        END IF;
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            computed_diff := jsonb_set(computed_diff, '{status}', to_jsonb(NEW.status));
        END IF;
        IF OLD.how_to_apply IS DISTINCT FROM NEW.how_to_apply THEN
            computed_diff := jsonb_set(computed_diff, '{how_to_apply}', to_jsonb(NEW.how_to_apply));
        END IF;
        IF OLD.application_url IS DISTINCT FROM NEW.application_url THEN
            computed_diff := jsonb_set(computed_diff, '{application_url}', to_jsonb(NEW.application_url));
        END IF;
        IF OLD.deadline IS DISTINCT FROM NEW.deadline THEN
            computed_diff := jsonb_set(computed_diff, '{deadline}', to_jsonb(NEW.deadline));
        END IF;
    END IF;

    INSERT INTO program_versions (program_id, snapshot, diff)
    VALUES (NEW.id, row_to_json(NEW.*)::jsonb, computed_diff);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER capture_program_version_insert
    AFTER INSERT ON programs
    FOR EACH ROW
    EXECUTE FUNCTION capture_program_version();

CREATE TRIGGER capture_program_version_update
    AFTER UPDATE ON programs
    FOR EACH ROW
    EXECUTE FUNCTION capture_program_version();
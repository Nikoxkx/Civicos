-- CivicOS: Seed Data
-- ===================================
-- This seeds the minimum data needed to run the first scraper + extraction
-- pipeline against Boston. All UUIDs are deterministic (generated from
-- md5 hashes) so this seed is idempotent — safe to run multiple times.

-- ============================================================
-- Cities
-- ============================================================
INSERT INTO cities (id, slug, name, state, timezone) VALUES
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'boston', 'Boston', 'MA', 'America/New_York')
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- Categories
-- ============================================================
INSERT INTO categories (slug, name, icon) VALUES
    ('housing',        'Housing',         '🏠'),
    ('food',           'Food Assistance', '🍎'),
    ('healthcare',     'Healthcare',      '🏥'),
    ('utilities',      'Utilities',       '⚡'),
    ('childcare',      'Childcare',       '🧒'),
    ('employment',     'Employment',      '💼'),
    ('legal',          'Legal Aid',       '⚖️'),
    ('transportation', 'Transportation',  '🚌'),
    ('other',          'Other',           '📋')
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- Initial Boston data sources
-- ============================================================
INSERT INTO sources (id, city_id, url, source_type, scrape_frequency, notes) VALUES
    (
        'b1b2b3b4-c5c6-7890-abcd-ef1234567891',
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'https://www.boston.gov/departments/housing/our-work-neighborhood-development',
        'web',
        'weekly',
        'Mayor''s Office of Housing — main programs and services listing'
    ),
    (
        'b1b2b3b4-c5c6-7890-abcd-ef1234567892',
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'https://www.boston.gov/departments/participatory-budgeting/bridging-gap-assistance-housing-stability',
        'web',
        'weekly',
        'Bridging the Gap — flexible housing stability assistance'
    )
ON CONFLICT DO NOTHING;
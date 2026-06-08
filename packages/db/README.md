# CivicOS DB — Database Schema & Migrations

**PostgreSQL 16+ schema for storing structured government benefit program data.**

## Overview

The CivicOS database is the canonical store for all ingested and extracted
program data. It uses a few key patterns:

- **UUIDs for public IDs** — prevents enumeration, enables distributed generation
- **JSONB for flexible fields** — `eligibility_json` and `program_versions.diff`
  adapt to heterogeneous government data without schema migrations
- **GENERATED tsvector column** — full-text search with zero external infrastructure
- **Trigger-based versioning** — every program insert/update creates a snapshot
  in `program_versions` with a computed diff

## Tables

| Table | Purpose |
|-------|---------|
| `cities` | Cities covered by CivicOS |
| `categories` | Program categories (housing, food, healthcare, etc.) |
| `programs` | Core program records — the main entity |
| `program_versions` | Every historical version of a program with computed diffs |
| `sources` | URLs to scrape — the input source registry |
| `ingestion_runs` | Audit trail of every scrape + extraction job |

## Quick Start

```bash
# Create database
createdb civicos

# Run migrations
psql -d civicos -f packages/db/migrations/001_initial_schema.sql
psql -d civicos -f packages/db/migrations/002_seed_data.sql
```

## Migrations

Migrations are raw SQL (not Alembic) for v0.1. This keeps the dependency
footprint small and makes reasoning about the schema explicit.

To add a migration, create a new numbered file in `migrations/`:

```
003_add_food_programs.sql
004_add_contact_methods.sql
```

## Query Examples

```sql
-- All active housing programs in Boston
SELECT * FROM programs
WHERE status = 'active'
  AND category_id = (SELECT id FROM categories WHERE slug = 'housing')
  AND city_id = (SELECT id FROM cities WHERE slug = 'boston');

-- Full-text search for rental assistance
SELECT name, description, ts_rank(search_vector, q) AS rank
FROM programs, plainto_tsquery('english', 'rental assistance') q
WHERE search_vector @@ q
ORDER BY rank DESC;

-- See what changed on a program's last update
SELECT diff, changed_at FROM program_versions
WHERE program_id = '...'
ORDER BY changed_at DESC LIMIT 1;
```

---
sidebar_position: 3
---

# Database Schema

## Tables

### `cities`
Cities covered by CivicOS. One city → many programs and sources.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `slug` | VARCHAR(50) | URL-safe identifier: "boston", "new-york-city" |
| `name` | VARCHAR(100) | Human-readable: "Boston" |
| `state` | CHAR(2) | "MA", "NY", etc. |
| `timezone` | VARCHAR(50) | IANA timezone for timezone-aware rendering |

### `categories`
Fixed set of program categories.

| slug | name | icon |
|------|------|------|
| `housing` | Housing | 🏠 |
| `food` | Food Assistance | 🍎 |
| `healthcare` | Healthcare | 🏥 |
| `utilities` | Utilities | ⚡ |
| `childcare` | Childcare | 🧒 |
| `employment` | Employment | 💼 |
| `legal` | Legal Aid | ⚖️ |
| `transportation` | Transportation | 🚌 |
| `other` | Other | 📋 |

### `programs`
The core table. Every row is a government benefit program or resource.

Key columns:
- `eligibility_json` (JSONB) — flexible structured eligibility
- `search_vector` (tsvector) — auto-generated for full-text search
- `raw_html` (TEXT) — preserved for re-extraction with improved models
- `source_url` + `source_type` — provenance tracking

### `program_versions`
Every insert or update to `programs` triggers a version snapshot with a computed `diff`:

```json
{
  "benefit_amount": "$500/month",  // old: null
  "status": "inactive"             // old: "active"
}
```

### `sources`
URLs to scrape. One city → many sources. Tracks last scrape status and frequency.

### `ingestion_runs`
Audit trail. Every scrape → extract → store cycle creates a run record with
program counts and error details.

## Indexes

- GIN indexes on `eligibility_json` and `languages` for array/JSONB queries
- GIN index on `search_vector` for full-text search
- B-tree indexes on `city_id`, `category_id`, `status` for common filter patterns
- Compound index on `(is_active, last_scraped_at)` for finding due-for-scrape sources
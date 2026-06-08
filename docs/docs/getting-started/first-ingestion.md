---
sidebar_position: 3
---

# First Ingestion

## Manual Ingestion via CLI

```bash
# Ingest all registered Boston sources
civicos ingest --city boston
```

This scrapes every registered source URL for Boston, runs the extraction
pipeline, and stores results in PostgreSQL.

## Ingest a Single URL

```bash
# Scrape only — see what raw text comes back
civicos scrape --url "https://www.boston.gov/departments/housing/..."

# Full extract — see what programs are detected
civicos extract --url "https://www.boston.gov/departments/housing/..."
```

## Ingestion via API

```bash
# First, add a data source
curl -X POST http://localhost:8000/v1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "city_slug": "boston",
    "url": "https://www.boston.gov/departments/housing/...",
    "source_type": "web",
    "scrape_frequency": "weekly"
  }'

# Then trigger ingestion
curl -X POST http://localhost:8000/v1/ingest/<source_id>
```

## What Happens During Ingestion

1. **Scrape**: The URL is fetched (httpx for static, Playwright for JS-rendered)
2. **Clean**: HTML is stripped, text is normalized
3. **Extract**: Claude or rule-based extraction parses structured programs
4. **Deduplicate**: Programs matched by name + source_url are updated, duplicates removed
5. **Version**: Every new or updated program gets a snapshot in `program_versions`
6. **Store**: Programs are inserted or updated in PostgreSQL

## Ingestion Run Tracking

Every ingestion run creates a record in the `ingestion_runs` table:

```sql
SELECT status, programs_found, programs_new, programs_updated, completed_at
FROM ingestion_runs
ORDER BY started_at DESC;
```
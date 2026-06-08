---
sidebar_position: 1
---

# Adding a New City

This guide walks through adding a new city to CivicOS.

## 1. Add the city to the database

```sql
INSERT INTO cities (id, slug, name, state, timezone)
VALUES (gen_random_uuid(), 'chicago', 'Chicago', 'IL', 'America/Chicago');
```

Or via seed data in `packages/db/migrations/002_seed_data.sql`:

```sql
INSERT INTO cities (slug, name, state, timezone) VALUES
    ('chicago', 'Chicago', 'IL', 'America/Chicago')
ON CONFLICT (slug) DO NOTHING;
```

## 2. Add data sources

Register URLs to scrape:

```sql
INSERT INTO sources (city_id, url, source_type, scrape_frequency, notes) VALUES
    (
        (SELECT id FROM cities WHERE slug = 'chicago'),
        'https://www.chicago.gov/city/en/depts/doh/provdrs/renters.html',
        'web',
        'weekly',
        'Chicago Department of Housing — rental assistance programs'
    );
```

Or via the API:

```bash
curl -X POST http://localhost:8000/v1/sources \
  -H "Content-Type: application/json" \
  -d '{
    "city_slug": "chicago",
    "url": "https://www.chicago.gov/...",
    "source_type": "web",
    "scrape_frequency": "weekly"
  }'
```

## 3. Test scraping

```bash
civicos scrape --url "https://www.chicago.gov/..."
```

Check that the extracted text contains program information.

## 4. Add extraction patterns (mock mode)

If using mock extraction, add keyword patterns in
`packages/extraction/mock_client.py` for Chicago-specific programs.

## 5. Run ingestion

```bash
civicos ingest --city chicago
```

## 6. Verify

```bash
curl http://localhost:8000/v1/cities/chicago
curl http://localhost:8000/v1/cities/chicago/programs
```

## Tips

- **Start with housing programs** — they're the most standardized across cities
- **Check for PDF sources** — many cities publish program guides as PDFs
- **Test with `--scrape-only` first** — verify text extraction before running the full pipeline
- **Add sources incrementally** — 3-5 good sources per city is better than 50 low-quality ones
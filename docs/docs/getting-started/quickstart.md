---
sidebar_position: 2
---

# Quick Start

Run the full pipeline in 5 minutes:

```bash
# 1. Seed the database
civicos seed

# 2. Run the demo (scrape → extract → store → verify)
python demo.py

# 3. Start the API
civicos serve

# 4. Query your data
curl http://localhost:8000/v1/programs
curl http://localhost:8000/v1/programs?category=housing
curl "http://localhost:8000/v1/search?q=rental+assistance"

# 5. Open API docs
open http://localhost:8000/docs
```

## Expected Output

The demo script scrapes 3 real Boston.gov data sources and extracts programs:

```
✅ Scraped 3 sources, 21,769 total characters
✅ Found 13 programs across 3 sources
✅ Stored 13 new programs
✅ API verified — 13 programs returned

API endpoints verified:
  GET /v1/programs         → 13 programs
  GET /v1/programs?category=housing → 13 programs
  GET /v1/search?q=housing → 7 results
```

## Next Steps

- **[Add a new city](/docs/guides/adding-a-city)** — expand coverage beyond Boston
- **[Deploy to production](/docs/guides/deploying)** — Docker, reverse proxy, cron
- **[Explore the API](/docs/api/overview)** — full endpoint reference
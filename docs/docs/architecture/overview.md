---
sidebar_position: 1
---

# Architecture Overview

CivicOS follows a pipeline architecture:

```
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌───────┐
│ Sources  │───▶│  Ingestion   │───▶│   API    │───▶│ Apps  │
│ (gov URLs)│    │ scrape→store │    │ (FastAPI)│    │ (DOR) │
└──────────┘    └──────────────┘    └──────────┘    └───────┘
                      │                   │
                      ▼                   ▼
               ┌────────────┐    ┌──────────────┐
               │ Extraction │    │  PostgreSQL  │
               │ (Claude)   │    │  + pgvector  │
               └────────────┘    └──────────────┘
```

## Packages

| Package | Language | Purpose |
|---------|----------|---------|
| `api` | Python/FastAPI | REST API server |
| `ingestion` | Python | Web scraper + PDF parser |
| `extraction` | Python | LLM + rule-based extraction |
| `db` | SQL | Schema, migrations, seeds |
| `sdk-js` | TypeScript | npm package for API consumers |
| `sdk-py` | Python | pip package for API consumers |
| `cli` | Python/Click | Command-line management tool |

## Data Flow

1. **Source URLs** are registered in the `sources` table
2. **Scraper** fetches the page/PDF, extracts clean text
3. **Extraction pipeline** parses text into structured `Program` records
4. **API** serves the data with filtering, search, and pagination
5. **Change detection** triggers create `program_versions` on update
6. **Consumers** (DOR101, third-party apps) query the API

## Design Decisions

- **PostgreSQL, not MongoDB**: Government data is relational — programs have cities, categories, and versions. JSONB covers the flexible fields without sacrificing SQL query power.
- **UUIDs, not auto-increment IDs**: Prevents enumeration attacks and enables future sharding.
- **Raw HTML preservation**: Storage is cheap; re-scraping is expensive. We keep `raw_html` alongside `raw_text` so extraction can be re-run later with improved models.
- **Mock extraction fallback**: Rule-based extraction catches ~70% of programs without API costs, enabling CI/CD and local development.
- **No message queue (yet)**: v0.1 runs ingestion synchronously in the API handler. A Celery/RQ worker can be added when multi-city weekly cron becomes necessary.
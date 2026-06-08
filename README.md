# CivicOS

**Open-source civic data intelligence platform.** CivicOS ingests government benefit and housing data from scattered websites and PDFs, uses LLMs to extract structured information, and exposes it all via a clean REST API — so any city, developer, or nonprofit can build resource navigators for their community.

> Built by [Bel](https://github.com/Yeisbel) — a high school junior from Dorchester, Boston. DOR101 was the first app. CivicOS is the platform that makes it possible for every city.

## The Problem

Government benefit programs — housing assistance, food aid, healthcare subsidies — exist in every city. But the information lives across dozens of inconsistently formatted websites, PDFs, and outdated portals. The people who need these services most are the least equipped to navigate this fragmentation.

## What CivicOS Does

1. **Ingest** — Scrapes government websites and PDFs (Playwright + httpx)
2. **Extract** — Uses Claude to parse unstructured text into structured program data
3. **Store** — Normalized PostgreSQL schema with version history and change detection
4. **Serve** — REST API with filtering, search, and program history endpoints
5. **Monitor** — Detects when government pages change and flags what was updated

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Yeisbel/civicos.git
cd civicos

# Copy environment config
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY

# Start PostgreSQL + API
docker compose up -d

# The API is now running at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

## Architecture

```
civicos/
├── packages/
│   ├── api/          # FastAPI REST server (port 8000)
│   ├── ingestion/    # Web scraper + PDF parser
│   ├── extraction/   # Claude API extraction pipeline
│   └── db/           # PostgreSQL schema + migrations + seeds
├── apps/
│   └── dor101/       # Electron desktop app (API consumer)
└── docs/             # Docusaurus documentation site
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/programs` | List programs (filter by city, category, language, status) |
| GET | `/v1/programs/:id` | Get a single program with full details |
| GET | `/v1/programs/:id/history` | Version history for a program |
| GET | `/v1/cities` | List covered cities |
| GET | `/v1/cities/:slug/programs` | Programs for a specific city |
| GET | `/v1/categories` | List all program categories |
| GET | `/v1/search?q=...` | Full-text search across programs |
| POST | `/v1/sources` | Add a new data source (admin) |
| POST | `/v1/ingest/:source_id` | Trigger ingestion for a source (admin) |

All list endpoints return: `{ data: [...], meta: { total, page, limit, pages } }`

## Tech Stack

- **API:** FastAPI (Python 3.12+) with asyncpg + SQLAlchemy
- **Database:** PostgreSQL 16 with pgvector
- **Scraping:** httpx (static) + Playwright (JS-rendered)
- **Extraction:** Anthropic Claude API (claude-sonnet-4-20250514)
- **Logging:** structlog (structured JSON logs)
- **Validation:** Pydantic v2

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup instructions.

### Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `chore:` maintenance, deps
- `docs:` documentation

## License

MIT — see [LICENSE](LICENSE)

## The Story

CivicOS started in Dorchester, Boston. I watched my neighbors struggle to find housing assistance and food programs scattered across dozens of government URLs. I built DOR101 to solve it for my community. Then I realized every city has this problem, and almost no city has the engineering resources to build the extraction and normalization layer.

CivicOS is that layer, open-sourced, so any developer or city can deploy it and give their residents the same tool.

— Bel

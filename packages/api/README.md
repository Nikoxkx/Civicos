# CivicOS API — REST Server

**FastAPI-based REST API serving structured government benefit data.**

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/programs` | List programs (filter by city, category, language, status) |
| GET | `/v1/programs/:id` | Get a single program with full details |
| GET | `/v1/programs/:id/history` | Version history for a program |
| GET | `/v1/cities` | List covered cities |
| GET | `/v1/cities/:slug` | City detail |
| GET | `/v1/cities/:slug/programs` | Programs for a specific city |
| GET | `/v1/categories` | List all program categories |
| GET | `/v1/search` | Full-text search across programs |
| POST | `/v1/sources` | Add a new data source (admin) |
| POST | `/v1/ingest/:source_id` | Trigger ingestion for a source |

## Architecture

```
routers/          # Route handlers — one file per resource
  programs.py     # Programs CRUD + search + history
  cities.py       # Cities CRUD + city-scoped programs
  categories.py   # Categories listing
  sources.py      # Source management + ingestion trigger

models.py         # SQLAlchemy ORM models (maps 1:1 to DB)
schemas.py        # Pydantic request/response schemas
db.py             # Async SQLAlchemy engine + session factory
config.py         # Pydantic Settings (env vars → config)
main.py           # FastAPI app entry point + middleware
```

## Quick Start

```bash
# Install civicos
pip install -e ".[dev]"

# Set required env vars
export DATABASE_URL=postgresql+asyncpg://civicos:civicos_dev@localhost:5432/civicos

# Run the API
uvicorn packages.api.main:app --reload --port 8000

# Open Swagger docs
open http://localhost:8000/docs
```

## Response Format

All list endpoints return a `{ data, meta }` envelope:

```json
{
  "data": [...],
  "meta": {
    "total": 13,
    "page": 1,
    "limit": 20,
    "pages": 1
  }
}
```

All error responses are structured:

```json
{
  "error": {
    "code": "PROGRAM_NOT_FOUND",
    "message": "No program found with id ..."
  }
}
```

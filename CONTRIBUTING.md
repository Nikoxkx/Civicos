# CivicOS — Contributing Guide

## Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or Docker)
- Node.js 20+ (for Playwright)

### Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/Yeisbel/civicos.git
cd civicos

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Install Playwright browsers
playwright install chromium

# 5. Copy and edit environment config
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 6. Start PostgreSQL (via Docker)
docker compose up -d db

# 7. Run the API
uvicorn packages.api.main:app --reload --port 8000
```

### Running Tests

```bash
# Create test database
createdb civicos_test

# Run tests
pytest -v
```

### Code Quality

```bash
# Lint
ruff check packages/

# Type check
mypy packages/

# Format
ruff format packages/
```

## Architecture

See [README.md](README.md) for the full architecture overview.

### Adding a new city

1. Add the city to the seed data (`packages/db/migrations/002_seed_data.sql`)
2. Add data source URLs for the city in the same file
3. Trigger ingestion via the API: `POST /v1/ingest/:source_id`

### Adding a new extraction schema field

1. Add the field to `EXTRACTION_SYSTEM_PROMPT` in `packages/extraction/prompts.py`
2. Add the column to the `programs` table via a new migration
3. Update `schemas.py` (Pydantic model)
4. Update `models.py` (SQLAlchemy model)
5. Update the `sources.py` router's store logic

## Commit Convention

- `feat:` — new feature (e.g. `feat: add change detection diff algorithm`)
- `fix:` — bug fix (e.g. `fix: handle PDFs with embedded images`)
- `chore:` — maintenance (e.g. `chore: bump playwright to 1.45`)
- `docs:` — documentation (e.g. `docs: add API auth guide`)
- `test:` — tests (e.g. `test: add extraction pipeline integration test`)
- `refactor:` — code change that neither fixes nor adds features

## Questions?

Open a GitHub issue or reach out to Bel directly.

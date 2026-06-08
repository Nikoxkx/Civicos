---
sidebar_position: 1
---

# Installation

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 16+** (or Docker)
- **Node.js 20+** (for Playwright browser automation)

## Install from source

```bash
git clone https://github.com/Yeisbel/civicos.git
cd civicos
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## Database Setup

### Option 1: Docker (recommended)

```bash
docker compose up -d db
```

### Option 2: Local PostgreSQL

```bash
# Create database and user
sudo -u postgres createuser civicos -P
sudo -u postgres createdb civicos -O civicos

# Run migrations
psql -d civicos -f packages/db/migrations/001_initial_schema.sql
psql -d civicos -f packages/db/migrations/002_seed_data.sql
```

## Configure

```bash
cp .env.example .env
# Edit .env:
#   DATABASE_URL=postgresql+asyncpg://civicos:password@localhost:5432/civicos
#   ANTHROPIC_API_KEY=sk-ant-... (optional — enables Claude extraction)
```

## Verify

```bash
# Start API
uvicorn packages.api.main:app --port 8000

# In another terminal
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0"}

curl http://localhost:8000/v1/categories
# [{"id":1,"slug":"housing","name":"Housing","icon":"🏠"},...]
```
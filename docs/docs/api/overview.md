---
sidebar_position: 1
---

# API Overview

The CivicOS REST API serves structured government benefit program data.

**Base URL:** `http://localhost:8000/v1`

## Authentication

v0.1 has no authentication — designed for self-hosted deployments behind
a reverse proxy. API key auth will be added in v0.5.

## Response Format

All **list** endpoints return:

```json
{
  "data": [ /* array of results */ ],
  "meta": {
    "total": 13,
    "page": 1,
    "limit": 20,
    "pages": 1
  }
}
```

All **single-resource** endpoints return the resource directly:

```json
{
  "id": "uuid",
  "name": "Program Name",
  ...
}
```

All **error** responses are structured:

```json
{
  "error": {
    "code": "PROGRAM_NOT_FOUND",
    "message": "No program found with id ..."
  }
}
```

## Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/programs` | — | List programs |
| GET | `/v1/programs/:id` | — | Get program detail |
| GET | `/v1/programs/:id/history` | — | Version history |
| GET | `/v1/cities` | — | List cities |
| GET | `/v1/cities/:slug` | — | City detail |
| GET | `/v1/cities/:slug/programs` | — | City-scoped programs |
| GET | `/v1/categories` | — | List categories |
| GET | `/v1/search` | — | Full-text search |
| POST | `/v1/sources` | admin | Add data source |
| POST | `/v1/ingest/:source_id` | admin | Trigger ingestion |
| GET | `/health` | — | Health check |

## Pagination

All list endpoints support `page` and `limit` query parameters:

```
GET /v1/programs?page=1&limit=20
```

Max `limit` is 100. Default is 20.

## Filtering

Programs support multiple filter dimensions:

```
# By city
GET /v1/programs?city=boston

# By category
GET /v1/programs?category=housing

# By language
GET /v1/programs?language=es

# By status
GET /v1/programs?status=active  # or inactive, all

# Combined
GET /v1/programs?city=boston&category=housing&language=es
```

## Full-Text Search

Uses PostgreSQL's built-in tsvector/tsquery with ranking:

```
GET /v1/search?q=rental+assistance
```

Results are ranked by relevance score. Minimum query length is 2 characters.

## OpenAPI / Swagger

When running in development mode, interactive API docs are available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
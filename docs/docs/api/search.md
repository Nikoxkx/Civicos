---
sidebar_position: 4
---

# Search API

Full-text search across program names, descriptions, and eligibility text.

## Endpoint

```http
GET /v1/search?q=rental+assistance
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `q` | string | **required** | Search query (min 2 characters) |
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Results per page |

## How It Works

CivicOS uses PostgreSQL's built-in full-text search with a GENERATED `tsvector` column:

```sql
search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(eligibility, '')), 'C')
) STORED
```

- **Weight A (highest):** Program name
- **Weight B:** Description
- **Weight C:** Eligibility text

Results are ranked by `ts_rank()`, so name matches appear first.

## Examples

```bash
# Simple search
curl "http://localhost:8000/v1/search?q=seniors"

# Multi-word
curl "http://localhost:8000/v1/search?q=affordable+housing"

# Combined with pagination
curl "http://localhost:8000/v1/search?q=rental+assistance&page=1&limit=10"
```

## Response

Same `{ data, meta }` envelope as other list endpoints, with programs ranked
by relevance to your search query.
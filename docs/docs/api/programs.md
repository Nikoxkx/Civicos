---
sidebar_position: 2
---

# Programs API

## List Programs

```http
GET /v1/programs
```

Filter by city, category, language, or status:

```http
GET /v1/programs?city=boston&category=housing&status=active&page=1&limit=20
```

**Parameters:**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `city` | string | — | City slug |
| `category` | string | — | Category slug |
| `language` | string | — | Language code (en, es, pt, etc.) |
| `status` | string | `"active"` | active, inactive, or all |
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Results per page (max 100) |

**Response:**

```json
{
  "data": [
    {
      "id": "uuid",
      "city_id": "uuid",
      "category_id": 1,
      "name": "Seniors Save",
      "description": "Helps seniors replace failing heating systems...",
      "benefit_amount": "varies",
      "status": "active",
      "is_ongoing": true,
      "languages": ["en"],
      "deadline": null,
      "created_at": "2026-06-08T14:59:22Z"
    }
  ],
  "meta": {
    "total": 13,
    "page": 1,
    "limit": 20,
    "pages": 1
  }
}
```

## Get Program

```http
GET /v1/programs/{program_id}
```

Returns the full program detail including nested category and eligibility data.

**Response includes:**
- All summary fields plus:
- `eligibility` — plain text eligibility
- `eligibility_json` — structured eligibility (income limits, age ranges, etc.)
- `how_to_apply` — step-by-step instructions
- `application_url`, `phone`, `email`, `address` — contact methods
- `source_url`, `source_type` — provenance
- `category` — nested category object

## Get Program History

```http
GET /v1/programs/{program_id}/history
```

Returns all historical versions of a program with computed diffs:

```json
{
  "data": [
    {
      "id": "uuid",
      "program_id": "uuid",
      "snapshot": { /* full program at this point */ },
      "diff": {
        "benefit_amount": "$600/month",
        "status": "active"
      },
      "changed_at": "2026-01-15T10:30:00Z"
    }
  ]
}
```

Diffs show exactly what changed between versions — useful for program monitoring.
---
sidebar_position: 2
---

# Extraction Pipeline

The extraction pipeline is the core engine of CivicOS. It transforms messy
government text into structured, queryable program data.

## How It Works

### 1. Input: Raw Text

From the scraper or PDF parser, we receive cleaned plain text:

```
Mayor's Office of Housing (MOH) is responsible for: housing the homeless,
developing affordable housing, and managing the City's real estate...
Seniors Save program helps seniors replace failing heating systems...
ONE+Boston offers the lowest fixed interest rates...
```

### 2. Mode Selection

| Condition | Mode |
|-----------|------|
| `ANTHROPIC_API_KEY` set and valid | **Claude** — LLM extraction |
| No API key or placeholder key | **Mock** — rule-based extraction |

### 3. Chunking

Documents >30,000 characters are split on paragraph boundaries:

```python
chunks = _chunk_text(raw_text)  # ["paragraph 1\n\nparagraph 2", ...]
```

Each chunk is extracted independently. Programs appearing in multiple chunks
are deduplicated by name, keeping the most complete version.

### 4. Claude Extraction (Production)

```python
EXTRACTION_SYSTEM_PROMPT = """
You are a civic data extraction specialist...
Return ONLY a valid JSON object. No markdown, no preamble.
"""
```

- **Temperature: 0.0** — deterministic output
- **Model: claude-sonnet-4-20250514** — best at structured extraction
- **Retry: 3 attempts** with exponential backoff for transient errors

### 5. Mock Extraction (Development)

Uses 20 regex patterns tuned for government benefit/housing page language.
Detects programs like "Seniors Save", "ONE+Boston", "Foreclosure Prevention"
and assigns categories, descriptions, and contact info.

### 6. Output

```json
{
  "programs": [
    {
      "name": "Seniors Save",
      "category": "housing",
      "description": "Helps seniors replace failing heating systems...",
      "benefit_amount": "varies",
      "is_ongoing": true,
      "languages": ["en"],
      "phone": "617-635-4200"
    }
  ]
}
```

## Adding New Extraction Patterns

To improve the mock extractor for a new city, add patterns to `mock_client.py`:

```python
PROGRAM_PATTERNS = [
    (
        r"(?i)(?:new\s*program\s*name)",  # case-insensitive regex
        {
            "category": "housing",
            "description": "What the program does",
            "is_ongoing": True,
        },
    ),
]
```

To improve Claude extraction, update the system prompt in `prompts.py` with
examples from the target city's language.
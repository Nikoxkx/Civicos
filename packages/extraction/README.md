# CivicOS Extraction — LLM & Rule-Based Program Extraction

**Extracts structured program data from raw scraped text.**

## Two Modes

### Claude Mode (Production)

When `ANTHROPIC_API_KEY` is set, uses `claude-sonnet-4-20250514` to extract
structured JSON from unstructured government text. Handles implicit eligibility
rules, benefit amounts, and nuance that rule-based systems miss.

### Mock Mode (Development / CI)

When no API key is set, falls back to rule-based extraction using keyword
matching and regex patterns tuned for government benefit/housing pages.
Catches ~70% of programs Claude would find — sufficient for testing pipeline
flow without API costs.

## Components

### `client.py` — Anthropic Claude API client

- Async client with exponential backoff retry
- Extracts JSON from Claude's markdown-wrapped responses
- Token usage logging for cost tracking
- Zero-temperature for deterministic extraction

### `mock_client.py` — Rule-based extraction (fallback)

- 20 keyword patterns targeting real Boston.gov programs
- Contact info extraction (phone, email, URLs)
- Category inference from keyword density

### `pipeline.py` — Orchestrator

- Auto-selects Claude or mock mode
- Chunks documents >30k chars on paragraph boundaries
- Deduplicates programs across chunks by name

### `prompts.py` — Claude system prompt

- Production-grade extraction prompt with explicit JSON schema
- Anti-hallucination rules
- Closed category enum

## Usage

```python
import asyncio
from packages.extraction.pipeline import ExtractionPipeline

async def main():
    pipeline = ExtractionPipeline()
    result = await pipeline.extract(scraped_text, source_url)
    for program in result["programs"]:
        print(f"{program['name']} ({program['category']})")

asyncio.run(main())
```

## Cost

Claude Sonnet extraction costs approximately:

- **~$0.003** per government web page (~15k chars)
- **~$0.15** to bootstrap a new city (50 pages × $0.003)
- **~$0.05/month** per city for weekly re-extraction (4 pages × $0.003)

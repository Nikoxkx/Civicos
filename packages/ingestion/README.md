# CivicOS Ingestion — Scraper & PDF Parser

**Scrapes government websites and PDFs for downstream extraction.**

## Components

### `scraper.py` — Web scraper

- **Fast path:** `httpx` for static HTML pages (no browser overhead)
- **Slow path:** `playwright` (headless Chromium) for JS-rendered SPAs
- **Auto-fallback:** if fast path returns <500 meaningful characters, falls back to Playwright
- Extracts cleaned plain text + preserves raw HTML

### `pdf_parser.py` — PDF text extractor

- Uses `pdfminer.six` with layout-aware parameters
- Handles multi-column layouts and vertical text
- Downloads PDF via httpx, extracts in memory

## Usage

```python
import asyncio
from packages.ingestion.scraper import scrape_url

async def main():
    # Scrape a web page
    result = await scrape_url("https://www.boston.gov/...", source_type="web")
    print(f"Text: {len(result['text'])} chars")
    print(f"HTML: {len(result['html'])} chars")

    # Scrape a PDF
    result = await scrape_url("https://www.boston.gov/...pdf", source_type="pdf")
    print(f"Pages: {result.get('page_count')}")
    print(f"Text: {result['text'][:500]}...")

asyncio.run(main())
```

## Output Schema

```python
{
    "url": str,
    "text": str,         # Cleaned plain text
    "html": str | None,  # Raw HTML (None for PDFs)
    "source_type": str,  # "web" | "pdf"
    "page_count": int | None,  # PDFs only
}
```

## Dependencies

- `httpx` — fast path HTTP client
- `playwright` — headless browser (install with `playwright install chromium`)
- `pdfminer.six` — PDF text extraction

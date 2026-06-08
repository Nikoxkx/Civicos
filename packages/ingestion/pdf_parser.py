"""
CivicOS Ingestion — PDF parser.

Extracts text from government PDFs (program guides, policy documents, etc.).
Uses pdfminer.six for text extraction with layout preservation.

Government PDFs are notoriously hard to parse — they often use multi-column
layouts, embedded tables, and scanned images. This module handles the
common cases:

1. Text-based PDFs → direct extraction with layout analysis
2. Scanned PDFs → (future: OCR via Tesseract — not yet implemented)

For now we focus on text-based PDFs, which cover ~80% of government documents.
"""

from __future__ import annotations

import io
from typing import Any

import httpx
import structlog
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams

logger = structlog.get_logger()


async def scrape_pdf(url: str) -> dict[str, Any]:
    """Download a PDF from a URL and extract its text content.

    Returns the same structure as scraper.scrape_url() for consistency.
    """
    logger.info("pdf_scrape_start", url=url)

    async with httpx.AsyncClient(
        timeout=60.0,  # PDFs can be large
        follow_redirects=True,
        headers={
            "User-Agent": "CivicOS/0.1 (civic data indexing bot)",
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            logger.warning("pdf_scrape_not_pdf", url=url, content_type=content_type)
            # Try extraction anyway — sometimes gov servers misreport content-type

        pdf_bytes = response.content

    # Extract text with layout-aware params
    laparams = LAParams(
        line_margin=0.5,     # Tolerance for grouping text lines
        char_margin=2.0,     # Tolerance for grouping characters into words
        word_margin=0.1,     # Tolerance for grouping words into lines
        boxes_flow=0.5,      # Tolerance for flowing text across columns
        detect_vertical=True, # Handle vertical text (rare but present in some gov docs)
    )

    text = extract_text(io.BytesIO(pdf_bytes), laparams=laparams)

    logger.info("pdf_scrape_complete", url=url, text_length=len(text))

    return {
        "url": url,
        "text": text,
        "html": None,  # PDFs have no HTML
        "source_type": "pdf",
        "page_count": _count_pages(pdf_bytes),
    }


def _count_pages(pdf_bytes: bytes) -> int:
    """Count pages in a PDF by scanning for page markers. Fallback only — not 100% reliable."""
    import re

    matches = re.findall(rb"/Type\s*/Page[^s]", pdf_bytes)
    return len(matches) or 1

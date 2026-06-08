"""
CivicOS Ingestion — Web scraper.

Handles both static HTML pages (via httpx) and JavaScript-rendered pages
(via Playwright). Returns cleaned text and raw HTML for downstream extraction.

Design decisions:
- We keep raw_html alongside extracted text because LLMs can sometimes infer
  structure from markup (tables, lists, definition lists) that plain text loses.
- Playwright is heavy (~100MB install). The fast path uses httpx for static
  pages. We fall back to Playwright only when the fast path returns < 500 chars
  of meaningful text (likely a JS-rendered SPA).
"""

from __future__ import annotations

import re
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# ── HTML cleaning regexes ────────────────────────────────────────────────
# We remove script/style tags before text extraction — their content is noise.
SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
# Whitespace normalization: collapse 3+ newlines into 2, strip trailing whitespace
WHITESPACE_RE = re.compile(r"\n{3,}")
TRAILING_WS_RE = re.compile(r"[ \t]+$", re.MULTILINE)


def _clean_html(html: str) -> str:
    """Strip script/style tags and normalize whitespace from HTML."""
    html = SCRIPT_RE.sub("", html)
    html = STYLE_RE.sub("", html)
    return html


def _html_to_text(html: str) -> str:
    """Extract human-readable text from HTML.

    This is intentionally simple — we're not trying to perfectly render the page.
    The LLM extraction step handles recovering structure from messy text.
    We remove obvious noise (scripts, styles), normalize whitespace, and strip
    leading/trailing blank lines.
    """
    cleaned = _clean_html(html)

    # Remove all remaining HTML tags — replace with space to avoid word collision
    text = re.sub(r"<[^>]+>", " ", cleaned)

    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&#039;", "'")
    text = text.replace("&apos;", "'")
    text = text.replace("&nbsp;", " ")

    # Normalize whitespace
    text = WHITESPACE_RE.sub("\n\n", text)
    lines = [TRAILING_WS_RE.sub("", line) for line in text.splitlines()]
    text = "\n".join(lines)

    # Strip blank lines at start/end
    return text.strip()


async def _scrape_with_httpx(url: str) -> tuple[str, str]:
    """Fast path: fetch with httpx for static HTML pages."""
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "CivicOS/0.1 (civic data indexing bot; "
                "https://github.com/civicos/civicos)"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*",
        },
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        text = _html_to_text(html)
        return text, html


async def _scrape_with_playwright(url: str) -> tuple[str, str]:
    """Slow path: use Playwright for JS-rendered pages (SPAs, React apps)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            text = _html_to_text(html)
        finally:
            await browser.close()

    return text, html


async def scrape_url(url: str, source_type: str = "web") -> dict[str, Any]:
    """Scrape a URL and return structured result.

    Args:
        url: The URL to scrape.
        source_type: One of 'web', 'pdf', 'rss'.

    Returns:
        A dict with keys: url, text, html, source_type, scraped_at.
    """
    logger.info("scrape_start", url=url, source_type=source_type)

    if source_type == "pdf":
        # PDF handling is in pdf_parser.py — this function handles routing
        from .pdf_parser import scrape_pdf

        return await scrape_pdf(url)

    # Try fast path first
    text, html = await _scrape_with_httpx(url)

    # If we got very little text, the page is likely a JS-rendered SPA.
    # Fall back to Playwright.
    meaningful_chars = len(re.sub(r"\s+", "", text))
    if meaningful_chars < 500:
        logger.info("scrape_fast_path_insufficient", url=url, chars=meaningful_chars)
        text, html = await _scrape_with_playwright(url)

    logger.info("scrape_complete", url=url, text_length=len(text))

    return {
        "url": url,
        "text": text,
        "html": html,
        "source_type": source_type,
    }

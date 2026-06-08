"""
CivicOS — Scraper unit tests.

Tests the HTML cleaning, text extraction, and URL validation logic
without network calls (mocking httpx/Playwright).
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from packages.ingestion.scraper import _clean_html, _html_to_text


class TestHtmlCleaning:
    """Tests for HTML → plain text extraction."""

    def test_strips_script_tags(self) -> None:
        html = "<html><script>alert('xss')</script><p>Hello</p></html>"
        result = _html_to_text(html)
        assert "alert" not in result
        assert "Hello" in result

    def test_strips_style_tags(self) -> None:
        html = "<html><style>.x {color:red}</style><p>Hello</p></html>"
        result = _html_to_text(html)
        assert "color" not in result
        assert "Hello" in result

    def test_decodes_entities(self) -> None:
        html = "<p>Housing &amp; Development</p>"
        result = _html_to_text(html)
        assert "&" in result
        assert "&amp;" not in result

    def test_normalizes_whitespace(self) -> None:
        html = "<p>Line one</p>\n\n\n\n<p>Line two</p>"
        result = _html_to_text(html)
        # Multiple blank lines should be collapsed
        assert "\n\n\n\n" not in result

    def test_empty_input(self) -> None:
        assert _html_to_text("") == ""
        assert _html_to_text("   ") == ""

    def test_strips_trailing_whitespace(self) -> None:
        html = "<p>Hello world   </p>"
        result = _html_to_text(html)
        assert not result.endswith("   ")

    def test_preserves_meaningful_content(self) -> None:
        html = """
        <html>
        <body>
            <h1>Housing Programs</h1>
            <p>Apply online at <a href="https://example.com">example.com</a></p>
            <p>Call 617-635-4200 for assistance.</p>
        </body>
        </html>
        """
        result = _html_to_text(html)
        assert "Housing Programs" in result
        assert "example.com" in result
        assert "617-635-4200" in result

    def test_handles_html_with_only_noise(self) -> None:
        """A page with only scripts and styles should produce near-empty text."""
        html = "<html><script>var x=1;</script><style>body{}</style></html>"
        result = _html_to_text(html)
        meaningful = result.strip()
        assert len(meaningful) < 20

    def test_apos_entity_decoded(self) -> None:
        html = "<p>Mayor&#039;s Office of Housing</p>"
        result = _html_to_text(html)
        assert "Mayor's" in result
        assert "&#039;" not in result


class TestScraperIntegration:
    """Light integration tests with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_scrape_web_page_mocked(self) -> None:
        """Test scrape_url with a mocked httpx response."""
        from packages.ingestion.scraper import scrape_url

        # Text long enough to avoid Playwright fallback (>500 meaningful chars)
        long_text = (
            "Housing Stability Services. " + "Boston MA resource information. " * 50 +
            "The Office of Housing Stability provides comprehensive support for " +
            "residents seeking affordable housing, rental assistance, and " +
            "foreclosure prevention. Call 617-635-4200 for more details."
        )

        with patch("packages.ingestion.scraper._scrape_with_httpx") as mock_scrape:
            mock_scrape.return_value = (long_text, "<html></html>")

            result = await scrape_url("https://example.com", source_type="web")

            assert result["url"] == "https://example.com"
            assert result["source_type"] == "web"
            assert "text" in result
            assert "html" in result

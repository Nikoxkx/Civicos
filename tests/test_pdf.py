"""
CivicOS — PDF parser unit tests.
"""

from __future__ import annotations

import pytest

from packages.ingestion.pdf_parser import _count_pages


class TestPageCount:
    """Tests for PDF page counting."""

    def test_empty_pdf(self) -> None:
        """An empty PDF should report at least 1 page (fallback)."""
        pages = _count_pages(b"")
        assert pages == 1

    def test_typical_pdf_page_count(self) -> None:
        """A PDF with /Type /Page references."""
        pdf = b"%PDF-1.4\n1 0 obj\n<</Type /Page /Parent 2 0 R>>\nendobj\n"
        pages = _count_pages(pdf)
        assert pages >= 1

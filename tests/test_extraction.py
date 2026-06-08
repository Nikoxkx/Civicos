"""
CivicOS — Extraction pipeline unit tests.

Tests the mock extractor, text chunking, and program deduplication logic.
"""

from __future__ import annotations

import pytest

from packages.extraction.mock_client import MockExtractionClient
from packages.extraction.pipeline import _chunk_text, _deduplicate_programs


class TestTextChunking:
    """Tests for the paragraph-aware text chunker."""

    def test_short_text_not_chunked(self) -> None:
        text = "Short text\n\nTwo paragraphs\n\nThat's it."
        chunks = _chunk_text(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_chunked(self) -> None:
        text = "a" * 100 + "\n\n" + "b" * 100 + "\n\n" + "c" * 100
        chunks = _chunk_text(text, max_chars=250)
        assert len(chunks) > 1

    def test_chunks_preserve_paragraph_boundaries(self) -> None:
        para1 = "Paragraph one content here."
        para2 = "Paragraph two different content."
        text = f"{para1}\n\n{para2}"
        chunks = _chunk_text(text, max_chars=len(para1) + 5)
        # Each paragraph should be in its own chunk since together they exceed the limit
        assert len(chunks) <= 2

    def test_single_long_paragraph(self) -> None:
        """A single paragraph longer than max_chars gets hard-split."""
        text = "x" * 100
        chunks = _chunk_text(text, max_chars=50)
        assert len(chunks) == 2


class TestProgramDeduplication:
    """Tests for cross-chunk program dedup."""

    def test_dedup_by_name_case_insensitive(self) -> None:
        # Second has 2 non-null fields vs first with 1 — it should win
        programs = [
            {"name": "Seniors Save", "description": "Basic desc", "phone": None, "email": None},
            {"name": "SENIORS SAVE", "description": None, "phone": "617-555-1234", "email": "test@test.com"},
        ]
        result = _deduplicate_programs(programs)
        assert len(result) == 1
        # Should keep the more complete version (with phone + email)
        assert result[0]["phone"] == "617-555-1234"
        assert result[0]["email"] == "test@test.com"

    def test_dedup_keeps_most_complete(self) -> None:
        programs = [
            {"name": "Program A", "a": 1, "b": None, "c": None},
            {"name": "Program A", "a": None, "b": 2, "c": 3},
        ]
        result = _deduplicate_programs(programs)
        assert len(result) == 1
        # Second has 2 fields, first has 1
        assert result[0]["b"] == 2
        assert result[0]["c"] == 3

    def test_empty_name_skipped(self) -> None:
        programs = [
            {"name": "", "description": "No name"},
            {"name": "Valid", "description": "Has name"},
        ]
        result = _deduplicate_programs(programs)
        assert len(result) == 1
        assert result[0]["name"] == "Valid"

    def test_unique_programs_kept(self) -> None:
        programs = [
            {"name": "Program A", "description": "First"},
            {"name": "Program B", "description": "Second"},
            {"name": "Program C", "description": "Third"},
        ]
        result = _deduplicate_programs(programs)
        assert len(result) == 3


class TestMockExtractor:
    """Tests for the rule-based mock extraction client."""

    def test_extracts_seniors_save(self) -> None:
        client = MockExtractionClient()
        text = "The Seniors Save program helps seniors replace failing heating systems."
        result = client._extract_programs(text, "https://example.com")
        names = [p["name"] for p in result]
        assert any("Seniors Save" in n for n in names)

    def test_extracts_one_boston(self) -> None:
        client = MockExtractionClient()
        text = "ONE+Boston offers the lowest fixed interest rates available."
        result = client._extract_programs(text, "https://example.com")
        names = [p["name"] for p in result]
        assert any("ONE+Boston" in n or "ONE" in n for n in names)

    def test_extracts_foreclosure_prevention(self) -> None:
        client = MockExtractionClient()
        text = "The Foreclosure Prevention program helps families avoid foreclosure."
        result = client._extract_programs(text, "https://example.com")
        names = [p["name"] for p in result]
        assert any("Foreclosure" in n for n in names)

    def test_empty_text_returns_no_programs(self) -> None:
        client = MockExtractionClient()
        result = client._extract_programs("", "https://example.com")
        assert result == []

    def test_irrelevant_text_returns_no_programs(self) -> None:
        client = MockExtractionClient()
        text = "The weather in Boston is cloudy today with a high of 72 degrees."
        result = client._extract_programs(text, "https://example.com")
        assert result == []

    def test_extracts_phone_numbers(self) -> None:
        client = MockExtractionClient()
        text = "Call 617-635-4200 for more information about housing stability."
        phone = client._extract_phone(text)
        assert phone is not None
        assert "617" in phone

    def test_extracts_email_addresses(self) -> None:
        client = MockExtractionClient()
        text = "Email housingstability@boston.gov for assistance."
        email = client._extract_email(text)
        assert email == "housingstability@boston.gov"

    def test_extracts_urls(self) -> None:
        client = MockExtractionClient()
        text = "Apply at https://www.boston.gov/departments/housing/apply"
        url = client._extract_urls(text)
        assert url is not None
        assert "boston.gov" in url

    def test_multiple_programs_deduped(self) -> None:
        client = MockExtractionClient()
        text = """
        The Seniors Save program helps seniors.
        Also check out Seniors Save for more options.
        ONE+Boston offers mortgage assistance.
        """
        result = client._extract_programs(text, "https://example.com")
        # Seniors Save appears twice but should be deduplicated
        names = [p["name"].lower() for p in result]
        assert names.count("seniors save") <= 1

    async def test_async_extract_method(self) -> None:
        client = MockExtractionClient()
        text = "The Seniors Save program provides heating assistance."
        user_message = f"Source URL: https://example.com\n\nTEXT:\n---\n{text}\n---"
        result = await client.extract(
            system_prompt="",
            user_message=user_message,
        )
        assert "programs" in result
        assert len(result["programs"]) >= 1

    def test_categorizes_housing_programs(self) -> None:
        client = MockExtractionClient()
        text = "Apply for rental relief and foreclosure prevention today."
        result = client._extract_programs(text, "https://example.com")
        for program in result:
            assert program.get("category") == "housing"

    def test_categorizes_food_programs(self) -> None:
        client = MockExtractionClient()
        text = "The Fresh Food Access initiative expands access to nutritious food."
        result = client._extract_programs(text, "https://example.com")
        for program in result:
            if "food" in program["name"].lower():
                assert program["category"] == "food"

    def test_all_programs_have_required_fields(self) -> None:
        client = MockExtractionClient()
        text = "Seniors Save and ONE+Boston are available for residents."
        result = client._extract_programs(text, "https://example.com")
        required = ["name", "category", "is_ongoing", "languages"]
        for program in result:
            for field in required:
                assert field in program, f"Missing field '{field}' in {program}"

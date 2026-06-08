"""
CivicOS Extraction — End-to-end extraction pipeline.

Orchestrates: raw scraped text → extraction → structured program data.
Auto-detects whether to use Claude API or rule-based mock extraction.

Design decisions:
- Chunking happens before extraction for long documents (>30k chars)
- Programs are deduplicated by name across chunks, keeping the most complete version
- Each chunk failure is isolated — one bad chunk doesn't lose all data
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from .prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE

logger = structlog.get_logger()

MAX_CHUNK_CHARS = 30_000


def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split text on paragraph boundaries to avoid cutting sentences."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > max_chars:
                current_chunk = para[:max_chars]
                chunks.append(current_chunk)
                current_chunk = para[max_chars:]
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _deduplicate_programs(programs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedup by name, keeping the version with more non-null fields."""
    seen: dict[str, dict[str, Any]] = {}

    for program in programs:
        name_key = program.get("name", "").strip().lower()
        if not name_key:
            continue

        if name_key in seen:
            existing_fields = sum(1 for v in seen[name_key].values() if v is not None and v != [])
            new_fields = sum(1 for v in program.values() if v is not None and v != [])
            if new_fields > existing_fields:
                seen[name_key] = program
        else:
            seen[name_key] = program

    return list(seen.values())


class ExtractionPipeline:
    """End-to-end pipeline: scrape text → extract programs → validate output.

    Auto-selects Claude extraction when ANTHROPIC_API_KEY is set,
    falls back to rule-based mock extraction for dev/CI.
    """

    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

        if api_key and not api_key.startswith("sk-ant-placeholder"):
            from .client import ClaudeExtractionClient

            self.client = ClaudeExtractionClient(api_key=api_key)
            self._use_claude = True
            logger.info("extraction_mode", mode="claude")
        else:
            from .mock_client import MockExtractionClient

            self.client = MockExtractionClient()
            self._use_claude = False
            logger.info("extraction_mode", mode="mock")

    async def extract(self, text: str, source_url: str) -> dict[str, Any]:
        """Extract structured programs from raw scraped text.

        Args:
            text: Raw text scraped from a government website or PDF.
            source_url: The source URL for context.

        Returns:
            ``{"programs": [...]}`` with structured program dicts.
        """
        logger.info("extraction_pipeline_start", url=source_url, text_length=len(text))

        if not text or len(text.strip()) < 50:
            logger.warning("extraction_insufficient_text", url=source_url)
            return {"programs": []}

        chunks = _chunk_text(text)
        logger.info("extraction_chunks", total_chunks=len(chunks))

        all_programs: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            user_message = EXTRACTION_USER_PROMPT_TEMPLATE.format(
                source_url=source_url, text=chunk
            )

            chunk_label = f" (chunk {i + 1}/{len(chunks)})" if len(chunks) > 1 else ""

            try:
                if self._use_claude:
                    result = await self.client.extract(
                        system_prompt=EXTRACTION_SYSTEM_PROMPT,
                        user_message=user_message,
                    )
                else:
                    result = await self.client.extract(
                        system_prompt="",
                        user_message=user_message,
                    )
                programs = result.get("programs", [])
                logger.info(f"extraction_chunk_complete{chunk_label}", programs_found=len(programs))
                all_programs.extend(programs)
            except Exception:
                logger.exception(f"extraction_chunk_failed{chunk_label}")
                continue

        unique_programs = _deduplicate_programs(all_programs)

        logger.info(
            "extraction_pipeline_complete",
            url=source_url,
            total_programs=len(unique_programs),
            before_dedup=len(all_programs),
        )

        return {"programs": unique_programs}

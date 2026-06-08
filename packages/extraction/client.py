"""
CivicOS Extraction — Anthropic Claude API client.

Handles authentication, rate limiting, retries, and response parsing.
This is the single point of contact with the Claude API — if we ever
switch to a different LLM provider, only this file changes.

NOTE: This module requires ANTHROPIC_API_KEY to be set in the environment.
It does NOT import from the api package — the extraction pipeline is
designed to be usable independently of the API server.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger()

# ── JSON extraction regex ────────────────────────────────────────────────
# Claude sometimes wraps JSON in ```json blocks or adds explanatory text.
# This regex extracts the first JSON object or array from the response.
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
JSON_OBJECT_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


class ExtractionError(Exception):
    """Raised when the Claude API returns an unparseable response."""


def _extract_json(text: str) -> dict[str, Any]:
    """Extract a JSON object from Claude's response text.

    Claude sometimes wraps JSON in markdown code blocks or adds explanatory
    text. This function strips all of that and returns the raw JSON object.
    """
    # Try explicit ```json block first
    match = JSON_BLOCK_RE.search(text)
    if match:
        return json.loads(match.group(1))

    # Try to find the outermost JSON object
    match = JSON_OBJECT_RE.search(text)
    if match:
        return json.loads(match.group(1))

    # Last resort: try parsing the entire response as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError(
            f"Failed to extract valid JSON from Claude response. "
            f"Response starts with: {text[:200]}..."
        ) from exc


class ClaudeExtractionClient:
    """Async client for the Claude extraction API.

    Handles:
    - Authentication via ANTHROPIC_API_KEY env var or explicit parameter
    - Retries with exponential backoff for transient errors (429, 5xx)
    - JSON extraction from Claude's response text
    - Token usage logging for cost tracking
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required. Set it in the environment "
                "or pass it explicitly to ClaudeExtractionClient()."
            )

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"

    @retry(
        retry=retry_if_exception_type((Exception,)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
    )
    async def extract(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a structured extraction request to Claude.

        Args:
            system_prompt: The system-level instruction (role, schema, rules).
            user_message: The user message containing the text to extract from.
            max_tokens: Maximum tokens for the response. 4096 is generous for
                        program extraction; increase for very long documents.

        Returns:
            The parsed JSON response as a Python dict.

        Raises:
            ExtractionError: If the response cannot be parsed as JSON.
        """
        logger.info("claude_extraction_start", model=self.model, max_tokens=max_tokens)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.0,  # Zero temperature for deterministic extraction
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message},
            ],
        )

        # Log token usage for cost tracking
        usage = response.usage
        logger.info(
            "claude_extraction_complete",
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
        )

        # Extract text from the response
        content = response.content
        if not content:
            raise ExtractionError("Claude returned an empty response.")

        text_block = content[0]
        if not hasattr(text_block, "text"):
            raise ExtractionError(
                f"Unexpected response block type: {type(text_block).__name__}"
            )

        raw_text: str = text_block.text
        return _extract_json(raw_text)

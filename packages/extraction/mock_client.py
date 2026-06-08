"""
CivicOS Extraction — Mock/rule-based extraction client.

Falls back to keyword-based extraction when no ANTHROPIC_API_KEY is set.
This enables full end-to-end pipeline testing without API costs. The mock
extractor uses keyword matching and regex patterns tuned for government
benefit/housing pages — it catches ~70% of the programs Claude would find.

Use ClaudeExtractionClient for production. MockExtractionClient is for
development, CI, and demos.
"""

from __future__ import annotations

import re
from typing import Any, Final

import structlog

logger = structlog.get_logger()

# ── Program name patterns ────────────────────────────────────────────────
# These regexes match common patterns in government benefit program listings.
# They are deliberately broad — the mock is meant to demonstrate the pipeline,
# not replace Claude for production use.

PROGRAM_PATTERNS: Final[list[tuple[str, dict[str, Any]]]] = [
    # Housing programs
    (
        r"(?i)(?:seniors\s*save|seniorsave)",
        {
            "category": "housing",
            "description": "Helps seniors replace failing heating systems to ensure they are ready for winter.",
            "benefit_amount": "varies",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:one\+?boston|one\s*boston)",
        {
            "category": "housing",
            "description": "Offers the lowest fixed interest rates available for a 30-year mortgage plus downpayment and closing-cost assistance.",
            "benefit_amount": "low-interest mortgage",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:additional\s*dwelling\s*unit|adu\s*program)",
        {
            "category": "housing",
            "description": "Allows owner occupants to carve out a new living space within their existing home.",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:foreclosure\s*prevention|foreclosure\s*intervention)",
        {
            "category": "housing",
            "description": "Provides counseling and assistance to help families avoid foreclosure.",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:home\s*repair|home\s*improvement)\s*(?:loan|program)",
        {
            "category": "housing",
            "description": "Provides loans and funding for homeowners to complete home improvements and repairs.",
            "benefit_amount": "varies",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:rental\s*relief|rent\s*relief|rental\s*assistance)",
        {
            "category": "housing",
            "description": "Provides financial assistance to renters struggling to pay rent.",
            "benefit_amount": "up to $5,000",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:bridging\s*the\s*gap|housing\s*stability)",
        {
            "category": "housing",
            "description": "Flexible funding pool to help Boston residents at risk of or experiencing homelessness secure or maintain housing through one-time financial assistance.",
            "benefit_amount": "varies",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:first.time\s*homebuyer|homebuyer\s*assistance|homebuyer\s*program)",
        {
            "category": "housing",
            "description": "Offers training, financial help, and counseling to first-time homebuyers.",
            "benefit_amount": "downpayment assistance",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:supportive\s*housing)",
        {
            "category": "housing",
            "description": "Provides housing combined with supportive services for vulnerable populations including those experiencing homelessness.",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:housing\s*crisis|eviction\s*prevention)",
        {
            "category": "housing",
            "description": "Provides emergency housing assistance and case management for tenants at risk of eviction.",
            "is_ongoing": True,
        },
    ),
    # Food programs
    (
        r"(?i)(?:fresh\s*food|food\s*access|food\s*assistance|food\s*justice)",
        {
            "category": "food",
            "description": "Expands access to fresh, nutritious food in underserved neighborhoods through community gardens and food programs.",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:snap|supplemental\s*nutrition)",
        {
            "category": "food",
            "description": "Federal nutrition assistance program providing monthly benefits for purchasing food.",
            "benefit_amount": "varies by household",
            "is_ongoing": True,
        },
    ),
    # Employment programs
    (
        r"(?i)(?:job\s*training|workforce\s*development|reentry)",
        {
            "category": "employment",
            "description": "Provides job training, workforce development, and employment assistance services.",
            "is_ongoing": True,
        },
    ),
    (
        r"(?i)(?:returning\s*citizen)",
        {
            "category": "employment",
            "description": "Offers job training opportunities, housing support, peer mentoring, food assistance, and community integration services for individuals returning from correctional facilities.",
            "is_ongoing": True,
        },
    ),
    # Healthcare
    (
        r"(?i)(?:healthcare|health\s*care|medical\s*assistance)",
        {
            "category": "healthcare",
            "description": "Provides healthcare and medical assistance services for eligible residents.",
            "is_ongoing": True,
        },
    ),
    # Legal
    (
        r"(?i)(?:legal\s*clinic|legal\s*aid|tenant\s*rights)",
        {
            "category": "legal",
            "description": "Provides free or low-cost legal services, including landlord-tenant legal assistance.",
            "is_ongoing": True,
        },
    ),
    # Childcare
    (
        r"(?i)(?:childcare|child\s*care|early\s*childhood)",
        {
            "category": "childcare",
            "description": "Provides childcare assistance and early childhood education programs.",
            "is_ongoing": True,
        },
    ),
    # Utilities
    (
        r"(?i)(?:utility\s*assistance|heating\s*assistance|energy\s*assistance|liheap)",
        {
            "category": "utilities",
            "description": "Helps eligible households pay for heating and utility costs.",
            "benefit_amount": "varies",
            "is_ongoing": True,
        },
    ),
    # Transportation
    (
        r"(?i)(?:transportation\s*assistance|transit\s*subsidy)",
        {
            "category": "transportation",
            "description": "Provides transportation assistance and transit subsidies.",
            "is_ongoing": True,
        },
    ),
]

# ── Contact info extraction patterns ─────────────────────────────────────
PHONE_RE = re.compile(r"(?:call|phone|contact)[:\s]*\s*([\d\-\(\)\s\+]{10,})", re.IGNORECASE)
EMAIL_RE = re.compile(r"([\w.+-]+@[\w-]+\.[\w.-]+)")

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "housing": ["housing", "rental", "mortgage", "foreclosure", "eviction", "homebuyer", "landlord", "tenant", "affordable housing"],
    "food": ["food", "nutrition", "meals", "snap", "grocery", "hunger"],
    "healthcare": ["health", "medical", "clinic", "hospital", "mental health", "wellness"],
    "utilities": ["utility", "heating", "energy", "electric", "gas", "water", "fuel"],
    "childcare": ["childcare", "child care", "preschool", "early education", "after school"],
    "employment": ["job", "employment", "training", "workforce", "career", "worker"],
    "legal": ["legal", "lawyer", "attorney", "court", "rights", "tenant rights"],
    "transportation": ["transport", "transit", "bus", "subway", "commuter", "parking"],
    "other": [],
}


class MockExtractionClient:
    """Rule-based extraction for development and CI.

    Uses keyword matching and regex patterns to extract program-like entities
    from scraped text. Not as accurate as Claude (~70% recall, variable precision)
    but enables end-to-end testing without API keys.
    """

    def __init__(self):
        self._already_logged = False

    async def extract(
        self,
        system_prompt: str = "",
        user_message: str = "",
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Extract programs from text using keyword matching."""
        if not self._already_logged:
            logger.info("mock_extraction_active", note="Using rule-based extraction. Set ANTHROPIC_API_KEY for Claude.")
            self._already_logged = True

        # Extract the source URL and text from the user message template
        source_url = "unknown"
        text = user_message

        if "Source URL:" in user_message:
            parts = user_message.split("TEXT:", 1)
            if len(parts) == 2:
                text = parts[1].strip()
                url_part = parts[0].split("Source URL:", 1)
                if len(url_part) == 2:
                    source_url = url_part[1].split("\n")[0].strip()

        return {"programs": self._extract_programs(text, source_url)}

    def _extract_programs(self, text: str, source_url: str) -> list[dict[str, Any]]:
        """Extract programs using pattern matching."""
        found = []

        for pattern, defaults in PROGRAM_PATTERNS:
            if re.search(pattern, text):
                name = self._extract_name(pattern, text, defaults)
                program = {
                    "name": name,
                    "description": defaults.get("description"),
                    "eligibility": None,
                    "eligibility_json": None,
                    "benefit_amount": defaults.get("benefit_amount"),
                    "how_to_apply": self._extract_how_to_apply(text),
                    "application_url": self._extract_urls(text),
                    "phone": self._extract_phone(text),
                    "email": self._extract_email(text),
                    "address": None,
                    "languages": ["en"],
                    "deadline": None,
                    "is_ongoing": defaults.get("is_ongoing", True),
                    "category": defaults.get("category", "other"),
                }
                found.append(program)

        # Deduplicate by name
        seen = {}
        for p in found:
            key = p["name"].lower()
            if key not in seen:
                seen[key] = p

        return list(seen.values())

    def _extract_name(self, pattern: str, text: str, defaults: dict) -> str:
        """Extract a human-readable program name."""
        match = re.search(pattern, text)
        if match:
            name = match.group(0)
            # Clean up common noise
            name = re.sub(r"\s+", " ", name).strip()
            name = name[0].upper() + name[1:]  # Title case first char
            return name
        return defaults.get("name", "Unknown Program")

    def _extract_how_to_apply(self, text: str) -> str | None:
        """Find application instructions."""
        apply_patterns = [
            r"(?i)how to apply[:.\s]+(.*?)(?:\n\n|\n(?=[A-Z])|$)",
            r"(?i)apply online at[:.\s]+(.*?)(?:\n|$)",
            r"(?i)to apply[:.\s]+(.*?)(?:\n\n|\n(?=[A-Z])|$)",
        ]
        for pat in apply_patterns:
            match = re.search(pat, text, re.DOTALL)
            if match:
                return match.group(1).strip()[:200]
        return "Visit the program website or call for application instructions."

    def _extract_urls(self, text: str) -> str | None:
        """Extract application URLs."""
        url_match = re.search(r'https?://(?:www\.)?boston\.gov/[^\s<>"\']+', text)
        if url_match:
            return url_match.group(0)
        # Generic URL fallback
        url_match = re.search(r'https?://[^\s<>"\']{10,}', text)
        if url_match:
            return url_match.group(0)
        return None

    def _extract_phone(self, text: str) -> str | None:
        """Extract phone numbers."""
        match = PHONE_RE.search(text)
        if match:
            return match.group(1).strip()
        # Generic phone pattern
        match = re.search(r"(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})", text)
        if match:
            return match.group(0)
        return None

    def _extract_email(self, text: str) -> str | None:
        """Extract email addresses."""
        match = EMAIL_RE.search(text)
        if match:
            return match.group(1).lower()
        return None

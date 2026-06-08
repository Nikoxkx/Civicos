"""
CivicOS API — Pydantic schemas for request/response serialization.

These are the "shape" of data entering and leaving the API. They are
deliberately separate from the SQLAlchemy models — this decouples the
database layer from the API contract, which means we can change the DB
schema without breaking API consumers (as long as we handle the mapping).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Shared ───────────────────────────────────────────────────────────────
class PaginationMeta(BaseModel):
    """Included in every list endpoint response."""
    total: int
    page: int
    limit: int
    pages: int  # total / limit, rounded up


class ErrorResponse(BaseModel):
    """Standard error envelope returned by all endpoints."""
    error: dict[str, str]  # { "code": "PROGRAM_NOT_FOUND", "message": "..." }


# ── City ──────────────────────────────────────────────────────────────────
class CityOut(BaseModel):
    id: UUID
    slug: str
    name: str
    state: str
    timezone: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CityListResponse(BaseModel):
    data: list[CityOut]
    meta: PaginationMeta


# ── Category ─────────────────────────────────────────────────────────────
class CategoryOut(BaseModel):
    id: int
    slug: str
    name: str
    icon: str | None = None

    model_config = {"from_attributes": True}


# ── Program ──────────────────────────────────────────────────────────────
class EligibilityJSON(BaseModel):
    """Structured eligibility data extracted by the LLM pipeline."""
    income_limit_percent_ami: float | None = None
    max_household_income: float | None = None
    household_size_min: int | None = None
    household_size_max: int | None = None
    citizenship_required: bool | None = None
    age_min: int | None = None
    age_max: int | None = None
    residency_required: bool | None = None
    other_requirements: list[str] = Field(default_factory=list)


class ProgramOut(BaseModel):
    """Full program representation returned by the API."""
    id: UUID
    city_id: UUID
    category_id: int
    name: str
    description: str | None = None
    eligibility: str | None = None
    eligibility_json: dict[str, Any] | None = None
    benefit_amount: str | None = None
    how_to_apply: str | None = None
    application_url: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    languages: list[str] | None = None
    deadline: date | None = None
    is_ongoing: bool = True
    status: str
    source_url: str
    source_type: str
    extracted_at: datetime | None = None
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Nested relations — only included on single-program lookups, not in lists
    category: CategoryOut | None = None

    model_config = {"from_attributes": True}


class ProgramSummary(BaseModel):
    """Lighter program representation for list endpoints (no nested relations)."""
    id: UUID
    city_id: UUID
    category_id: int
    name: str
    description: str | None = None
    benefit_amount: str | None = None
    status: str
    is_ongoing: bool = True
    languages: list[str] | None = None
    deadline: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgramListResponse(BaseModel):
    data: list[ProgramSummary]
    meta: PaginationMeta


class ProgramVersionOut(BaseModel):
    """A historical snapshot of a program at a point in time."""
    id: UUID
    program_id: UUID
    snapshot: dict[str, Any]
    diff: dict[str, Any] | None = None
    changed_at: datetime

    model_config = {"from_attributes": True}


class ProgramHistoryResponse(BaseModel):
    data: list[ProgramVersionOut]


# ── Source ───────────────────────────────────────────────────────────────
class SourceOut(BaseModel):
    id: UUID
    city_id: UUID
    url: str
    source_type: str
    scrape_frequency: str
    last_scraped_at: datetime | None = None
    last_status: str
    is_active: bool
    notes: str | None = None

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    """Request body for POST /v1/sources."""
    city_slug: str
    url: str
    source_type: str = "web"
    scrape_frequency: str = "weekly"
    notes: str | None = None


class IngestResponse(BaseModel):
    """Response from triggering a manual ingestion."""
    run_id: UUID
    source_id: UUID
    status: str
    message: str

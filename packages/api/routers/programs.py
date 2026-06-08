"""
CivicOS API — Programs router.

Endpoints:
    GET  /v1/programs         List programs with filters
    GET  /v1/programs/{id}    Get single program with full detail
    GET  /v1/programs/{id}/history  Version history for a program
    GET  /v1/search           Full-text search across programs
"""

from __future__ import annotations

import math
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .. import get_settings
from ..db import get_db
from ..models import Category, City, Program, ProgramVersion
from ..schemas import (
    ProgramHistoryResponse,
    ProgramListResponse,
    ProgramOut,
    ProgramSummary,
    ProgramVersionOut,
)

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()


def _program_to_summary(p: Program) -> ProgramSummary:
    """Map a Program ORM object to the lighter summary schema."""
    return ProgramSummary.model_validate(p)


def _program_to_detail(p: Program) -> ProgramOut:
    """Map a Program ORM object to full detail including nested relations."""
    return ProgramOut.model_validate(p)


@router.get(
    "/programs",
    response_model=ProgramListResponse,
    summary="List programs",
    description="List all programs with optional filters for city, category, language, and status.",
)
async def list_programs(
    city: str | None = Query(None, description="City slug (e.g. 'boston')"),
    category: str | None = Query(None, description="Category slug (e.g. 'housing')"),
    language: str | None = Query(None, description="Language code (e.g. 'es')"),
    status_filter: str | None = Query(None, alias="status", description="active, inactive, or all"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> ProgramListResponse:
    """List programs with filtering and pagination."""
    query = select(Program)

    # Build filters
    if city:
        city_subquery = select(City.id).where(City.slug == city).scalar_subquery()
        query = query.where(Program.city_id == city_subquery)

    if category:
        cat_subquery = select(Category.id).where(Category.slug == category).scalar_subquery()
        query = query.where(Program.category_id == cat_subquery)

    if language:
        query = query.where(Program.languages.any(language))  # type: ignore[arg-type]

    if status_filter and status_filter != "all":
        query = query.where(Program.status == status_filter)
    elif status_filter != "all":
        # Default: only active programs
        query = query.where(Program.status == "active")

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total: int = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(Program.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    programs = result.scalars().all()

    return ProgramListResponse(
        data=[_program_to_summary(p) for p in programs],
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 0,
        },
    )


@router.get(
    "/programs/{program_id}",
    response_model=ProgramOut,
    summary="Get a program",
    responses={404: {"description": "Program not found"}},
)
async def get_program(
    program_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProgramOut:
    """Get a single program by ID, including its category and full detail."""
    query = (
        select(Program)
        .options(joinedload(Program.category), joinedload(Program.city))
        .where(Program.id == program_id)
    )
    result = await db.execute(query)
    program = result.unique().scalar_one_or_none()

    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PROGRAM_NOT_FOUND",
                    "message": f"No program found with id {program_id}",
                }
            },
        )

    return _program_to_detail(program)


@router.get(
    "/programs/{program_id}/history",
    response_model=ProgramHistoryResponse,
    summary="Program version history",
    responses={404: {"description": "Program not found"}},
)
async def get_program_history(
    program_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProgramHistoryResponse:
    """Get the version history of a program, showing how it has changed over time."""
    # Verify the program exists
    program = await db.get(Program, program_id)
    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PROGRAM_NOT_FOUND",
                    "message": f"No program found with id {program_id}",
                }
            },
        )

    query = (
        select(ProgramVersion)
        .where(ProgramVersion.program_id == program_id)
        .order_by(ProgramVersion.changed_at.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()

    return ProgramHistoryResponse(
        data=[ProgramVersionOut.model_validate(v) for v in versions]
    )


@router.get(
    "/search",
    response_model=ProgramListResponse,
    summary="Full-text search programs",
    description=(
        "Search across program names, descriptions, and eligibility text "
        "using PostgreSQL full-text search."
    ),
)
async def search_programs(
    q: str = Query(..., min_length=2, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ProgramListResponse:
    """Full-text search across programs using PostgreSQL tsvector."""
    search_vec = literal_column("programs.search_vector")
    tsquery = func.plainto_tsquery("english", q)

    query = (
        select(Program)
        .where(Program.status == "active")
        .where(search_vec.op("@@")(tsquery))
        .order_by(func.ts_rank(search_vec, tsquery).desc())
    )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    programs = result.scalars().all()

    return ProgramListResponse(
        data=[_program_to_summary(p) for p in programs],
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 0,
        },
    )

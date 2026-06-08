"""
CivicOS API — Cities router.

Endpoints:
    GET  /v1/cities              List covered cities
    GET  /v1/cities/{slug}/programs  Programs for a specific city
"""

from __future__ import annotations

import math

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import City, Program
from ..schemas import CityListResponse, CityOut, ProgramListResponse, ProgramSummary

logger = structlog.get_logger()
router = APIRouter()


@router.get(
    "/cities",
    response_model=CityListResponse,
    summary="List cities",
)
async def list_cities(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> CityListResponse:
    """List all cities currently covered by CivicOS."""
    count_query = select(func.count()).select_from(City)
    total = (await db.execute(count_query)).scalar_one()

    offset = (page - 1) * limit
    query = select(City).order_by(City.name).offset(offset).limit(limit)
    result = await db.execute(query)
    cities = result.scalars().all()

    return CityListResponse(
        data=[CityOut.model_validate(c) for c in cities],
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 0,
        },
    )


@router.get(
    "/cities/{slug}",
    response_model=CityOut,
    summary="Get a city",
    responses={404: {"description": "City not found"}},
)
async def get_city(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> CityOut:
    """Get a city by its slug."""
    result = await db.execute(select(City).where(City.slug == slug))
    city = result.scalar_one_or_none()

    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "message": f"No city found with slug '{slug}'",
                }
            },
        )

    return CityOut.model_validate(city)


@router.get(
    "/cities/{slug}/programs",
    response_model=ProgramListResponse,
    summary="List programs for a city",
)
async def list_city_programs(
    slug: str,
    category: str | None = Query(None, description="Filter by category slug"),
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ProgramListResponse:
    """List all programs for a specific city, with optional category filter."""
    # Resolve city slug to ID
    city_result = await db.execute(select(City.id).where(City.slug == slug))
    city_id = city_result.scalar_one_or_none()

    if city_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "message": f"No city found with slug '{slug}'",
                }
            },
        )

    # Build program query
    query = select(Program).where(Program.city_id == city_id)

    if category:
        from ..models import Category
        cat_subquery = select(Category.id).where(Category.slug == category).scalar_subquery()
        query = query.where(Program.category_id == cat_subquery)

    if status_filter and status_filter != "all":
        query = query.where(Program.status == status_filter)
    elif status_filter != "all":
        query = query.where(Program.status == "active")

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * limit
    query = query.order_by(Program.name).offset(offset).limit(limit)

    result = await db.execute(query)
    programs = result.scalars().all()

    return ProgramListResponse(
        data=[ProgramSummary.model_validate(p) for p in programs],
        meta={
            "total": total,
            "page": page,
            "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 0,
        },
    )

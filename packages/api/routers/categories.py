"""
CivicOS API — Categories router.

Endpoint:
    GET  /v1/categories   List all program categories
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Category
from ..schemas import CategoryOut

logger = structlog.get_logger()
router = APIRouter()


@router.get(
    "/categories",
    response_model=list[CategoryOut],
    summary="List categories",
    description="Returns all program categories (housing, food, healthcare, etc.).",
)
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[CategoryOut]:
    """List all program categories. This endpoint is not paginated — there are ~10."""
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()

    return [CategoryOut.model_validate(c) for c in categories]

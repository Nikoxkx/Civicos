"""
CivicOS API — Sources router (admin endpoints).

Endpoints:
    POST /v1/sources          Add a new data source
    POST /v1/ingest/{source_id}  Trigger manual ingestion for a source
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import City, IngestionRun, Source
from ..schemas import IngestResponse, SourceCreate, SourceOut

logger = structlog.get_logger()
router = APIRouter()


@router.post(
    "/sources",
    response_model=SourceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a data source",
    description="Register a new URL to be scraped and ingested.",
)
async def create_source(
    body: SourceCreate,
    db: AsyncSession = Depends(get_db),
) -> SourceOut:
    """Create a new data source for a city."""
    # Resolve city slug
    result = await db.execute(select(City).where(City.slug == body.city_slug))
    city = result.scalar_one_or_none()

    if city is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "CITY_NOT_FOUND",
                    "message": f"No city found with slug '{body.city_slug}'",
                }
            },
        )

    # Check for duplicate URL
    existing = await db.execute(
        select(Source).where(Source.url == body.url, Source.city_id == city.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "SOURCE_EXISTS",
                    "message": f"A source with URL '{body.url}' already exists for this city",
                }
            },
        )

    source = Source(
        city_id=city.id,
        url=body.url,
        source_type=body.source_type,
        scrape_frequency=body.scrape_frequency,
        notes=body.notes,
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    logger.info("source_created", source_id=str(source.id), url=body.url)

    return SourceOut.model_validate(source)


@router.post(
    "/ingest/{source_id}",
    response_model=IngestResponse,
    summary="Trigger ingestion",
    description="Manually trigger scraping and extraction for a data source.",
)
async def trigger_ingestion(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Trigger a manual ingestion run for a specific source.

    In production, this would be a background task or dispatched to a worker queue.
    For now, we run it synchronously (acceptable for single-source ingestion).
    """
    # Verify source exists
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "SOURCE_NOT_FOUND",
                    "message": f"No source found with id {source_id}",
                }
            },
        )

    if not source.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SOURCE_INACTIVE",
                    "message": f"Source {source_id} is inactive. Reactivate it before ingesting.",
                }
            },
        )

    # Create ingestion run record
    run = IngestionRun(
        source_id=source.id,
        status="started",
    )
    db.add(run)
    await db.flush()

    # ── Actual ingestion happens here ────────────────────────────────────
    # In production: dispatch to a Celery/RQ/background task.
    # For now: import and run the pipeline inline.
    try:
        from extraction.pipeline import ExtractionPipeline
        from ingestion.scraper import scrape_url

        logger.info("ingestion_started", run_id=str(run.id), url=source.url)

        # 1. Scrape
        scraped = await scrape_url(source.url, source.source_type)
        run.status = "scraped"
        run.programs_found = 0  # Will be updated after extraction
        db.add(run)
        await db.flush()

        # 2. Extract with Claude
        pipeline = ExtractionPipeline()
        extracted = await pipeline.extract(scraped["text"], source.url)

        run.status = "extracted"
        run.programs_found = len(extracted.get("programs", []))
        db.add(run)

        # 3. Store programs
        new_count = 0
        updated_count = 0

        for program_data in extracted.get("programs", []):
            # Check if this program already exists (by source_url + name)
            existing = await db.execute(
                select(Program).where(
                    Program.source_url == source.url,
                    Program.name == program_data["name"],
                )
            )
            existing_program = existing.scalar_one_or_none()

            if existing_program:
                # Update existing program
                for key, value in program_data.items():
                    if key in ("category", "eligibility_json"):
                        continue  # Handled separately
                    if hasattr(existing_program, key):
                        setattr(existing_program, key, value)

                # Resolve category
                cat_slug = program_data.get("category", "other")
                cat_result = await db.execute(
                    select(Category).where(Category.slug == cat_slug)
                )
                cat = cat_result.scalar_one_or_none()
                if cat:
                    existing_program.category_id = cat.id

                existing_program.last_checked_at = datetime.now(timezone.utc)
                updated_count += 1
            else:
                # Create new program
                cat_slug = program_data.get("category", "other")
                cat_result = await db.execute(
                    select(Category).where(Category.slug == cat_slug)
                )
                cat = cat_result.scalar_one_or_none()
                category_id = cat.id if cat else 9  # 9 = "other"

                new_program = Program(
                    city_id=source.city_id,
                    category_id=category_id,
                    name=program_data["name"],
                    description=program_data.get("description"),
                    eligibility=program_data.get("eligibility"),
                    eligibility_json=program_data.get("eligibility_json"),
                    benefit_amount=program_data.get("benefit_amount"),
                    how_to_apply=program_data.get("how_to_apply"),
                    application_url=program_data.get("application_url"),
                    phone=program_data.get("phone"),
                    email=program_data.get("email"),
                    address=program_data.get("address"),
                    languages=program_data.get("languages", ["en"]),
                    deadline=program_data.get("deadline"),
                    is_ongoing=program_data.get("is_ongoing", True),
                    status="active",
                    source_url=source.url,
                    source_type=source.source_type,
                    raw_text=scraped["text"],
                    raw_html=scraped.get("html"),
                )
                db.add(new_program)
                new_count += 1

        run.status = "stored"
        run.programs_new = new_count
        run.programs_updated = updated_count
        run.completed_at = datetime.now(timezone.utc)

        # Update source metadata
        source.last_scraped_at = datetime.now(timezone.utc)
        source.last_status = "success"
        source.last_error = None

        await db.flush()

        logger.info(
            "ingestion_complete",
            run_id=str(run.id),
            new=new_count,
            updated=updated_count,
        )

        return IngestResponse(
            run_id=run.id,
            source_id=source.id,
            status="stored",
            message=(
                f"Successfully ingested {new_count} new and updated "
                f"{updated_count} existing programs."
            ),
        )

    except Exception as e:
        # Log the error and update the run
        logger.exception("ingestion_failed", run_id=str(run.id), error=str(e))

        run.status = "error"
        run.error_message = str(e)
        run.completed_at = datetime.now(timezone.utc)

        source.last_scraped_at = datetime.now(timezone.utc)
        source.last_status = "error"
        source.last_error = str(e)

        await db.flush()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INGESTION_FAILED",
                    "message": f"Ingestion failed: {e!s}",
                }
            },
        ) from e


# Import at bottom to avoid circular import
from ..models import Category, Program

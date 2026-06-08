"""
CivicOS CLI — ``civicos`` command.

Usage::

    civicos ingest --city boston
    civicos scrape --url https://www.boston.gov/departments/housing/...
    civicos serve
    civicos seed
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="civicos")
def main() -> None:
    """CivicOS — Open-source civic data intelligence platform.

    Ingests government benefit data, extracts structured info,
    and serves it via REST API.
    """


@main.command()
@click.option("--city", "-c", default="boston", help="City slug to ingest data for")
@click.option("--source-id", "-s", default=None, help="Specific source ID to ingest")
def ingest(city: str, source_id: str | None) -> None:
    """Scrape and extract programs for a city."""
    click.echo(f"Starting ingestion for city: {city}")

    async def _run() -> None:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from packages.api.db import async_session_factory
        from packages.api.models import Category, City, Program, Source
        from packages.extraction.pipeline import ExtractionPipeline
        from packages.ingestion.scraper import scrape_url

        async with async_session_factory() as db:
            result = await db.execute(select(City).where(City.slug == city))
            city_obj = result.scalar_one_or_none()

            if not city_obj:
                click.echo(
                    f"Error: City '{city}' not found. Run 'civicos seed' first.",
                    err=True,
                )
                return

            query = select(Source).where(
                Source.city_id == city_obj.id, Source.is_active.is_(True)
            )
            if source_id:
                query = query.where(Source.id == source_id)
            result = await db.execute(query)
            sources = result.scalars().all()

            if not sources:
                click.echo(
                    f"No active sources found for {city}. "
                    "Add sources via the API.",
                    err=True,
                )
                return

            pipeline = ExtractionPipeline()

            for source in sources:
                click.echo(f"  Scraping: {source.url}")
                scraped = await scrape_url(source.url, source.source_type)
                click.echo(
                    f"  Extracted {len(scraped['text'])} characters of text"
                )

                click.echo("  Extracting programs...")
                extracted = await pipeline.extract(scraped["text"], source.url)
                programs = extracted.get("programs", [])
                click.echo(f"  Found {len(programs)} programs")

                new_count = 0
                for pdata in programs:
                    existing = await db.execute(
                        select(Program).where(
                            Program.source_url == source.url,
                            Program.name == pdata["name"],
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    cat_slug = pdata.get("category", "other")
                    cat_result = await db.execute(
                        select(Category).where(Category.slug == cat_slug)
                    )
                    cat = cat_result.scalar_one_or_none()
                    category_id = cat.id if cat else 9

                    program = Program(
                        city_id=city_obj.id,
                        category_id=category_id,
                        name=pdata["name"],
                        description=pdata.get("description"),
                        eligibility=pdata.get("eligibility"),
                        eligibility_json=pdata.get("eligibility_json"),
                        benefit_amount=pdata.get("benefit_amount"),
                        how_to_apply=pdata.get("how_to_apply"),
                        application_url=pdata.get("application_url"),
                        phone=pdata.get("phone"),
                        email=pdata.get("email"),
                        address=pdata.get("address"),
                        languages=pdata.get("languages", ["en"]),
                        deadline=pdata.get("deadline"),
                        is_ongoing=pdata.get("is_ongoing", True),
                        status="active",
                        source_url=source.url,
                        source_type=source.source_type,
                        raw_text=scraped["text"],
                        raw_html=scraped.get("html"),
                    )
                    db.add(program)
                    new_count += 1

                source.last_scraped_at = datetime.now(timezone.utc)
                source.last_status = "success"
                click.echo(f"  Stored {new_count} new programs")
                click.echo()

            await db.commit()
            click.echo("Done! Run 'civicos serve' to start the API.")

    asyncio.run(_run())


@main.command()
@click.option("--url", "-u", required=True, help="URL to scrape")
@click.option(
    "--type",
    "-t",
    "source_type",
    default="web",
    help="Source type: web, pdf, rss",
)
def scrape(url: str, source_type: str) -> None:
    """Scrape a URL and show extracted text."""

    async def _run() -> None:
        from packages.ingestion.scraper import scrape_url

        click.echo(f"Scraping: {url}")
        result = await scrape_url(url, source_type)
        click.echo(f"Source type: {result['source_type']}")
        click.echo(f"Text length: {len(result['text'])} chars")
        click.echo("--- First 1000 characters ---")
        click.echo(result["text"][:1000])
        click.echo("--- End preview ---")

    asyncio.run(_run())


@main.command()
@click.option("--url", "-u", required=True, help="URL to scrape and extract from")
def extract(url: str) -> None:
    """Scrape a URL and run the full extraction pipeline."""

    async def _run() -> None:
        from packages.extraction.pipeline import ExtractionPipeline
        from packages.ingestion.scraper import scrape_url

        click.echo(f"1. Scraping: {url}")
        scraped = await scrape_url(url, "web")

        click.echo("2. Extracting programs...")
        pipeline = ExtractionPipeline()
        result = await pipeline.extract(scraped["text"], url)

        programs = result.get("programs", [])
        click.echo(f"3. Found {len(programs)} programs:\n")

        for p in programs:
            click.echo(f"  🏷  {p.get('name', 'Unknown')}")
            click.echo(f"     Category: {p.get('category', 'N/A')}")
            if p.get("description"):
                desc = p["description"]
                click.echo(f"     Description: {desc[:120]}...")
            if p.get("phone"):
                click.echo(f"     Phone: {p['phone']}")
            if p.get("email"):
                click.echo(f"     Email: {p['email']}")
            click.echo()

    asyncio.run(_run())


@main.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to bind to")
def serve(host: str, port: int) -> None:
    """Start the CivicOS API server."""
    import uvicorn

    click.echo(f"Starting CivicOS API on http://{host}:{port}")
    click.echo(f"Docs: http://{host}:{port}/docs")
    uvicorn.run("packages.api.main:app", host=host, port=port, reload=True)


@main.command()
def seed() -> None:
    """Seed the database with cities and categories."""
    import asyncio

    from sqlalchemy import text

    from packages.api.db import async_session_factory

    async def _run() -> None:
        migrations_dir = Path(__file__).parent.parent / "db" / "migrations"
        async with async_session_factory() as db:
            for sql_file in sorted(migrations_dir.glob("*.sql")):
                click.echo(f"  Running: {sql_file.name}")
                sql = sql_file.read_text()
                await db.execute(text(sql))
            await db.commit()
            click.echo("Seed complete!")

    asyncio.run(_run())


if __name__ == "__main__":
    main()

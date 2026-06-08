#!/usr/bin/env python3
"""
CivicOS — End-to-End Demo Script
=================================
Runs the full pipeline: scrape → extract → store → serve.
Generates a report showing every program found and the API responses.

Usage:
    python demo.py                    # Run with local PostgreSQL
    python demo.py --scrape-only      # Only scrape (no DB needed)
    python demo.py --db-url URL       # Custom database URL

Requirements:
    - PostgreSQL running (or --scrape-only)
    - All dependencies installed (pip install -e ".[dev]")
    - Playwright browsers installed (playwright install chromium)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure the project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Config ───────────────────────────────────────────────────────────────
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://civicos:civicos_dev@localhost:5432/civicos",
)

# Test URLs — real Boston.gov pages with benefit program content
DEMO_SOURCES = [
    {
        "url": "https://www.boston.gov/departments/housing/our-work-neighborhood-development",
        "type": "web",
        "name": "Mayor's Office of Housing — Programs & Services",
    },
    {
        "url": "https://www.boston.gov/departments/participatory-budgeting/bridging-gap-assistance-housing-stability",
        "type": "web",
        "name": "Bridging the Gap — Housing Stability Assistance",
    },
    {
        "url": "https://www.boston.gov/sites/default/files/file/2020/08/OHS%20Fact%20Sheet,%20English.pdf",
        "type": "pdf",
        "name": "Office of Housing Stability — Fact Sheet (PDF)",
    },
]

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                    CIVICOS DEMO                               ║
║  Open-Source Civic Data Intelligence Platform                ║
║  Scrape → Extract → Store → Serve                            ║
╚══════════════════════════════════════════════════════════════╝
"""

SEPARATOR = "─" * 70


def print_header(title: str) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(f"{SEPARATOR}")


def print_program(p: dict, index: int) -> None:
    """Print a single program in a formatted way."""
    cat_emojis = {
        "housing": "🏠", "food": "🍎", "healthcare": "🏥",
        "utilities": "⚡", "childcare": "🧒", "employment": "💼",
        "legal": "⚖️", "transportation": "🚌", "other": "📋",
    }
    cat = p.get("category", "other")
    emoji = cat_emojis.get(cat, "📋")

    print(f"""
  {emoji}  Program #{index}: {p.get('name', 'Unknown')}
  {' ' * 4}Category:     {cat}
  {' ' * 4}Ongoing:      {'✅ Yes' if p.get('is_ongoing') else '❌ No'}
  {' ' * 4}Languages:    {', '.join(p.get('languages', ['en']))}""")

    if p.get("description"):
        desc = p["description"]
        print(f"  {' ' * 4}Description:  {desc[:150]}{'...' if len(desc) > 150 else ''}")

    if p.get("benefit_amount"):
        print(f"  {' ' * 4}Benefit:      {p['benefit_amount']}")

    if p.get("phone"):
        print(f"  {' ' * 4}Phone:        {p['phone']}")

    if p.get("email"):
        print(f"  {' ' * 4}Email:        {p['email']}")

    if p.get("application_url"):
        print(f"  {' ' * 4}Apply:        {p['application_url']}")


async def demo_scrape_only() -> dict:
    """Run just the scraping phase — no database needed."""
    from packages.ingestion.scraper import scrape_url

    results = {}
    print_header("PHASE 1: Scraping Government Data Sources")

    for i, source in enumerate(DEMO_SOURCES, 1):
        print(f"\n  [{i}/{len(DEMO_SOURCES)}] {source['name']}")
        print(f"       URL: {source['url']}")

        try:
            result = await scrape_url(source["url"], source["type"])
            text_len = len(result["text"])
            print(f"       ✅ Extracted {text_len:,} characters")
            results[source["url"]] = result
        except Exception as e:
            print(f"       ❌ Failed: {e}")
            results[source["url"]] = None

    return results


async def demo_extraction(scraped: dict) -> list:
    """Run extraction on scraped data."""
    from packages.extraction.pipeline import ExtractionPipeline

    print_header("PHASE 2: Extracting Structured Program Data")

    pipeline = ExtractionPipeline()
    all_programs = []

    for url, data in scraped.items():
        if data is None:
            continue

        source_name = next((s["name"] for s in DEMO_SOURCES if s["url"] == url), url)
        print(f"\n  📄 Source: {source_name}")
        print(f"     Text length: {len(data['text']):,} chars")

        result = await pipeline.extract(data["text"], url)
        programs = result.get("programs", [])

        if programs:
            print(f"     ✅ Found {len(programs)} programs:")
            for i, p in enumerate(programs, 1):
                print_program(p, i)
                all_programs.append({"source_url": url, **p})
        else:
            print(f"     ⚠️  No programs detected in this source")

    return all_programs


async def demo_store(all_programs: list) -> dict:
    """Store extracted programs in the database."""
    from packages.api.db import async_session_factory
    from packages.api.models import City, Program, Category, Source
    from packages.api import get_settings
    from sqlalchemy import select
    from datetime import datetime, timezone

    print_header("PHASE 3: Storing in PostgreSQL")

    settings = get_settings()
    print(f"  Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'localhost'}")

    async with async_session_factory() as db:
        # Get Boston city
        result = await db.execute(select(City).where(City.slug == "boston"))
        city = result.scalar_one_or_none()

        if not city:
            print("  ⚠️  Boston not in database. Run seed data first.")
            return {"new": 0, "updated": 0}

        new_count = 0
        updated_count = 0

        for pdata in all_programs:
            # Check if program exists by name + source_url
            existing = await db.execute(
                select(Program).where(
                    Program.source_url == pdata["source_url"],
                    Program.name == pdata["name"],
                )
            )
            existing_program = existing.scalar_one_or_none()

            # Resolve category
            cat_slug = pdata.get("category", "other")
            cat_result = await db.execute(select(Category).where(Category.slug == cat_slug))
            cat = cat_result.scalar_one_or_none()
            category_id = cat.id if cat else 9

            if existing_program:
                # Update
                for key in ("description", "benefit_amount", "how_to_apply",
                            "phone", "email", "languages", "is_ongoing", "status"):
                    if key in pdata and hasattr(existing_program, key):
                        setattr(existing_program, key, pdata[key])
                existing_program.last_checked_at = datetime.now(timezone.utc)
                updated_count += 1
            else:
                # Insert
                program = Program(
                    city_id=city.id,
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
                    source_url=pdata["source_url"],
                    source_type="web",
                )
                db.add(program)
                new_count += 1

        await db.commit()
        print(f"  ✅ {new_count} new programs inserted")
        print(f"  ✅ {updated_count} programs updated")
        return {"new": new_count, "updated": updated_count}


async def demo_api_verify() -> dict:
    """Verify the API returns the stored data."""
    from packages.api.main import app
    from httpx import ASGITransport, AsyncClient

    print_header("PHASE 4: Verifying API Responses")

    results = {}
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        r = await client.get("/health")
        results["health"] = r.status_code == 200
        print(f"  GET /health              → {r.status_code} {'✅' if results['health'] else '❌'}")

        # Categories
        r = await client.get("/v1/categories")
        cats = r.json()
        results["categories"] = len(cats)
        print(f"  GET /v1/categories       → {len(cats)} categories {'✅' if len(cats) == 9 else '⚠️'}")

        # Cities
        r = await client.get("/v1/cities")
        cities = r.json()
        results["cities"] = cities["meta"]["total"]
        print(f"  GET /v1/cities           → {cities['meta']['total']} city {'✅' if cities['meta']['total'] >= 1 else '⚠️'}")

        # Programs
        r = await client.get("/v1/programs")
        progs = r.json()
        results["programs"] = progs["meta"]["total"]
        print(f"  GET /v1/programs         → {progs['meta']['total']} programs {'✅' if progs['meta']['total'] > 0 else '⚠️ (empty)'}")

        # Housing programs
        r = await client.get("/v1/programs", params={"category": "housing"})
        housing = r.json()
        results["housing"] = housing["meta"]["total"]
        print(f"  GET /v1/programs?category=housing → {housing['meta']['total']} housing programs")

        # Boston city detail
        r = await client.get("/v1/cities/boston")
        city = r.json()
        results["city_detail"] = city["name"]
        print(f"  GET /v1/cities/boston    → {city['name']}, {city['state']} {'✅' if city['name'] == 'Boston' else '❌'}")

        # Search
        r = await client.get("/v1/search", params={"q": "housing"})
        search = r.json()
        results["search"] = search["meta"]["total"]
        print(f"  GET /v1/search?q=housing → {search['meta']['total']} results")

    return results


def save_report(scraped: dict, programs: list, store: dict, api: dict) -> None:
    """Save a JSON report of the demo run."""
    report = {
        "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
        "sources_scraped": len([v for v in scraped.values() if v is not None]),
        "total_programs_found": len(programs),
        "programs_stored_new": store.get("new", 0),
        "programs_updated": store.get("updated", 0),
        "api_verification": api,
        "programs": [
            {
                "name": p.get("name"),
                "category": p.get("category"),
                "description": (p.get("description") or "")[:200],
                "benefit_amount": p.get("benefit_amount"),
                "is_ongoing": p.get("is_ongoing"),
            }
            for p in programs
        ],
    }

    report_path = PROJECT_ROOT / "demo_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  📄 Full report saved to: {report_path}")


async def main(scrape_only: bool = False) -> None:
    print(BANNER)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Mode: {'Scrape + Extract only' if scrape_only else 'Full pipeline (scrape → extract → store → serve)'}")

    # Phase 1: Scrape
    scraped = await demo_scrape_only()

    if scrape_only:
        print_header("DONE (--scrape-only)")
        total_chars = sum(len(d["text"]) for d in scraped.values() if d)
        print(f"  Scraped {len(scraped)} sources, {total_chars:,} total characters")
        return

    # Phase 2: Extract
    programs = await demo_extraction(scraped)

    if not programs:
        print_header("DONE (no programs found)")
        return

    # Phase 3: Store
    try:
        store = await demo_store(programs)
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        print(f"  ⚠️  Skipping store phase. Run 'civicos seed' to set up the database.")
        store = {"new": 0, "updated": 0}

    # Phase 4: API verification
    try:
        api = await demo_api_verify()
    except Exception as e:
        print(f"  ⚠️  API verification failed: {e}")
        api = {}

    # Save report
    save_report(scraped, programs, store, api)

    # Summary
    print_header("DEMO COMPLETE")
    print(f"""
  📊 Summary:
     Sources scraped:   {len([v for v in scraped.values() if v is not None])}
     Programs found:    {len(programs)}
     Stored (new):      {store.get('new', 0)}
     Stored (updated):  {store.get('updated', 0)}

  🚀 Next Steps:
     1. Start the API:        civicos serve
     2. Open API docs:        http://localhost:8000/docs
     3. Query programs:       curl http://localhost:8000/v1/programs
     4. Filter by category:   curl http://localhost:8000/v1/programs?category=housing
     5. Full-text search:     curl 'http://localhost:8000/v1/search?q=rental'

  🌟 Thanks for trying CivicOS!
""")


if __name__ == "__main__":
    scrape_only = "--scrape-only" in sys.argv
    asyncio.run(main(scrape_only=scrape_only))

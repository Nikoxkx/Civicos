"""
CivicOS — End-to-end API integration test.

Run with: python tests/integration_test.py
Requires: PostgreSQL running, DATABASE_URL set, migrations applied.
"""

import asyncio
import os
import sys

sys.path.insert(0, ".")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://civicos:civicos_dev@localhost:5432/civicos",
)

from httpx import ASGITransport, AsyncClient
from packages.api.main import app


async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tests = []

        # 1. Health
        r = await client.get("/health")
        assert r.status_code == 200, f"Health: {r.status_code}"
        assert r.json()["status"] == "healthy"
        tests.append("✅ Health check")

        # 2. Categories
        r = await client.get("/v1/categories")
        assert r.status_code == 200
        cats = r.json()
        assert len(cats) == 9, f"Expected 9 categories, got {len(cats)}"
        assert cats[0]["slug"]
        tests.append(f"✅ Categories ({len(cats)})")

        # 3. Cities
        r = await client.get("/v1/cities")
        assert r.status_code == 200
        cities = r.json()
        assert cities["meta"]["total"] == 1
        assert cities["data"][0]["slug"] == "boston"
        tests.append("✅ Cities (Boston)")

        # 4. City detail
        r = await client.get("/v1/cities/boston")
        assert r.status_code == 200
        assert r.json()["name"] == "Boston"
        tests.append("✅ City detail")

        # 5. Empty programs
        r = await client.get("/v1/programs")
        assert r.status_code == 200
        progs = r.json()
        assert progs["data"] == []
        assert progs["meta"]["total"] == 0
        assert progs["meta"]["page"] == 1
        tests.append("✅ Programs (empty, correct meta)")

        # 6. Search
        r = await client.get("/v1/search", params={"q": "housing"})
        assert r.status_code == 200
        search_res = r.json()
        assert search_res["data"] == []
        tests.append("✅ Search (empty, no error)")

        # 7. 404
        r = await client.get("/v1/programs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
        err = r.json()
        # FastAPI wraps HTTPException detail in {"detail": ...}
        error_body = err.get("detail", err)
        assert error_body["error"]["code"] == "PROGRAM_NOT_FOUND"
        tests.append("✅ 404 with structured error")

        # 8. Validation (search query too short)
        r = await client.get("/v1/search", params={"q": "a"})
        assert r.status_code == 422
        tests.append("✅ Validation (422 on short query)")

        # 9. City programs filter
        r = await client.get("/v1/cities/boston/programs")
        assert r.status_code == 200
        city_progs = r.json()
        assert city_progs["meta"]["total"] == 0
        tests.append("✅ City programs filter")

    print("\n".join(tests))
    print(f"\n🎉 All {len(tests)} tests passed!")


if __name__ == "__main__":
    asyncio.run(main())

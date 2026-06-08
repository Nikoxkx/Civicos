"""
CivicOS API — Test fixtures.

Tests use the main database in a development environment. Each test session
creates a savepoint that gets rolled back, so tests are isolated.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://civicos:civicos_dev@localhost:5432/civicos",
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

"""Test configuration and shared fixtures."""

import os
from collections.abc import AsyncIterator, Iterator

os.environ["APP_ENV"] = "test"
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "astraos")
os.environ.setdefault("POSTGRES_PASSWORD", "astraos")
os.environ["POSTGRES_DB"] = "astraos_test"
# CI and unit tests stay offline. Demo default remains llm + rule fallback.
os.environ["INTENT_PARSER_MODE"] = "rule_based"
os.environ["SEMANTIC_EMBEDDING_PROVIDER"] = "hashing"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.db.session import AsyncSessionLocal
from app.main import app
from app.seed.runner import reset_schema, seed_database


@pytest.fixture(scope="session", autouse=True)
def migrate_and_seed() -> None:
    """Apply migrations and seed the test database once per session."""
    reset_schema()

    async def _seed() -> None:
        async with AsyncSessionLocal() as session:
            await seed_database(session, 2026)

    import asyncio

    asyncio.run(_seed())


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Request-scoped session. Callers rollback after writes that should not persist."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """HTTP client bound to the test database."""

    async def _override() -> AsyncIterator[AsyncSession]:
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

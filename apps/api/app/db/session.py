"""Async SQLAlchemy engine and session factory."""

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine: AsyncEngine = create_async_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def wait_for_database(attempts: int = 30, delay: float = 1.0) -> None:
    """Retry PostgreSQL connectivity until the database accepts connections."""
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001 - retry any connect failure
            last_error = exc
            await asyncio.sleep(delay)
    raise RuntimeError("PostgreSQL is not ready") from last_error


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with AsyncSessionLocal() as session:
        yield session

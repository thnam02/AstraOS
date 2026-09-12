"""FastAPI dependencies for database access."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide a request-scoped async SQLAlchemy session."""
    async for session in get_session():
        yield session

"""Persistence for semantic match runs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MatchRun


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, run: MatchRun) -> MatchRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, run_id: uuid.UUID) -> MatchRun | None:
        result = await self.session.scalars(
            select(MatchRun)
            .options(selectinload(MatchRun.matches))
            .where(MatchRun.id == run_id)
        )
        return result.unique().one_or_none()

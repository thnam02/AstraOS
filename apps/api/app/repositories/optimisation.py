"""Persistence for optimisation runs."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.optimisation import OptimisationRun


class OptimisationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, run: OptimisationRun) -> OptimisationRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, run_id: uuid.UUID) -> OptimisationRun | None:
        result = await self.session.scalars(
            select(OptimisationRun).where(OptimisationRun.id == run_id)
        )
        return result.one_or_none()

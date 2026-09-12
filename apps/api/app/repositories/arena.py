"""Persistence for Arena duels and benchmark summaries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ArenaBenchmarkRun, ArenaRun


class ArenaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_run(self, row: ArenaRun) -> ArenaRun:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_benchmark(self, row: ArenaBenchmarkRun) -> ArenaBenchmarkRun:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_run(self, run_id: UUID) -> ArenaRun | None:
        result = await self.session.scalars(
            select(ArenaRun).where(ArenaRun.id == run_id)
        )
        return result.one_or_none()

    async def get_benchmark(self, run_id: UUID) -> ArenaBenchmarkRun | None:
        result = await self.session.scalars(
            select(ArenaBenchmarkRun)
            .options(
                selectinload(ArenaBenchmarkRun.strategy_metrics),
                selectinload(ArenaBenchmarkRun.segment_metrics),
            )
            .where(ArenaBenchmarkRun.id == run_id)
        )
        return result.unique().one_or_none()

    async def latest_benchmark(self) -> ArenaBenchmarkRun | None:
        result = await self.session.scalars(
            select(ArenaBenchmarkRun)
            .options(
                selectinload(ArenaBenchmarkRun.strategy_metrics),
                selectinload(ArenaBenchmarkRun.segment_metrics),
            )
            .where(ArenaBenchmarkRun.status == "COMPLETED")
            .order_by(ArenaBenchmarkRun.created_at.desc())
            .limit(1)
        )
        return result.unique().one_or_none()

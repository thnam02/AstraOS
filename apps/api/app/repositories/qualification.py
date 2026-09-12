"""Persistence for qualification runs and per-variant traces."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import QualificationRun, QualificationVariantResult


class QualificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, run: QualificationRun) -> QualificationRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get(self, run_id: uuid.UUID) -> QualificationRun | None:
        stmt = (
            select(QualificationRun)
            .options(selectinload(QualificationRun.variant_results))
            .where(QualificationRun.id == run_id)
        )
        result = await self.session.scalars(stmt)
        return result.unique().one_or_none()

    async def list_variant_results(
        self,
        run_id: uuid.UUID,
        *,
        outcome: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[QualificationVariantResult], int]:
        filters = [QualificationVariantResult.run_id == run_id]
        if outcome:
            filters.append(QualificationVariantResult.outcome == outcome)
        count_stmt = select(func.count()).select_from(QualificationVariantResult)
        count_stmt = count_stmt.where(*filters)
        total = int(await self.session.scalar(count_stmt) or 0)
        stmt = (
            select(QualificationVariantResult)
            .where(*filters)
            .order_by(
                QualificationVariantResult.outcome,
                QualificationVariantResult.product_name,
                QualificationVariantResult.sku,
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.scalars(stmt)).all()
        return rows, total

    async def get_variant_result(
        self, run_id: uuid.UUID, variant_id: uuid.UUID
    ) -> QualificationVariantResult | None:
        stmt = select(QualificationVariantResult).where(
            QualificationVariantResult.run_id == run_id,
            QualificationVariantResult.variant_id == variant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

"""Persistence for merchant ingestion runs."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MerchantIngestionRun


class IngestionRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: MerchantIngestionRun) -> MerchantIngestionRun:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, run_id: uuid.UUID) -> MerchantIngestionRun | None:
        return await self.session.get(MerchantIngestionRun, run_id)

    async def list_recent(self, *, limit: int = 20) -> Sequence[MerchantIngestionRun]:
        result = await self.session.scalars(
            select(MerchantIngestionRun)
            .order_by(MerchantIngestionRun.started_at.desc())
            .limit(limit)
        )
        return result.all()

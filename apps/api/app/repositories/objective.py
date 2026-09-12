"""Merchant objective persistence."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MerchantObjective


class MerchantObjectiveRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active(self) -> MerchantObjective | None:
        result = await self.session.execute(
            select(MerchantObjective)
            .where(MerchantObjective.is_active.is_(True))
            .order_by(MerchantObjective.updated_at.desc())
        )
        return result.scalars().first()

    async def update_active(self, row: MerchantObjective) -> MerchantObjective:
        await self.session.commit()
        await self.session.refresh(row)
        return row

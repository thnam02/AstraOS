"""Merchant policy persistence."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MerchantPolicy


class MerchantPolicyRepository:
    """Load and persist the active merchant policy."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active(self) -> MerchantPolicy | None:
        stmt = (
            select(MerchantPolicy)
            .where(MerchantPolicy.is_active.is_(True))
            .order_by(MerchantPolicy.updated_at.desc())
            .limit(1)
        )
        result = await self.session.scalars(stmt)
        return result.one_or_none()

    async def update_active(self, policy: MerchantPolicy) -> MerchantPolicy:
        self.session.add(policy)
        await self.session.flush()
        await self.session.refresh(policy)
        return policy

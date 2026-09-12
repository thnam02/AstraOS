"""Read-only merchant catalogue state for later decision modules."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AttributeEvidence,
    BundleOption,
    DataSource,
    DeliveryOption,
    Merchant,
    MerchantPolicy,
    ReturnPolicy,
    VariantDeliveryOption,
    WarrantyOption,
)


@dataclass
class MerchantCatalogueState:
    """Reference data the decision engine will consume later."""

    merchant: Merchant | None
    policy: MerchantPolicy | None
    delivery_options: list[DeliveryOption]
    warranty_options: list[WarrantyOption]
    bundle_options: list[BundleOption]
    return_policies: list[ReturnPolicy]
    data_sources: list[DataSource]


class CatalogueRepository:
    """Assemble merchant reference data. Does not decide offers."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_merchant_state(self) -> MerchantCatalogueState:
        merchant = (
            await self.session.scalars(
                select(Merchant).order_by(Merchant.created_at).limit(1)
            )
        ).one_or_none()
        policy = (
            await self.session.scalars(
                select(MerchantPolicy)
                .where(MerchantPolicy.is_active.is_(True))
                .order_by(MerchantPolicy.updated_at.desc())
                .limit(1)
            )
        ).one_or_none()
        delivery = list(
            (
                await self.session.scalars(
                    select(DeliveryOption).order_by(DeliveryOption.code)
                )
            ).all()
        )
        warranty = list(
            (
                await self.session.scalars(
                    select(WarrantyOption).order_by(WarrantyOption.months)
                )
            ).all()
        )
        bundles = list(
            (
                await self.session.scalars(
                    select(BundleOption).order_by(BundleOption.code)
                )
            ).all()
        )
        returns = list(
            (
                await self.session.scalars(
                    select(ReturnPolicy).order_by(ReturnPolicy.return_window_days)
                )
            ).all()
        )
        sources = list(
            (
                await self.session.scalars(select(DataSource).order_by(DataSource.name))
            ).all()
        )
        return MerchantCatalogueState(
            merchant=merchant,
            policy=policy,
            delivery_options=delivery,
            warranty_options=warranty,
            bundle_options=bundles,
            return_policies=returns,
            data_sources=sources,
        )

    async def same_day_capable_count(self) -> int:
        stmt = (
            select(func.count(func.distinct(VariantDeliveryOption.variant_id)))
            .join(DeliveryOption)
            .where(
                DeliveryOption.code == "SAME_DAY",
                VariantDeliveryOption.available.is_(True),
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def evidence_count(self) -> int:
        return int(
            await self.session.scalar(
                select(func.count()).select_from(AttributeEvidence)
            )
            or 0
        )

    async def load_sources(self) -> dict[object, DataSource]:
        sources = (
            await self.session.scalars(
                select(DataSource).options(selectinload(DataSource.evidence))
            )
        ).all()
        return {source.id: source for source in sources}

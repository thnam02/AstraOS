"""Hackathon-only live merchant-state mutations. Not a production admin API."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.offers.feasibility import sellable_units
from app.models.product import ProductVariant
from app.repositories.policy import MerchantPolicyRepository
from app.repositories.product import ProductRepository
from app.schemas.transaction import (
    DemoDeliveryCapacityRequest,
    DemoInventoryRequest,
    DemoPolicyRequest,
    DemoStateResponse,
)


class DemoStateError(ValueError):
    """Invalid demo mutation."""


class DemoStateService:
    """Mutate real catalogue/policy rows for live Stage 7 demos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.products = ProductRepository(session)
        self.policy = MerchantPolicyRepository(session)

    async def set_inventory(self, payload: DemoInventoryRequest) -> DemoStateResponse:
        variant = await self._variant(payload.sku, payload.variant_id)
        if variant.inventory is None:
            raise DemoStateError("Variant has no inventory record.")
        variant.inventory.units_available = payload.units_available
        if variant.inventory.units_reserved > payload.units_available:
            variant.inventory.units_reserved = payload.units_available
        await self.session.commit()
        return await self._view(variant, delivery_code=None)

    async def set_delivery_capacity(
        self, payload: DemoDeliveryCapacityRequest
    ) -> DemoStateResponse:
        variant = await self._variant(payload.sku, payload.variant_id)
        updated = False
        for link in variant.delivery_options:
            if link.delivery_option.code == payload.delivery_code:
                link.available = payload.available
                updated = True
        if not updated:
            raise DemoStateError(
                f"Delivery {payload.delivery_code} is not linked to this SKU."
            )
        await self.session.commit()
        return await self._view(variant, delivery_code=payload.delivery_code)

    async def set_policy(self, payload: DemoPolicyRequest) -> DemoStateResponse:
        policy = await self.policy.get_active()
        if policy is None:
            raise DemoStateError("No active merchant policy.")
        if payload.minimum_margin_rate is not None:
            policy.minimum_margin_rate = Decimal(str(payload.minimum_margin_rate))
        if payload.maximum_discount_rate is not None:
            policy.maximum_discount_rate = Decimal(str(payload.maximum_discount_rate))
        await self.session.commit()
        variants = await self.products.list_active_variants()
        variant = variants[0] if variants else None
        if variant is None:
            return DemoStateResponse(
                sku="NONE",
                variant_id=policy.id,
                units_available=0,
                units_reserved=0,
                sellable_units=0,
                minimum_margin_rate=float(policy.minimum_margin_rate),
            )
        return await self._view(variant, delivery_code=None)

    async def _variant(
        self, sku: str | None, variant_id: UUID | None
    ) -> ProductVariant:
        variant = None
        if variant_id is not None:
            variant = await self.products.get_variant(variant_id)
        elif sku:
            variant = await self.products.get_variant_by_sku(sku)
        if variant is None:
            raise DemoStateError("Variant not found.")
        return variant

    async def _view(
        self, variant: ProductVariant, *, delivery_code: str | None
    ) -> DemoStateResponse:
        policy = await self.policy.get_active()
        available = None
        if delivery_code:
            for link in variant.delivery_options:
                if link.delivery_option.code == delivery_code:
                    available = bool(link.available and link.delivery_option.enabled)
        units = sellable_units(variant) or 0
        inventory = variant.inventory
        return DemoStateResponse(
            sku=variant.sku,
            variant_id=variant.id,
            units_available=int(inventory.units_available) if inventory else 0,
            units_reserved=int(inventory.units_reserved) if inventory else 0,
            sellable_units=units,
            delivery_code=delivery_code,
            delivery_available=available,
            minimum_margin_rate=float(
                policy.minimum_margin_rate if policy else Decimal("0")
            ),
        )

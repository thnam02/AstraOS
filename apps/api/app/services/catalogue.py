"""Catalogue read service. Assembles DTOs only — no offer decisions."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.proof.quality import catalogue_evidence_quality
from app.models import (
    AttributeEvidence,
    Merchant,
    Product,
    ProductVariant,
    VariantBundleOption,
    VariantDeliveryOption,
    VariantReturnPolicy,
    VariantWarrantyOption,
)
from app.repositories.catalogue import CatalogueRepository
from app.repositories.product import ProductRepository
from app.schemas.bundle import BundleOptionResponse
from app.schemas.delivery import DeliveryOptionResponse
from app.schemas.inventory import InventoryResponse
from app.schemas.product import (
    CatalogueStatsResponse,
    ProductDetail,
    ProductListResponse,
    ProductRecord,
    ProductSummary,
    ProductVariantDetail,
    VariantSummary,
)
from app.schemas.provenance import AttributeEvidenceResponse, DataSourceResponse
from app.schemas.returns import ReturnPolicyResponse
from app.schemas.warranty import WarrantyOptionResponse

CORE_ATTRIBUTES = (
    "anc",
    "battery_hours",
    "comfort_score",
    "travel_score",
    "weight_g",
    "wireless",
)


def _has_missing_attributes(attributes: dict[str, Any]) -> bool:
    return any(
        key not in attributes or attributes[key] is None for key in CORE_ATTRIBUTES
    )


def _same_day_available(variant: ProductVariant) -> bool:
    for link in variant.delivery_options:
        option = link.delivery_option
        if link.available and option is not None and option.code == "SAME_DAY":
            return True
    return False


def _attr_bool(attributes: dict[str, Any], key: str) -> bool | None:
    if key not in attributes or attributes[key] is None:
        return None
    return bool(attributes[key])


def _attr_number(attributes: dict[str, Any], key: str) -> float | None:
    value = attributes.get(key)
    if value is None:
        return None
    return float(value)


class CatalogueService:
    """Read merchant catalogue data for inspection APIs."""

    def __init__(self, session: AsyncSession) -> None:
        self.products = ProductRepository(session)
        self.catalogue = CatalogueRepository(session)

    async def list_products(
        self,
        *,
        category: str | None = None,
        brand: str | None = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> ProductListResponse:
        items, total = await self.products.list_products(
            category=category,
            brand=brand,
            active_only=active_only,
            limit=limit,
            offset=offset,
        )
        return ProductListResponse(
            items=[self._to_product_summary(product) for product in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_product(self, product_id: uuid.UUID) -> ProductDetail | None:
        product = await self.products.get_product(product_id)
        if product is None:
            return None
        return ProductDetail(
            product=ProductRecord.model_validate(product),
            variants=[self._to_variant_detail(variant) for variant in product.variants],
        )

    async def get_variant(self, variant_id: uuid.UUID) -> ProductVariantDetail | None:
        variant = await self.products.get_variant(variant_id)
        if variant is None:
            return None
        return self._to_variant_detail(variant)

    async def stats(self) -> CatalogueStatsResponse:
        base = await self.products.stats()
        items, _ = await self.products.list_products(
            active_only=False, limit=1000, offset=0
        )
        missing = 0
        out_of_stock = 0
        for product in items:
            for variant in product.variants:
                if _has_missing_attributes(variant.attributes):
                    missing += 1
                available = (
                    variant.inventory.units_available if variant.inventory else 0
                )
                reserved = variant.inventory.units_reserved if variant.inventory else 0
                if max(available - reserved, 0) <= 0:
                    out_of_stock += 1
        return CatalogueStatsResponse(
            products=base["products"],
            variants=base["variants"],
            in_stock_variants=base["in_stock_variants"],
            out_of_stock_variants=out_of_stock,
            same_day_capable=await self.catalogue.same_day_capable_count(),
            missing_attribute_variants=missing,
            brands=base["brands"],
            categories=base["categories"],
            evidence_records=await self.catalogue.evidence_count(),
            data_mode=await self._data_mode(),
            evidence_quality=catalogue_evidence_quality(list(items)),
        )

    def _to_product_summary(self, product: Product) -> ProductSummary:
        return ProductSummary(
            id=product.id,
            name=product.name,
            brand=product.brand,
            category=product.category,
            model_number=product.model_number,
            is_active=product.is_active,
            source_system=product.source_system,
            variant_count=len(product.variants),
            variants=[
                self._to_variant_summary(variant) for variant in product.variants
            ],
        )

    def _to_variant_summary(self, variant: ProductVariant) -> VariantSummary:
        inventory = variant.inventory
        return VariantSummary(
            id=variant.id,
            sku=variant.sku,
            variant_name=variant.variant_name,
            currency=variant.currency,
            base_price_cents=variant.base_price_cents,
            cogs_cents=variant.cogs_cents,
            units_available=inventory.units_available if inventory else 0,
            units_reserved=inventory.units_reserved if inventory else 0,
            same_day_available=_same_day_available(variant),
            anc=_attr_bool(variant.attributes, "anc"),
            battery_hours=_attr_number(variant.attributes, "battery_hours"),
            is_active=variant.is_active,
            has_missing_attributes=_has_missing_attributes(variant.attributes),
            source_system=variant.source_system,
        )

    def _to_variant_detail(self, variant: ProductVariant) -> ProductVariantDetail:
        return ProductVariantDetail(
            id=variant.id,
            product_id=variant.product_id,
            sku=variant.sku,
            variant_name=variant.variant_name,
            currency=variant.currency,
            base_price_cents=variant.base_price_cents,
            cogs_cents=variant.cogs_cents,
            attributes=variant.attributes,
            is_active=variant.is_active,
            source_system=variant.source_system,
            inventory=(
                InventoryResponse.model_validate(variant.inventory)
                if variant.inventory
                else None
            ),
            delivery_options=[
                self._delivery(link) for link in variant.delivery_options
            ],
            warranty_options=[
                self._warranty(link) for link in variant.warranty_options
            ],
            bundle_options=[self._bundle(link) for link in variant.bundle_options],
            return_policies=[
                self._return_policy(link) for link in variant.return_policies
            ],
            evidence=[self._evidence(row) for row in variant.evidence],
        )

    def _delivery(self, link: VariantDeliveryOption) -> DeliveryOptionResponse:
        option = link.delivery_option
        return DeliveryOptionResponse(
            id=option.id,
            code=option.code,
            name=option.name,
            description=option.description,
            delivery_days=option.delivery_days,
            merchant_cost_cents=option.merchant_cost_cents,
            customer_charge_cents=option.customer_charge_cents,
            enabled=option.enabled,
            available=link.available,
            merchant_cost_override_cents=link.merchant_cost_override_cents,
            customer_charge_override_cents=link.customer_charge_override_cents,
            cutoff_time=link.cutoff_time,
        )

    def _warranty(self, link: VariantWarrantyOption) -> WarrantyOptionResponse:
        option = link.warranty_option
        return WarrantyOptionResponse(
            id=option.id,
            code=option.code,
            name=option.name,
            months=option.months,
            merchant_cost_cents=option.merchant_cost_cents,
            customer_price_cents=option.customer_price_cents,
            enabled=option.enabled,
            available=link.available,
        )

    def _bundle(self, link: VariantBundleOption) -> BundleOptionResponse:
        option = link.bundle_option
        return BundleOptionResponse(
            id=option.id,
            code=option.code,
            name=option.name,
            description=option.description,
            merchant_cost_cents=option.merchant_cost_cents,
            customer_price_cents=option.customer_price_cents,
            enabled=option.enabled,
            attributes=option.attributes,
            available=link.available,
        )

    def _return_policy(self, link: VariantReturnPolicy) -> ReturnPolicyResponse:
        option = link.return_policy
        return ReturnPolicyResponse(
            id=option.id,
            code=option.code,
            name=option.name,
            return_window_days=option.return_window_days,
            restocking_fee_rate=option.restocking_fee_rate,
            conditions=option.conditions,
            merchant_expected_cost_cents=option.merchant_expected_cost_cents,
            enabled=option.enabled,
            available=link.available,
        )

    def _evidence(self, row: AttributeEvidence) -> AttributeEvidenceResponse:
        now = datetime.now(UTC)
        expires = row.expires_at
        is_stale = expires is not None and expires < now
        return AttributeEvidenceResponse(
            id=row.id,
            variant_id=row.variant_id,
            attribute_name=row.attribute_name,
            value=row.value,
            source=DataSourceResponse.model_validate(row.source),
            source_reference=row.source_reference,
            confidence=row.confidence,
            verification_status=row.verification_status,
            observed_at=row.observed_at,
            expires_at=row.expires_at,
            is_stale=is_stale,
        )

    async def _data_mode(self) -> str | None:
        merchant = (
            await self.products.session.scalars(select(Merchant).limit(1))
        ).first()
        return merchant.data_mode if merchant is not None else None

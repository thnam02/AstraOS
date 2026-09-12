"""In-memory catalogue snapshot used by the eligibility evaluator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.models import ProductVariant


@dataclass(frozen=True)
class DeliverySnapshot:
    code: str
    name: str
    days: int
    available: bool
    enabled: bool


@dataclass(frozen=True)
class EvidenceSnapshot:
    id: str
    attribute_name: str
    value: Any
    source_name: str
    source_type: str
    source_reference: str | None
    verification_status: str
    observed_at: datetime
    expires_at: datetime | None

    @property
    def is_stale(self) -> bool:
        if self.expires_at is None:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires < datetime.now(UTC)


@dataclass(frozen=True)
class InventorySnapshot:
    units_available: int
    units_reserved: int
    updated_at: datetime | None = None

    @property
    def sellable_units(self) -> int:
        return self.units_available - self.units_reserved


@dataclass
class VariantSnapshot:
    """Merchant facts the evaluator may read. No offer fields."""

    product_id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    brand: str
    category: str
    variant_name: str | None
    base_price_cents: int
    attributes: dict[str, Any]
    inventory: InventorySnapshot | None = None
    deliveries: list[DeliverySnapshot] = field(default_factory=list)
    evidence: list[EvidenceSnapshot] = field(default_factory=list)


def variant_to_snapshot(variant: ProductVariant) -> VariantSnapshot:
    """Map a loaded ORM variant to an evaluator snapshot."""
    product = variant.product
    inventory = None
    if variant.inventory is not None:
        inventory = InventorySnapshot(
            units_available=variant.inventory.units_available,
            units_reserved=variant.inventory.units_reserved,
            updated_at=variant.inventory.updated_at,
        )
    deliveries = []
    for link in variant.delivery_options:
        option = link.delivery_option
        if option is None:
            continue
        deliveries.append(
            DeliverySnapshot(
                code=option.code,
                name=option.name,
                days=option.delivery_days,
                available=bool(link.available),
                enabled=bool(option.enabled),
            )
        )
    evidence = []
    for row in variant.evidence:
        source = row.source
        evidence.append(
            EvidenceSnapshot(
                id=str(row.id),
                attribute_name=row.attribute_name,
                value=row.value,
                source_name=source.name if source is not None else "unknown",
                source_type=source.source_type if source is not None else "unknown",
                source_reference=row.source_reference,
                verification_status=row.verification_status,
                observed_at=row.observed_at,
                expires_at=row.expires_at,
            )
        )
    return VariantSnapshot(
        product_id=product.id,
        variant_id=variant.id,
        sku=variant.sku,
        product_name=product.name,
        brand=product.brand,
        category=product.category,
        variant_name=variant.variant_name,
        base_price_cents=variant.base_price_cents,
        attributes=dict(variant.attributes or {}),
        inventory=inventory,
        deliveries=deliveries,
        evidence=evidence,
    )

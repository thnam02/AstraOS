"""External and canonical ingestion DTOs. Not SQLAlchemy models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExternalMerchantSnapshot:
    """Adapter output. Raw typed records before normalisation."""

    schema_version: str
    source_type: str
    source_name: str
    merchant: dict[str, Any] = field(default_factory=dict)
    products: list[dict[str, Any]] = field(default_factory=list)
    variants: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    delivery_options: list[dict[str, Any]] = field(default_factory=list)
    warranties: list[dict[str, Any]] = field(default_factory=list)
    bundles: list[dict[str, Any]] = field(default_factory=list)
    return_policies: list[dict[str, Any]] = field(default_factory=list)
    variant_delivery: list[dict[str, Any]] = field(default_factory=list)
    variant_warranty: list[dict[str, Any]] = field(default_factory=list)
    variant_bundle: list[dict[str, Any]] = field(default_factory=list)
    variant_returns: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    raw_bytes: bytes = b""


@dataclass
class CanonicalProduct:
    external_id: str
    name: str
    brand: str
    category: str
    description: str | None
    model_number: str | None
    manufacturer: str | None
    is_active: bool = True


@dataclass
class CanonicalVariant:
    sku: str
    product_external_id: str
    variant_name: str | None
    currency: str
    base_price_cents: int
    cogs_cents: int
    attributes: dict[str, Any]
    is_active: bool = True


@dataclass
class CanonicalInventory:
    sku: str
    units_available: int
    warehouse_code: str
    observed_at: datetime | None = None


@dataclass
class CanonicalDeliveryOption:
    code: str
    name: str
    description: str | None
    delivery_days: int
    merchant_cost_cents: int
    customer_charge_cents: int
    enabled: bool = True


@dataclass
class CanonicalWarrantyOption:
    code: str
    name: str
    months: int
    merchant_cost_cents: int
    customer_price_cents: int
    enabled: bool = True


@dataclass
class CanonicalBundleOption:
    code: str
    name: str
    description: str | None
    merchant_cost_cents: int
    customer_price_cents: int
    enabled: bool = True
    attributes: dict[str, Any] | None = None


@dataclass
class CanonicalReturnPolicy:
    code: str
    name: str
    return_window_days: int
    restocking_fee_rate: float | None
    conditions: str | None
    merchant_expected_cost_cents: int | None
    enabled: bool = True


@dataclass
class CanonicalVariantLink:
    sku: str
    option_code: str
    available: bool = True


@dataclass
class CanonicalEvidence:
    sku: str
    attribute_name: str
    value: Any
    source_type: str
    source_name: str
    source_reference: str | None
    verification_status: str
    observed_at: datetime
    expires_at: datetime | None
    confidence: float | None = None


@dataclass
class CanonicalMerchantSnapshot:
    schema_version: str
    source_type: str
    source_name: str
    merchant_name: str | None
    merchant_code: str | None
    currency: str
    products: list[CanonicalProduct] = field(default_factory=list)
    variants: list[CanonicalVariant] = field(default_factory=list)
    inventory: list[CanonicalInventory] = field(default_factory=list)
    delivery_options: list[CanonicalDeliveryOption] = field(default_factory=list)
    warranties: list[CanonicalWarrantyOption] = field(default_factory=list)
    bundles: list[CanonicalBundleOption] = field(default_factory=list)
    return_policies: list[CanonicalReturnPolicy] = field(default_factory=list)
    variant_delivery: list[CanonicalVariantLink] = field(default_factory=list)
    variant_warranty: list[CanonicalVariantLink] = field(default_factory=list)
    variant_bundle: list[CanonicalVariantLink] = field(default_factory=list)
    variant_returns: list[CanonicalVariantLink] = field(default_factory=list)
    evidence: list[CanonicalEvidence] = field(default_factory=list)

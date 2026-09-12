"""Helpers for isolated persistence tests."""

import uuid
from decimal import Decimal

from app.models import (
    AttributeEvidence,
    BundleOption,
    DataSource,
    DeliveryOption,
    InventoryRecord,
    Merchant,
    MerchantPolicy,
    Product,
    ProductVariant,
    ReturnPolicy,
    VariantBundleOption,
    VariantDeliveryOption,
    VariantWarrantyOption,
    WarrantyOption,
)
from app.seed.ids import stable_uuid


def unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def make_product(**overrides: object) -> Product:
    token = unique("P")
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": f"Test {token}",
        "brand": "Helix",
        "category": "headphones",
        "description": "Test product",
        "model_number": token,
        "manufacturer": "Helix",
        "is_active": True,
    }
    values.update(overrides)
    return Product(**values)  # type: ignore[arg-type]


def make_variant(product_id: uuid.UUID, **overrides: object) -> ProductVariant:
    sku = unique("SKU")
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "product_id": product_id,
        "sku": sku,
        "variant_name": "Black",
        "currency": "AUD",
        "base_price_cents": 19900,
        "cogs_cents": 11000,
        "attributes": {"anc": True, "battery_hours": 30},
        "is_active": True,
    }
    values.update(overrides)
    return ProductVariant(**values)  # type: ignore[arg-type]


def make_inventory(variant_id: uuid.UUID, **overrides: object) -> InventoryRecord:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "variant_id": variant_id,
        "units_available": 10,
        "units_reserved": 0,
        "warehouse_code": "SYD-01",
    }
    values.update(overrides)
    return InventoryRecord(**values)  # type: ignore[arg-type]


def make_delivery(**overrides: object) -> DeliveryOption:
    code = unique("DEL")
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": code,
        "name": code,
        "delivery_days": 2,
        "merchant_cost_cents": 0,
        "customer_charge_cents": 0,
        "enabled": True,
    }
    values.update(overrides)
    return DeliveryOption(**values)  # type: ignore[arg-type]


def make_warranty(**overrides: object) -> WarrantyOption:
    code = unique("WAR")
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": code,
        "name": code,
        "months": 12,
        "merchant_cost_cents": 0,
        "customer_price_cents": 0,
        "enabled": True,
    }
    values.update(overrides)
    return WarrantyOption(**values)  # type: ignore[arg-type]


def make_bundle(**overrides: object) -> BundleOption:
    code = unique("BUN")
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": code,
        "name": code,
        "merchant_cost_cents": 700,
        "customer_price_cents": 1500,
        "enabled": True,
    }
    values.update(overrides)
    return BundleOption(**values)  # type: ignore[arg-type]


def make_source(**overrides: object) -> DataSource:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": unique("SRC"),
        "source_type": "SYNTHETIC",
    }
    values.update(overrides)
    return DataSource(**values)  # type: ignore[arg-type]


def make_merchant(**overrides: object) -> Merchant:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "name": "Test Merchant",
        "code": unique("MER"),
        "currency": "AUD",
    }
    values.update(overrides)
    return Merchant(**values)  # type: ignore[arg-type]


def make_policy(merchant_id: uuid.UUID, **overrides: object) -> MerchantPolicy:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "merchant_id": merchant_id,
        "name": "Test Policy",
        "is_active": False,
        "minimum_margin_rate": Decimal("0.1500"),
        "maximum_discount_rate": Decimal("0.1000"),
        "delivery_subsidy_enabled": True,
        "warranty_upgrade_enabled": True,
        "bundle_enabled": True,
        "flexible_returns_enabled": True,
        "loyalty_enabled": False,
    }
    values.update(overrides)
    return MerchantPolicy(**values)  # type: ignore[arg-type]


__all__ = [
    "AttributeEvidence",
    "ReturnPolicy",
    "VariantBundleOption",
    "VariantDeliveryOption",
    "VariantWarrantyOption",
    "make_bundle",
    "make_delivery",
    "make_inventory",
    "make_merchant",
    "make_policy",
    "make_product",
    "make_source",
    "make_variant",
    "make_warranty",
    "stable_uuid",
    "unique",
]

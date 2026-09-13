"""Canonical fingerprints for unchanged detection and index invalidation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.ingestion.constants import SEMANTIC_ATTRIBUTE_KEYS
from app.ingestion.schemas import (
    CanonicalInventory,
    CanonicalProduct,
    CanonicalVariant,
)


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fingerprint(*parts: Any) -> str:
    return hashlib.sha256(_dump(parts).encode("utf-8")).hexdigest()


def product_fingerprint(row: CanonicalProduct) -> str:
    return fingerprint(
        row.external_id,
        row.name,
        row.brand,
        row.category,
        row.description,
        row.model_number,
        row.manufacturer,
        row.is_active,
    )


def commercial_fingerprint(row: CanonicalVariant) -> str:
    return fingerprint(
        row.sku,
        row.currency,
        row.base_price_cents,
        row.cogs_cents,
        row.variant_name,
        row.is_active,
    )


def semantic_fingerprint(
    product: CanonicalProduct,
    variant: CanonicalVariant,
    *,
    same_day: bool | None,
) -> str:
    attrs = {
        key: variant.attributes.get(key)
        for key in SEMANTIC_ATTRIBUTE_KEYS
        if key in variant.attributes
    }
    return fingerprint(
        product.name,
        product.brand,
        product.category,
        product.description,
        attrs,
        same_day,
    )


def inventory_fingerprint(row: CanonicalInventory) -> str:
    return fingerprint(row.sku, row.units_available, row.warehouse_code)


def existing_product_fingerprint(
    *,
    external_id: str,
    name: str,
    brand: str,
    category: str,
    description: str | None,
    model_number: str | None,
    manufacturer: str | None,
    is_active: bool,
) -> str:
    return product_fingerprint(
        CanonicalProduct(
            external_id=external_id,
            name=name,
            brand=brand,
            category=category,
            description=description,
            model_number=model_number,
            manufacturer=manufacturer,
            is_active=is_active,
        )
    )


def existing_commercial_fingerprint(
    *,
    sku: str,
    currency: str,
    base_price_cents: int,
    cogs_cents: int,
    variant_name: str | None,
    is_active: bool,
) -> str:
    return fingerprint(
        sku, currency, base_price_cents, cogs_cents, variant_name, is_active
    )


def existing_inventory_fingerprint(
    *, sku: str, units_available: int, warehouse_code: str
) -> str:
    return fingerprint(sku, units_available, warehouse_code)

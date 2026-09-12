"""Controlled mapping from constraint fields to merchant data.

Do not scatter `if field == ...` through services. Add new categories here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from app.decision.eligibility.snapshot import EvidenceSnapshot, VariantSnapshot
from app.decision.intent.models import ConstraintField

ResolutionKind = Literal["scalar", "inventory", "delivery"]


@dataclass(frozen=True)
class FieldResolution:
    """Result of looking up one allow-listed field on a variant."""

    present: bool
    value: Any | None
    kind: ResolutionKind
    missing_reason: str
    evidence: EvidenceSnapshot | None = None
    source_name: str | None = None
    source_reference: str | None = None


EVIDENCE_ATTRIBUTE_NAMES: dict[ConstraintField, str] = {
    ConstraintField.PRICE: "base_price_cents",
    ConstraintField.ANC: "anc",
    ConstraintField.BATTERY_HOURS: "battery_hours",
    ConstraintField.WEIGHT_G: "weight_g",
    ConstraintField.FOLDABLE: "foldable",
    ConstraintField.WIRELESS: "wireless",
    ConstraintField.MICROPHONE: "microphone",
    ConstraintField.IN_STOCK: "units_available",
    ConstraintField.BRAND: "brand",
    ConstraintField.CATEGORY: "category",
}

ATTRIBUTE_KEYS: dict[ConstraintField, str] = {
    ConstraintField.ANC: "anc",
    ConstraintField.BATTERY_HOURS: "battery_hours",
    ConstraintField.WEIGHT_G: "weight_g",
    ConstraintField.FOLDABLE: "foldable",
    ConstraintField.WIRELESS: "wireless",
    ConstraintField.MICROPHONE: "microphone",
}


def _pick_evidence(
    snapshot: VariantSnapshot, attribute_name: str
) -> EvidenceSnapshot | None:
    matches = [row for row in snapshot.evidence if row.attribute_name == attribute_name]
    if not matches:
        return None
    fresh = [row for row in matches if not row.is_stale]
    if fresh:
        return max(fresh, key=lambda row: row.observed_at)
    return max(matches, key=lambda row: row.observed_at)


def _from_attribute(
    field: ConstraintField,
) -> Callable[[VariantSnapshot], FieldResolution]:
    key = ATTRIBUTE_KEYS[field]

    def resolve(snapshot: VariantSnapshot) -> FieldResolution:
        attributes = snapshot.attributes
        evidence = _pick_evidence(snapshot, key)
        if key not in attributes or attributes[key] is None:
            return FieldResolution(
                present=False,
                value=None,
                kind="scalar",
                missing_reason="MISSING_ATTRIBUTE",
                evidence=evidence,
                source_name=evidence.source_name if evidence else None,
                source_reference=evidence.source_reference if evidence else None,
            )
        return FieldResolution(
            present=True,
            value=attributes[key],
            kind="scalar",
            missing_reason="",
            evidence=evidence,
            source_name=evidence.source_name if evidence else "Product attributes",
            source_reference=evidence.source_reference if evidence else key,
        )

    return resolve


def _price(snapshot: VariantSnapshot) -> FieldResolution:
    evidence = _pick_evidence(snapshot, "base_price_cents")
    return FieldResolution(
        present=True,
        value=snapshot.base_price_cents,
        kind="scalar",
        missing_reason="",
        evidence=evidence,
        source_name=evidence.source_name if evidence else "Merchant pricing",
        source_reference=evidence.source_reference if evidence else "base_price_cents",
    )


def _brand(snapshot: VariantSnapshot) -> FieldResolution:
    return FieldResolution(
        present=bool(snapshot.brand),
        value=snapshot.brand or None,
        kind="scalar",
        missing_reason="MISSING_ATTRIBUTE" if not snapshot.brand else "",
        source_name="Product record",
        source_reference="brand",
    )


def _category(snapshot: VariantSnapshot) -> FieldResolution:
    return FieldResolution(
        present=bool(snapshot.category),
        value=snapshot.category or None,
        kind="scalar",
        missing_reason="MISSING_ATTRIBUTE" if not snapshot.category else "",
        source_name="Product record",
        source_reference="category",
    )


def _in_stock(snapshot: VariantSnapshot) -> FieldResolution:
    if snapshot.inventory is None:
        return FieldResolution(
            present=False,
            value=None,
            kind="inventory",
            missing_reason="MISSING_INVENTORY",
            source_name="Inventory",
            source_reference="inventory_records",
        )
    sellable = snapshot.inventory.sellable_units
    return FieldResolution(
        present=True,
        value=sellable > 0,
        kind="inventory",
        missing_reason="",
        source_name="Warehouse on-hand",
        source_reference="units_available - units_reserved",
    )


def _delivery(_snapshot: VariantSnapshot) -> FieldResolution:
    return FieldResolution(
        present=True,
        value=None,
        kind="delivery",
        missing_reason="",
        source_name="Fulfilment",
        source_reference="variant_delivery_options",
    )


FIELD_RESOLVERS: dict[ConstraintField, Callable[[VariantSnapshot], FieldResolution]] = {
    ConstraintField.PRICE: _price,
    ConstraintField.BRAND: _brand,
    ConstraintField.CATEGORY: _category,
    ConstraintField.IN_STOCK: _in_stock,
    ConstraintField.DELIVERY_DAYS: _delivery,
    ConstraintField.SAME_DAY_DELIVERY: _delivery,
    ConstraintField.ANC: _from_attribute(ConstraintField.ANC),
    ConstraintField.BATTERY_HOURS: _from_attribute(ConstraintField.BATTERY_HOURS),
    ConstraintField.WEIGHT_G: _from_attribute(ConstraintField.WEIGHT_G),
    ConstraintField.FOLDABLE: _from_attribute(ConstraintField.FOLDABLE),
    ConstraintField.WIRELESS: _from_attribute(ConstraintField.WIRELESS),
    ConstraintField.MICROPHONE: _from_attribute(ConstraintField.MICROPHONE),
}


def resolve_field(field: ConstraintField, snapshot: VariantSnapshot) -> FieldResolution:
    """Resolve one allow-listed field. Unknown fields stay unknown."""
    resolver = FIELD_RESOLVERS.get(field)
    if resolver is None:
        return FieldResolution(
            present=False,
            value=None,
            kind="scalar",
            missing_reason="UNSUPPORTED_FIELD",
        )
    return resolver(snapshot)

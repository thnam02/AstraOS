"""Documented deterministic derivations. Not merchant-supplied facts."""

from __future__ import annotations

import re
from typing import Any

from app.decision.eligibility.snapshot import VariantSnapshot

_WEIGHT_RE = re.compile(
    r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(kg|g|grams|gram|kilograms?)?\s*$",
    re.IGNORECASE,
)

LIGHTWEIGHT_RULE = "headphones_lightweight_v1"
LIGHTWEIGHT_GRAMS = 250
SAME_DAY_RULE = "fulfilment_same_day_v1"


def derive_lightweight(snapshot: VariantSnapshot) -> dict[str, Any] | None:
    weight = snapshot.attributes.get("weight_g")
    grams = _grams(weight)
    if grams is None or grams > LIGHTWEIGHT_GRAMS:
        return None
    return {
        "claim_key": "lightweight",
        "display_claim": f"Lightweight ({int(grams)}g)",
        "value": True,
        "unit": None,
        "derived": True,
        "derivation_rule": LIGHTWEIGHT_RULE,
        "source_attribute": "weight_g",
    }


def derive_same_day(snapshot: VariantSnapshot) -> dict[str, Any] | None:
    if not snapshot.deliveries:
        return None
    capable = any(
        option.available and option.enabled and option.days == 0
        for option in snapshot.deliveries
    )
    if not capable:
        return None
    option = next(
        item
        for item in snapshot.deliveries
        if item.available and item.enabled and item.days == 0
    )
    return {
        "claim_key": "same_day",
        "display_claim": "Same-day capable",
        "value": True,
        "unit": None,
        "derived": True,
        "derivation_rule": SAME_DAY_RULE,
        "source_record_id": option.code,
        "source_type": "FULFILMENT_CONFIGURATION",
        "source_name": option.name,
    }


def _grams(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    match = _WEIGHT_RE.match(str(value))
    if match is None:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "g").lower()
    if unit.startswith("kg"):
        return amount * 1000
    return amount

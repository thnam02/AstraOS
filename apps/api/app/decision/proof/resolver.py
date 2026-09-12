"""Deterministic source precedence and conflict detection."""

from __future__ import annotations

from typing import Any

from app.decision.eligibility.snapshot import EvidenceSnapshot, VariantSnapshot
from app.decision.proof.freshness import freshness_of
from app.decision.proof.models import public_verification

_PRECEDENCE = {
    "units_available": (
        "MERCHANT_INVENTORY",
        "MERCHANT_PRODUCT_FEED",
        "EXAMPLE_MERCHANT_IMPORT",
    ),
    "base_price_cents": (
        "PRICING_FEED",
        "MERCHANT_PRICING",
        "MERCHANT_PRODUCT_FEED",
        "EXAMPLE_MERCHANT_IMPORT",
    ),
    "same_day": ("FULFILMENT_CONFIGURATION", "FULFILMENT", "MERCHANT_PRODUCT_FEED"),
}


def _rank(attribute: str, source_type: str) -> int:
    order = _PRECEDENCE.get(attribute, ())
    key = source_type.upper()
    if key in order:
        return order.index(key)
    return len(order) + 1


def resolve_attribute(
    snapshot: VariantSnapshot, attribute: str
) -> tuple[EvidenceSnapshot | None, str]:
    """Return (evidence, verification). CONFLICTED if unresolved disagreement."""
    rows = [
        row
        for row in snapshot.evidence
        if row.attribute_name == attribute
    ]
    if not rows:
        return None, "UNKNOWN"
    current = [row for row in rows if freshness_of(row, attribute=attribute) != "STALE"]
    pool = current or rows
    ranked = sorted(pool, key=lambda row: _rank(attribute, row.source_type))
    winner = ranked[0]
    winner_rank = _rank(attribute, winner.source_type)
    values = {
        _norm(row.value)
        for row in ranked
        if _rank(attribute, row.source_type) == winner_rank
    }
    if len(values) > 1:
        return winner, "CONFLICTED"
    return winner, public_verification(winner.verification_status)


def _norm(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return f"{float(value):.6g}"
    return str(value).strip().lower()

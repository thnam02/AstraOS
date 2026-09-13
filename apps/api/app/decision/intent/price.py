"""Buyer price-constraint semantics. Default is final customer spend."""

from __future__ import annotations

import re

from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    PriceBasis,
    ShoppingIntent,
)

_PRODUCT_ONLY = re.compile(
    r"base(?:\s+product)?\s+price|product[- ]only|"
    r"before\s+(?:delivery|extras|add(?:-|\s)?ons)|"
    r"list price|sticker price|catalogue price",
    flags=re.IGNORECASE,
)

_MAX_OPS = {ConstraintOperator.LT, ConstraintOperator.LTE}


def infer_price_basis(source_phrase: str | None) -> PriceBasis:
    if source_phrase and _PRODUCT_ONLY.search(source_phrase):
        return PriceBasis.PRODUCT_BASE
    return PriceBasis.CUSTOMER_TOTAL


def resolved_price_basis(constraint: HardConstraint) -> PriceBasis:
    if constraint.applies_to is not None:
        return constraint.applies_to
    return infer_price_basis(constraint.source_phrase)


def price_constraints(intent: ShoppingIntent) -> list[HardConstraint]:
    return [
        item for item in intent.hard_constraints if item.field == ConstraintField.PRICE
    ]


def max_customer_total_cents(intent: ShoppingIntent) -> int | None:
    caps: list[int] = []
    for item in price_constraints(intent):
        if resolved_price_basis(item) != PriceBasis.CUSTOMER_TOTAL:
            continue
        if item.operator not in _MAX_OPS:
            continue
        value = (
            item.normalized_value if item.normalized_value is not None else item.value
        )
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        caps.append(int(value))
    return min(caps) if caps else None

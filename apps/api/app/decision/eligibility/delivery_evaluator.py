"""Delivery eligibility uses fulfilment rows, never product attributes."""

from __future__ import annotations

from typing import Any

from app.decision.eligibility.models import ConstraintStatus
from app.decision.eligibility.snapshot import DeliverySnapshot, VariantSnapshot
from app.decision.intent.models import ConstraintField, ConstraintOperator


def usable_delivery_options(snapshot: VariantSnapshot) -> list[DeliverySnapshot]:
    return [
        option for option in snapshot.deliveries if option.available and option.enabled
    ]


def evaluate_delivery(
    *,
    field: ConstraintField,
    operator: ConstraintOperator,
    expected: Any,
    snapshot: VariantSnapshot,
) -> tuple[ConstraintStatus, Any, str, str | None]:
    """Return status, observed value, reason, and supporting option name."""
    usable = usable_delivery_options(snapshot)
    has_rows = bool(snapshot.deliveries)
    if not has_rows:
        return (
            ConstraintStatus.UNKNOWN,
            None,
            "MISSING_DELIVERY_DATA",
            None,
        )

    if field == ConstraintField.SAME_DAY_DELIVERY:
        expected_bool = bool(expected)
        same_day = [option for option in usable if option.days == 0]
        observed = bool(same_day)
        if operator == ConstraintOperator.EQ:
            if observed == expected_bool:
                name = same_day[0].name if same_day else None
                return (
                    ConstraintStatus.SATISFIED,
                    observed,
                    "CONSTRAINT_SATISFIED",
                    name,
                )
            return ConstraintStatus.VIOLATED, observed, "CONSTRAINT_VIOLATED", None
        return ConstraintStatus.UNKNOWN, observed, "UNSUPPORTED_OPERATOR", None

    try:
        limit = int(expected)
    except (TypeError, ValueError):
        return ConstraintStatus.UNKNOWN, None, "INVALID_EXPECTED_VALUE", None

    qualifying = [option for option in usable if _meets(option.days, operator, limit)]
    fastest = min((option.days for option in usable), default=None)
    if qualifying:
        best = min(qualifying, key=lambda option: option.days)
        return (
            ConstraintStatus.SATISFIED,
            best.days,
            "CONSTRAINT_SATISFIED",
            best.name,
        )
    if usable:
        return ConstraintStatus.VIOLATED, fastest, "CONSTRAINT_VIOLATED", None
    return ConstraintStatus.UNKNOWN, None, "MISSING_DELIVERY_DATA", None


def _meets(days: int, operator: ConstraintOperator, limit: int) -> bool:
    if operator == ConstraintOperator.LT:
        return days < limit
    if operator == ConstraintOperator.LTE:
        return days <= limit
    if operator == ConstraintOperator.EQ:
        return days == limit
    if operator == ConstraintOperator.GT:
        return days > limit
    if operator == ConstraintOperator.GTE:
        return days >= limit
    if operator == ConstraintOperator.NE:
        return days != limit
    return False

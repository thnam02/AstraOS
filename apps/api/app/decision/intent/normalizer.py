"""Normalize parsed values so eligibility never sees natural-language variants."""

from __future__ import annotations

import re
from typing import Any

from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    IntentStatus,
    ShoppingIntent,
)

WORD_NUMBERS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twelve": 12,
}


def dollars_to_cents(value: Any) -> int:
    """Convert a dollar amount to integer AUD cents."""
    if isinstance(value, bool):
        raise ValueError("Boolean is not a money amount.")
    if isinstance(value, int) and abs(value) >= 1000:
        return value
    number = float(str(value).replace(",", "").replace("$", "").replace("A", ""))
    return int(round(number * 100))


def parse_money_to_cents(text: str) -> int | None:
    match = re.search(
        r"(?:a\$|aud\s*)?\$?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return dollars_to_cents(match.group(1))


def parse_number(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    if match:
        return float(match.group(1))
    for word, number in WORD_NUMBERS.items():
        if re.search(rf"\b{word}\b", text, flags=re.IGNORECASE):
            return float(number)
    return None


def normalize_weight_grams(text: str, raw: Any | None = None) -> int | None:
    kg = re.search(r"(\d+(?:\.\d+)?)\s*kg", text, flags=re.IGNORECASE)
    if kg:
        return int(round(float(kg.group(1)) * 1000))
    grams = re.search(r"(\d+(?:\.\d+)?)\s*g\b", text, flags=re.IGNORECASE)
    if grams:
        return int(round(float(grams.group(1))))
    if raw is not None:
        return int(round(float(raw)))
    return None


def expected_value(constraint: HardConstraint) -> Any:
    if constraint.normalized_value is not None:
        return constraint.normalized_value
    return constraint.value


def derive_intent_status(intent: ShoppingIntent) -> IntentStatus:
    mandatory = [item for item in intent.ambiguities if item.appears_mandatory]
    if mandatory and not intent.hard_constraints and intent.category is None:
        return IntentStatus.UNSUPPORTED
    if mandatory:
        return IntentStatus.NEEDS_CLARIFICATION
    if not intent.hard_constraints and intent.category is None:
        return IntentStatus.NEEDS_CLARIFICATION
    return IntentStatus.READY


def normalize_intent(intent: ShoppingIntent) -> ShoppingIntent:
    """Fill normalized_value and unit on every hard constraint."""
    updated: list[HardConstraint] = []
    for constraint in intent.hard_constraints:
        value = constraint.value
        unit = constraint.unit
        if constraint.field == ConstraintField.PRICE:
            if constraint.unit != "AUD_CENTS":
                value = dollars_to_cents(constraint.value)
            unit = "AUD_CENTS"
        elif constraint.field == ConstraintField.WEIGHT_G:
            grams = normalize_weight_grams(constraint.source_phrase, constraint.value)
            if grams is not None:
                value = grams
            unit = "G"
        elif constraint.field == ConstraintField.BATTERY_HOURS:
            unit = "HOURS"
            value = float(constraint.value)
        elif constraint.field == ConstraintField.DELIVERY_DAYS:
            unit = "DAYS"
            value = int(constraint.value)
        elif constraint.field in {
            ConstraintField.ANC,
            ConstraintField.FOLDABLE,
            ConstraintField.WIRELESS,
            ConstraintField.MICROPHONE,
            ConstraintField.IN_STOCK,
            ConstraintField.SAME_DAY_DELIVERY,
        }:
            unit = "BOOL"
            value = bool(constraint.value)
        normalized_constraint = constraint.model_copy(
            update={"normalized_value": value, "value": value, "unit": unit}
        )
        updated.append(same_day_as_delivery_days(normalized_constraint))

    # Collapse duplicate delivery constraints (today + delivered today).
    collapsed: list[HardConstraint] = []
    seen: set[tuple[str, str, str]] = set()
    for constraint in updated:
        key = (
            constraint.field.value,
            constraint.operator.value,
            repr(constraint.normalized_value),
        )
        if key in seen:
            continue
        seen.add(key)
        collapsed.append(constraint)

    normalized = intent.model_copy(update={"hard_constraints": collapsed})
    normalized.status = derive_intent_status(normalized)
    return normalized


def same_day_as_delivery_days(constraint: HardConstraint) -> HardConstraint:
    """Map same_day_delivery=true to delivery_days LTE 0."""
    if (
        constraint.field == ConstraintField.SAME_DAY_DELIVERY
        and constraint.operator == ConstraintOperator.EQ
        and bool(expected_value(constraint)) is True
    ):
        return constraint.model_copy(
            update={
                "field": ConstraintField.DELIVERY_DAYS,
                "operator": ConstraintOperator.LTE,
                "value": 0,
                "normalized_value": 0,
                "unit": "DAYS",
            }
        )
    return constraint

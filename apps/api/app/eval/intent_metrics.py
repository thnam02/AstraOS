"""Normalized intent-evaluation metrics. Not commercial scores."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.decision.intent.models import ShoppingIntent
from app.decision.intent.normalizer import dollars_to_cents
from app.eval.metrics import set_f1


def _norm_value(field: str, operator: str, value: Any) -> Any:
    if field == "price":
        try:
            return dollars_to_cents(value)
        except (TypeError, ValueError):
            return value
    if field == "brand" and isinstance(value, str):
        return value.strip().lower()
    if field in {
        "anc",
        "wireless",
        "foldable",
        "microphone",
        "in_stock",
        "same_day_delivery",
    }:
        return bool(value)
    if field == "delivery_days":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    return value


def constraint_tuple(item: dict[str, Any] | Any) -> tuple[str, str, Any]:
    if isinstance(item, dict):
        field = str(item.get("field"))
        operator = str(item.get("operator"))
        value = item.get("normalized_value", item.get("value"))
    else:
        field = item.field.value
        operator = item.operator.value
        value = (
            item.normalized_value
            if item.normalized_value is not None
            else item.value
        )
    return (field, operator, _norm_value(field, operator, value))


def predicted_sets(intent: ShoppingIntent) -> dict[str, set[str]]:
    constraints = {constraint_tuple(item) for item in intent.hard_constraints}
    return {
        "hard": {f"{field}|{op}|{value}" for field, op, value in constraints},
        "hard_fields": {item.field.value for item in intent.hard_constraints},
        "preferences": {item.field.value for item in intent.soft_preferences},
        "contexts": {item.label.value for item in intent.context_items}
        | set(intent.context_tags),
        "outcomes": {item.label.value for item in intent.desired_outcomes},
        "values": {item.field.value for item in intent.values},
        "tradeoffs": {
            f"{item.preferred_dimension.value}>{item.over_dimension.value}"
            for item in intent.tradeoffs
        },
        "ambiguities": {
            item.reason for item in intent.ambiguities if item.reason
        },
        "unsupported": {
            item.label for item in intent.unsupported_semantic_needs if item.label
        },
    }


def gold_sets(case: dict[str, Any]) -> dict[str, set[str]]:
    gold = case.get("gold") or {}
    hard = {
        f"{field}|{op}|{value}"
        for field, op, value in (
            constraint_tuple(item) for item in gold.get("hard_constraints") or []
        )
    }
    return {
        "hard": hard,
        "hard_fields": {
            str(item.get("field")) for item in gold.get("hard_constraints") or []
        },
        "preferences": set(gold.get("soft_preferences") or []),
        "contexts": set(gold.get("contexts") or []),
        "outcomes": set(gold.get("outcomes") or []),
        "values": set(gold.get("values") or []),
        "tradeoffs": set(gold.get("tradeoffs") or []),
        "ambiguities": set(gold.get("ambiguities") or []),
        "unsupported": set(gold.get("unsupported_semantic_needs") or []),
    }


def score_case(intent: ShoppingIntent, case: dict[str, Any]) -> dict[str, Any]:
    predicted = predicted_sets(intent)
    gold = gold_sets(case)
    report: dict[str, Any] = {
        key: set_f1(predicted[key], gold[key])
        for key in (
            "hard",
            "preferences",
            "contexts",
            "outcomes",
            "values",
            "tradeoffs",
            "ambiguities",
            "unsupported",
        )
    }
    extra_fields = predicted["hard_fields"] - gold["hard_fields"]
    critical = set(case.get("critical_hard_fields") or gold["hard_fields"])
    omitted = critical - predicted["hard_fields"]
    report["hard_false_positives"] = sorted(extra_fields)
    report["critical_omissions"] = sorted(omitted)
    report["hard_field_false_positive"] = bool(extra_fields)
    report["critical_omission"] = bool(omitted)
    return report


def mean(values: Iterable[float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return sum(items) / len(items)

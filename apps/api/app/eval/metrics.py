"""Evaluation metrics for intent extraction and semantic matching."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.intent.models import ShoppingIntent
from app.decision.retrieval.models import RankedProductMatch
from app.eval.cases import EvalCase


def set_f1(predicted: set[str], gold: set[str]) -> dict[str, float]:
    if not gold and not predicted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not gold:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
    if not predicted:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    tp = len(predicted & gold)
    precision = tp / len(predicted)
    recall = tp / len(gold)
    f1 = (
        0.0
        if precision + recall == 0
        else 2 * precision * recall / (precision + recall)
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def intent_sets(intent: ShoppingIntent) -> dict[str, set[str]]:
    tradeoffs = {
        f"{item.preferred_dimension.value}>{item.over_dimension.value}"
        for item in intent.tradeoffs
    }
    return {
        "constraints": {item.field.value for item in intent.hard_constraints},
        "contexts": {item.label.value for item in intent.context_items}
        | set(intent.context_tags),
        "outcomes": {item.label.value for item in intent.desired_outcomes},
        "preferences": {item.field.value for item in intent.soft_preferences},
        "tradeoffs": tradeoffs,
    }


def score_extraction(
    intent: ShoppingIntent, case: EvalCase
) -> dict[str, dict[str, float]]:
    predicted = intent_sets(intent)
    return {
        "constraints": set_f1(predicted["constraints"], case.gold_constraint_fields),
        "contexts": set_f1(predicted["contexts"], case.gold_contexts),
        "outcomes": set_f1(predicted["outcomes"], case.gold_outcomes),
        "preferences": set_f1(predicted["preferences"], case.gold_preferences),
        "tradeoffs": set_f1(predicted["tradeoffs"], case.gold_tradeoffs),
    }


def relevance_grade(snapshot: VariantSnapshot, spec: dict[str, Any]) -> float:
    attrs = snapshot.attributes
    if spec.get("anc") is True and attrs.get("anc") is not True:
        return 0.0
    if spec.get("wireless") is True and attrs.get("wireless") is not True:
        return 0.0
    if spec.get("foldable") is True and attrs.get("foldable") is not True:
        return 0.0
    if spec.get("microphone") is True and attrs.get("microphone") is not True:
        return 0.0
    if spec.get("has_water") and not attrs.get("water_resistance"):
        return 0.0
    max_price = spec.get("max_price_cents")
    if max_price is not None and snapshot.base_price_cents >= int(max_price):
        return 0.0
    min_battery = spec.get("min_battery")
    if min_battery is not None:
        battery = attrs.get("battery_hours")
        if battery is None or float(battery) < float(min_battery):
            return 0.0
    min_travel = spec.get("min_travel_score")
    if min_travel is not None:
        travel = attrs.get("travel_score")
        if travel is None or float(travel) < float(min_travel):
            return 0.0
    if spec.get("same_day") is True:
        ok = any(
            option.available and option.enabled and option.days == 0
            for option in snapshot.deliveries
        )
        if not ok:
            return 0.0
    grade = spec.get("grade")
    if grade == "travel_score":
        return float(attrs.get("travel_score") or 0.0)
    if grade == "comfort_score":
        return float(attrs.get("comfort_score") or 0.0)
    if grade == "battery_hours":
        return min(float(attrs.get("battery_hours") or 0.0) / 80.0, 1.0)
    if grade == "weight_inv":
        weight = attrs.get("weight_g")
        if weight is None:
            return 0.2
        return max(0.0, min(1.0, (420 - float(weight)) / 240))
    return 1.0


def recall_at_k(
    ranked: Sequence[RankedProductMatch],
    relevant: set[str],
    k: int,
) -> float:
    if not relevant:
        return 1.0
    top = {str(item.variant_id) for item in ranked[:k]}
    return len(top & relevant) / len(relevant)


def ndcg_at_k(
    ranked: Sequence[RankedProductMatch],
    grades: dict[str, float],
    k: int,
) -> float:
    if not grades:
        return 1.0
    import math

    def dcg(values: list[float]) -> float:
        total = 0.0
        for index, value in enumerate(values, start=1):
            total += value / math.log2(index + 1)
        return total

    gained = [grades.get(str(item.variant_id), 0.0) for item in ranked[:k]]
    ideal = sorted(grades.values(), reverse=True)[:k]
    denom = dcg(ideal)
    if denom == 0:
        return 0.0
    return dcg(gained) / denom


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)

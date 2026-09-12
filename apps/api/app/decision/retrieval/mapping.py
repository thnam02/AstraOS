"""MVP ontology: merchant facts that support semantic needs.

This is not universal truth. It is an explicit, testable mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.intent.models import PreferenceField, ShoppingIntent
from app.decision.intent.taxonomy import ContextLabel, OutcomeLabel

Direction = Literal["MAXIMIZE", "MINIMIZE", "TRUE", "PRESENT"]


@dataclass(frozen=True)
class FeatureSupport:
    attribute: str
    direction: Direction
    weight: float
    display: str


@dataclass
class SupportHit:
    attribute: str
    value: Any
    display: str
    score: float
    weight: float


# Reasonable ranges from the Stage 1 headphone seed.
_RANGES: dict[str, tuple[float, float]] = {
    "battery_hours": (15.0, 80.0),
    "weight_g": (180.0, 420.0),
    "comfort_score": (0.0, 1.0),
    "travel_score": (0.0, 1.0),
}

CONTEXT_SUPPORT: dict[str, list[FeatureSupport]] = {
    ContextLabel.LONG_HAUL_TRAVEL.value: [
        FeatureSupport("anc", "TRUE", 0.25, "ANC"),
        FeatureSupport("battery_hours", "MAXIMIZE", 0.25, "battery hours"),
        FeatureSupport("weight_g", "MINIMIZE", 0.15, "weight"),
        FeatureSupport("foldable", "TRUE", 0.15, "foldable"),
        FeatureSupport("travel_score", "MAXIMIZE", 0.20, "travel score"),
    ],
    ContextLabel.EXTENDED_CONTINUOUS_USE.value: [
        FeatureSupport("comfort_score", "MAXIMIZE", 0.55, "comfort score"),
        FeatureSupport("weight_g", "MINIMIZE", 0.25, "weight"),
        FeatureSupport("battery_hours", "MAXIMIZE", 0.20, "battery hours"),
    ],
    ContextLabel.COMMUTING.value: [
        FeatureSupport("anc", "TRUE", 0.35, "ANC"),
        FeatureSupport("foldable", "TRUE", 0.25, "foldable"),
        FeatureSupport("weight_g", "MINIMIZE", 0.25, "weight"),
        FeatureSupport("wireless", "TRUE", 0.15, "wireless"),
    ],
    ContextLabel.GAMING.value: [
        FeatureSupport("microphone", "TRUE", 0.4, "microphone"),
        FeatureSupport("comfort_score", "MAXIMIZE", 0.35, "comfort score"),
        FeatureSupport("wireless", "TRUE", 0.25, "wireless"),
    ],
    ContextLabel.STUDIO.value: [
        FeatureSupport("comfort_score", "MAXIMIZE", 0.5, "comfort score"),
        FeatureSupport("wireless", "TRUE", 0.2, "wireless"),
        FeatureSupport("microphone", "TRUE", 0.3, "microphone"),
    ],
    ContextLabel.SPORTS.value: [
        FeatureSupport("water_resistance", "PRESENT", 0.45, "water resistance"),
        FeatureSupport("weight_g", "MINIMIZE", 0.35, "weight"),
        FeatureSupport("wireless", "TRUE", 0.20, "wireless"),
    ],
    ContextLabel.OFFICE.value: [
        FeatureSupport("microphone", "TRUE", 0.4, "microphone"),
        FeatureSupport("anc", "TRUE", 0.3, "ANC"),
        FeatureSupport("comfort_score", "MAXIMIZE", 0.3, "comfort score"),
    ],
    ContextLabel.FREQUENT_TRAVEL.value: [
        FeatureSupport("foldable", "TRUE", 0.3, "foldable"),
        FeatureSupport("travel_score", "MAXIMIZE", 0.3, "travel score"),
        FeatureSupport("weight_g", "MINIMIZE", 0.2, "weight"),
        FeatureSupport("anc", "TRUE", 0.2, "ANC"),
    ],
    ContextLabel.SHORT_TRAVEL.value: [
        FeatureSupport("foldable", "TRUE", 0.4, "foldable"),
        FeatureSupport("weight_g", "MINIMIZE", 0.4, "weight"),
        FeatureSupport("wireless", "TRUE", 0.2, "wireless"),
    ],
}

OUTCOME_SUPPORT: dict[str, list[FeatureSupport]] = {
    OutcomeLabel.LOW_FATIGUE.value: [
        FeatureSupport("comfort_score", "MAXIMIZE", 0.65, "comfort score"),
        FeatureSupport("weight_g", "MINIMIZE", 0.35, "weight"),
    ],
    OutcomeLabel.STRONG_NOISE_ISOLATION.value: [
        FeatureSupport("anc", "TRUE", 1.0, "ANC"),
    ],
    OutcomeLabel.LONG_BATTERY_ENDURANCE.value: [
        FeatureSupport("battery_hours", "MAXIMIZE", 1.0, "battery hours"),
    ],
    OutcomeLabel.RELIABLE_EXTENDED_USE.value: [
        FeatureSupport("battery_hours", "MAXIMIZE", 0.55, "battery hours"),
        FeatureSupport("anc", "TRUE", 0.25, "ANC"),
        FeatureSupport("comfort_score", "MAXIMIZE", 0.20, "comfort score"),
    ],
    OutcomeLabel.PORTABLE_TRAVEL.value: [
        FeatureSupport("weight_g", "MINIMIZE", 0.4, "weight"),
        FeatureSupport("foldable", "TRUE", 0.4, "foldable"),
        FeatureSupport("wireless", "TRUE", 0.2, "wireless"),
    ],
    OutcomeLabel.CLEAR_CALLS.value: [
        FeatureSupport("microphone", "TRUE", 1.0, "microphone"),
    ],
    OutcomeLabel.IMMERSIVE_AUDIO.value: [
        FeatureSupport("anc", "TRUE", 0.5, "ANC"),
        FeatureSupport("comfort_score", "MAXIMIZE", 0.5, "comfort score"),
    ],
    OutcomeLabel.EASY_STORAGE.value: [
        FeatureSupport("foldable", "TRUE", 1.0, "foldable"),
    ],
    OutcomeLabel.WEATHER_RESILIENCE.value: [
        FeatureSupport("water_resistance", "PRESENT", 1.0, "water resistance"),
    ],
    OutcomeLabel.TRAVEL_CONVENIENCE.value: [
        FeatureSupport("same_day", "TRUE", 0.35, "same-day delivery"),
        FeatureSupport("foldable", "TRUE", 0.35, "foldable"),
        FeatureSupport("wireless", "TRUE", 0.30, "wireless"),
    ],
}

PREFERENCE_SUPPORT: dict[str, list[FeatureSupport]] = {
    PreferenceField.COMFORT.value: [
        FeatureSupport("comfort_score", "MAXIMIZE", 1.0, "comfort score"),
    ],
    PreferenceField.RELIABILITY.value: [
        FeatureSupport("battery_hours", "MAXIMIZE", 0.6, "battery hours"),
        FeatureSupport("anc", "TRUE", 0.4, "ANC"),
    ],
    PreferenceField.TRAVEL.value: [
        FeatureSupport("travel_score", "MAXIMIZE", 1.0, "travel score"),
    ],
    PreferenceField.BATTERY.value: [
        FeatureSupport("battery_hours", "MAXIMIZE", 1.0, "battery hours"),
    ],
    PreferenceField.WEIGHT.value: [
        FeatureSupport("weight_g", "MINIMIZE", 1.0, "weight"),
    ],
    PreferenceField.DELIVERY.value: [
        FeatureSupport("same_day", "TRUE", 1.0, "same-day delivery"),
    ],
}


def observe_attribute(snapshot: VariantSnapshot, name: str) -> Any:
    if name == "same_day":
        if not snapshot.deliveries:
            return None
        return any(
            option.available and option.enabled and option.days == 0
            for option in snapshot.deliveries
        )
    if name in snapshot.attributes:
        return snapshot.attributes.get(name)
    return None


def feature_score(value: Any, support: FeatureSupport) -> float | None:
    if value is None:
        return None
    if support.direction == "TRUE":
        return 1.0 if bool(value) else 0.0
    if support.direction == "PRESENT":
        return 1.0 if value not in {None, False, ""} else 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    low, high = _RANGES.get(support.attribute, (0.0, 1.0))
    if high == low:
        return 0.5
    if support.direction == "MINIMIZE":
        return float(np_clip((high - number) / (high - low)))
    return float(np_clip((number - low) / (high - low)))


def np_clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def support_hits(
    snapshot: VariantSnapshot, features: list[FeatureSupport]
) -> list[SupportHit]:
    hits: list[SupportHit] = []
    for feature in features:
        value = observe_attribute(snapshot, feature.attribute)
        score = feature_score(value, feature)
        if score is None:
            continue
        hits.append(
            SupportHit(
                attribute=feature.attribute,
                value=value,
                display=feature.display,
                score=score,
                weight=feature.weight,
            )
        )
    return hits


def weighted_score(hits: list[SupportHit]) -> float | None:
    if not hits:
        return None
    total = sum(hit.weight for hit in hits)
    if total <= 0:
        return None
    return sum(hit.score * hit.weight for hit in hits) / total


def semantic_needs(intent: ShoppingIntent) -> list[tuple[str, str, float]]:
    """Return (kind, label, importance) for coverage and rerank."""
    needs: list[tuple[str, str, float]] = []
    for context in intent.context_items:
        needs.append(("context", context.label.value, context.importance))
    for outcome in intent.desired_outcomes:
        needs.append(("outcome", outcome.label.value, outcome.importance))
    for pref in intent.soft_preferences:
        if pref.field.value != "price":
            needs.append(("preference", pref.field.value, pref.importance))
    for value in intent.values:
        needs.append(("value", value.field.value, value.importance))
    for extra in intent.unsupported_semantic_needs:
        needs.append(("unsupported", extra.label, 0.5))
    return needs


def features_for(kind: str, label: str) -> list[FeatureSupport]:
    if kind == "context":
        return CONTEXT_SUPPORT.get(label, [])
    if kind == "outcome":
        return OUTCOME_SUPPORT.get(label, [])
    if kind == "preference":
        return PREFERENCE_SUPPORT.get(label, [])
    return []

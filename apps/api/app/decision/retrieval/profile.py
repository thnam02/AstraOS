"""Intent semantic profile. Hard constraints stay out of the ranking text."""

from __future__ import annotations

from dataclasses import dataclass

from app.decision.intent.models import ShoppingIntent
from app.decision.intent.taxonomy import TradeoffDimension

PROFILE_VERSION = "intent_semantic.v1"

_LABELS = {
    "long_haul_travel": "Long-haul travel",
    "short_travel": "Short travel",
    "commuting": "Commuting",
    "office": "Office use",
    "gaming": "Gaming",
    "studio": "Studio work",
    "sports": "Sports",
    "frequent_travel": "Frequent travel",
    "extended_continuous_use": "Extended continuous use",
    "low_fatigue": "Low fatigue",
    "strong_noise_isolation": "Strong noise isolation",
    "long_battery_endurance": "Long battery endurance",
    "reliable_extended_use": "Reliable extended use",
    "portable_travel": "Portable travel",
    "clear_calls": "Clear calls",
    "immersive_audio": "Immersive audio",
    "easy_storage": "Easy storage",
    "weather_resilience": "Weather resilience",
    "travel_convenience": "Travel convenience",
    "comfort": "Comfort",
    "reliability": "Reliability",
    "price": "minimum price",
    "battery": "Battery",
    "weight": "Weight",
    "travel": "Travel suitability",
    "delivery": "Delivery speed",
    "warranty": "Warranty",
}


@dataclass
class IntentSemanticProfile:
    version: str
    text: str
    needs: list[str]


def build_intent_profile(intent: ShoppingIntent) -> IntentSemanticProfile:
    """Describe the human problem, not the hard filters already enforced."""
    lines: list[str] = []
    needs: list[str] = []
    for context in intent.context_items:
        lines.append(f"{_LABELS.get(context.label.value, context.label.value)}.")
        needs.append(f"context:{context.label.value}")
    for outcome in intent.desired_outcomes:
        lines.append(f"{_LABELS.get(outcome.label.value, outcome.label.value)}.")
        needs.append(f"outcome:{outcome.label.value}")
    for pref in intent.soft_preferences:
        qualifier = "high" if pref.importance >= 0.7 else "medium"
        if pref.field.value == "price" and pref.importance <= 0.4:
            qualifier = "medium"
        lines.append(f"{_LABELS.get(pref.field.value, pref.field.value)} {qualifier}.")
        needs.append(f"preference:{pref.field.value}")
    for value in intent.values:
        lines.append(f"{value.field.value} matters.")
        needs.append(f"value:{value.field.value}")
    for tradeoff in intent.tradeoffs:
        preferred = _LABELS.get(
            tradeoff.preferred_dimension.value, tradeoff.preferred_dimension.value
        )
        over = _LABELS.get(tradeoff.over_dimension.value, tradeoff.over_dimension.value)
        if tradeoff.over_dimension == TradeoffDimension.PRICE:
            over = "minimum price"
        lines.append(f"{preferred} is more important than {over}.")
        needs.append(
            f"tradeoff:{tradeoff.preferred_dimension.value}>{tradeoff.over_dimension.value}"
        )
    text = "\n".join(lines).strip()
    return IntentSemanticProfile(version=PROFILE_VERSION, text=text, needs=needs)

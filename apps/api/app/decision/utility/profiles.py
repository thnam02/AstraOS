"""Transparent simulation profiles. Scenario assumptions, not learned behaviour."""

from app.decision.utility.models import UtilityWeights

PROFILE_BALANCED = "BALANCED"
PROFILE_URGENT = "URGENT_TRAVELLER"
PROFILE_BUDGET = "BUDGET_SHOPPER"
PROFILE_ASSURANCE = "ASSURANCE_BUYER"
PROFILE_QUALITY = "QUALITY_FIRST"
PROFILE_INTENT = "INTENT_ADAPTED"

PROFILES: dict[str, UtilityWeights] = {
    PROFILE_BALANCED: UtilityWeights(
        product=0.30,
        price=0.20,
        delivery=0.15,
        warranty=0.15,
        bundle=0.10,
        returns=0.10,
    ),
    PROFILE_URGENT: UtilityWeights(
        product=0.30,
        price=0.10,
        delivery=0.30,
        warranty=0.10,
        bundle=0.10,
        returns=0.10,
    ),
    PROFILE_BUDGET: UtilityWeights(
        product=0.20,
        price=0.40,
        delivery=0.10,
        warranty=0.10,
        bundle=0.10,
        returns=0.10,
    ),
    PROFILE_ASSURANCE: UtilityWeights(
        product=0.25,
        price=0.10,
        delivery=0.10,
        warranty=0.30,
        bundle=0.10,
        returns=0.15,
    ),
    PROFILE_QUALITY: UtilityWeights(
        product=0.45,
        price=0.10,
        delivery=0.10,
        warranty=0.15,
        bundle=0.10,
        returns=0.10,
    ),
}

PROFILE_LABELS = {
    PROFILE_INTENT: "Intent-adapted",
    PROFILE_BALANCED: "Balanced",
    PROFILE_URGENT: "Urgent traveller",
    PROFILE_BUDGET: "Budget shopper",
    PROFILE_ASSURANCE: "Assurance",
    PROFILE_QUALITY: "Quality first",
}


def get_profile(profile_id: str) -> UtilityWeights:
    key = profile_id if profile_id in PROFILES else PROFILE_BALANCED
    return PROFILES[key].model_copy()


def normalize_weights(raw: dict[str, float]) -> UtilityWeights:
    keys = ("product", "price", "delivery", "warranty", "bundle", "returns")
    clipped = {key: max(0.0, float(raw.get(key, 0.0))) for key in keys}
    total = sum(clipped.values())
    if total <= 0:
        return get_profile(PROFILE_BALANCED)
    scaled = {key: value / total for key, value in clipped.items()}
    return UtilityWeights(**scaled)

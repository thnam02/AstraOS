"""Deterministic offer-feature → fit mappings. No LLM calls."""

from app.decision.economics.normalization import clamp01
from app.decision.intent.models import (
    ConstraintField,
    PreferenceField,
    ShoppingIntent,
)
from app.decision.offers.bundles import bundle_is_context_relevant
from app.decision.offers.models import OfferCandidate
from app.decision.utility.models import FitComponents, UtilityWeights
from app.decision.utility.profiles import (
    PROFILE_INTENT,
    PROFILE_URGENT,
    get_profile,
    normalize_weights,
)

_DELIVERY_PREF_LABELS = {
    "long_haul_travel",
    "short_travel",
    "frequent_travel",
    "extended_continuous_use",
}

_TRADEOFF_TO_WEIGHT = {
    "comfort": "product",
    "reliability": "warranty",
    "price": "price",
    "battery": "product",
    "weight": "product",
    "travel": "bundle",
    "delivery": "delivery",
    "warranty": "warranty",
}

_PREF_TO_WEIGHT = {
    PreferenceField.COMFORT: "product",
    PreferenceField.TRAVEL: "bundle",
    PreferenceField.RELIABILITY: "warranty",
    PreferenceField.PRICE: "price",
    PreferenceField.BATTERY: "product",
    PreferenceField.WEIGHT: "product",
    PreferenceField.DELIVERY: "delivery",
    PreferenceField.WARRANTY: "warranty",
}


def intent_labels(intent: ShoppingIntent) -> set[str]:
    labels = {item.label.value for item in intent.context_items}
    labels.update(item.label.value for item in intent.desired_outcomes)
    labels.update(intent.context_tags)
    return labels


def resolve_weights(intent: ShoppingIntent, profile_id: str) -> UtilityWeights:
    """IntentWeightResolver. Deterministic; never asks an LLM for weights."""
    if profile_id != PROFILE_INTENT:
        return get_profile(profile_id)

    hard = {item.field for item in intent.hard_constraints}
    labels = intent_labels(intent)
    urgent = (
        ConstraintField.DELIVERY_DAYS in hard
        or ConstraintField.SAME_DAY_DELIVERY in hard
        or bool(labels & _DELIVERY_PREF_LABELS)
    )
    weights = get_profile(PROFILE_URGENT if urgent else "BALANCED").as_dict()

    for tradeoff in intent.tradeoffs:
        preferred = _TRADEOFF_TO_WEIGHT.get(tradeoff.preferred_dimension.value)
        over = _TRADEOFF_TO_WEIGHT.get(tradeoff.over_dimension.value)
        delta = 0.08 * tradeoff.strength
        if preferred:
            weights[preferred] += delta
        if over:
            weights[over] = max(0.02, weights[over] - delta)

    for pref in intent.soft_preferences:
        key = _PREF_TO_WEIGHT.get(pref.field)
        if key is None:
            continue
        bump = 0.05 * pref.importance
        if pref.field == PreferenceField.PRICE:
            weights["price"] += bump
        else:
            weights[key] += bump

    return normalize_weights(weights)


def price_fit(
    price_cents: int,
    *,
    low_cents: int,
    high_cents: int,
    budget_cents: int | None,
) -> float:
    """Lower price is better. Range-normalized; budget is a secondary pull.

    If every offer shares a price, fit is 1. Documented, no cliffs.
    """
    if high_cents <= low_cents:
        range_fit = 1.0
    else:
        range_fit = (high_cents - price_cents) / (high_cents - low_cents)
    if budget_cents and budget_cents > 0:
        budget_fit = clamp01(1.0 - (price_cents / budget_cents))
        return clamp01(0.7 * range_fit + 0.3 * budget_fit)
    return clamp01(range_fit)


def delivery_fit(days: int, intent: ShoppingIntent) -> float:
    """Faster delivery scores higher when the request cares about timing."""
    labels = intent_labels(intent)
    hard = {item.field for item in intent.hard_constraints}
    cares = (
        ConstraintField.DELIVERY_DAYS in hard
        or ConstraintField.SAME_DAY_DELIVERY in hard
        or bool(labels & _DELIVERY_PREF_LABELS)
        or any(
            item.field == PreferenceField.DELIVERY
            for item in intent.soft_preferences
        )
    )
    if days <= 0:
        score = 1.0
    elif days == 1:
        score = 0.7
    elif days == 2:
        score = 0.35
    else:
        score = clamp01(1.0 - days / 7.0)
    if not cares:
        # Flatten: delivery still differs, but weakly.
        return clamp01(0.65 + 0.35 * score)
    return score


def warranty_fit(months: int, intent: ShoppingIntent) -> float:
    if months >= 36:
        score = 1.0
    elif months >= 24:
        score = 0.75
    elif months >= 12:
        score = 0.40
    else:
        score = 0.20
    cares = any(
        item.field in {PreferenceField.WARRANTY, PreferenceField.RELIABILITY}
        for item in intent.soft_preferences
    ) or any(
        item.preferred_dimension.value in {"warranty", "reliability"}
        for item in intent.tradeoffs
    )
    if not cares:
        return clamp01(0.55 + 0.30 * score)
    return score


def bundle_fit(offer: OfferCandidate, intent: ShoppingIntent) -> float:
    if not offer.bundle_code:
        return 0.50
    if bundle_is_context_relevant(offer.bundle_code, intent):
        return 0.90
    return 0.20


def returns_fit(window_days: int | None, intent: ShoppingIntent) -> float:
    days = int(window_days or 30)
    cares = any(
        item.field == PreferenceField.RELIABILITY for item in intent.soft_preferences
    ) or any(item.field.value == "durability" for item in intent.values)
    if days >= 60:
        return 0.85 if cares else 0.60
    if days >= 30:
        return 0.50
    return 0.30


def budget_cents(intent: ShoppingIntent) -> int | None:
    for item in intent.hard_constraints:
        if item.field != ConstraintField.PRICE:
            continue
        value = (
            item.normalized_value
            if item.normalized_value is not None
            else item.value
        )
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
    return None


def fit_components(
    offer: OfferCandidate,
    *,
    intent: ShoppingIntent,
    product_fit_score: float,
    price_low: int,
    price_high: int,
) -> FitComponents:
    return FitComponents(
        product=clamp01(product_fit_score),
        price=price_fit(
            offer.total_customer_price_cents,
            low_cents=price_low,
            high_cents=price_high,
            budget_cents=budget_cents(intent),
        ),
        delivery=delivery_fit(offer.delivery_days, intent),
        warranty=warranty_fit(offer.warranty_months, intent),
        bundle=bundle_fit(offer, intent),
        returns=returns_fit(offer.return_window_days, intent),
    )

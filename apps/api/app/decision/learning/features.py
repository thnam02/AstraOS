"""Pre-outcome features. The Stage 5 utility total is never a feature."""

from typing import Any

from app.decision.intent.models import ConstraintField, PreferenceField, ShoppingIntent
from app.decision.learning import FEATURE_SCHEMA_VERSION
from app.decision.offers.models import OfferCandidate
from app.decision.optimisation.models import ScoredOffer
from app.decision.retrieval.models import RankedProductMatch
from app.decision.utility.models import UtilityWeights

NUMERIC_FEATURES: tuple[str, ...] = (
    "w_product",
    "w_price",
    "w_delivery",
    "w_warranty",
    "w_bundle",
    "w_returns",
    "comfort_importance",
    "reliability_importance",
    "warranty_importance",
    "price_importance",
    "has_long_haul",
    "has_commuting",
    "has_gaming",
    "has_studio",
    "product_fit",
    "context_fit",
    "preference_fit",
    "evidence_coverage",
    "total_price_cents",
    "budget_headroom",
    "delivery_days",
    "is_same_day",
    "warranty_months",
    "bundle_present",
    "return_window_days",
    "discount_rate",
    "contribution_margin_rate",
    "intervention_cost_cents",
    "price_x_price_importance",
    "delivery_x_delivery_importance",
    "warranty_x_warranty_importance",
    "fit_x_product_importance",
)

CATEGORICAL_FEATURES: tuple[str, ...] = ("buyer_profile", "delivery_code")

FEATURE_NAMES: tuple[str, ...] = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _pref(intent: ShoppingIntent, field: PreferenceField) -> float:
    hits = [item.importance for item in intent.soft_preferences if item.field == field]
    return max(hits) if hits else 0.0


def _budget_cents(intent: ShoppingIntent) -> int | None:
    for constraint in intent.hard_constraints:
        if constraint.field == ConstraintField.PRICE:
            value = constraint.normalized_value or constraint.value
            if isinstance(value, int):
                return value
    return None


def _context_flag(intent: ShoppingIntent, *needles: str) -> float:
    blob = " ".join(intent.context_tags)
    blob += " " + " ".join(item.label.value for item in intent.context_items)
    return 1.0 if any(needle in blob for needle in needles) else 0.0


def extract_features(
    *,
    intent: ShoppingIntent,
    weights: UtilityWeights,
    scored: ScoredOffer,
    offer: OfferCandidate,
    match: RankedProductMatch | None,
    buyer_profile: str,
) -> dict[str, Any]:
    """Build a pre-outcome feature row. Must not include the utility total."""
    budget = _budget_cents(intent)
    price = scored.total_customer_price_cents
    headroom = 0.0
    if budget and budget > 0:
        headroom = (budget - price) / budget
    w = weights.as_dict()
    delivery_speed = 1.0 / (1.0 + max(scored.delivery_days, 0))
    comfort = _pref(intent, PreferenceField.COMFORT)
    reliability = _pref(intent, PreferenceField.RELIABILITY)
    warranty_imp = _pref(intent, PreferenceField.WARRANTY)
    price_imp = _pref(intent, PreferenceField.PRICE)
    product_fit = match.product_fit if match is not None else scored.product_fit
    context_fit = match.context_fit if match is not None else 0.0
    preference_fit = match.preference_fit if match is not None else 0.0
    evidence = match.evidence_coverage if match is not None else 0.0
    margin = float(scored.economics.contribution_margin_rate)
    return {
        "w_product": w["product"],
        "w_price": w["price"],
        "w_delivery": w["delivery"],
        "w_warranty": w["warranty"],
        "w_bundle": w["bundle"],
        "w_returns": w["returns"],
        "comfort_importance": comfort,
        "reliability_importance": reliability,
        "warranty_importance": warranty_imp,
        "price_importance": price_imp,
        "has_long_haul": _context_flag(intent, "long_haul"),
        "has_commuting": _context_flag(intent, "commuting"),
        "has_gaming": _context_flag(intent, "gaming"),
        "has_studio": _context_flag(intent, "studio"),
        "product_fit": product_fit,
        "context_fit": context_fit,
        "preference_fit": preference_fit,
        "evidence_coverage": evidence,
        "total_price_cents": float(price),
        "budget_headroom": headroom,
        "delivery_days": float(scored.delivery_days),
        "is_same_day": 1.0 if scored.delivery_days <= 0 else 0.0,
        "warranty_months": float(scored.warranty_months),
        "bundle_present": 1.0 if scored.bundle_code else 0.0,
        "return_window_days": float(scored.return_window_days or 30),
        "discount_rate": float(offer.price_adjustment_rate),
        "contribution_margin_rate": margin,
        "intervention_cost_cents": float(
            scored.economics.incremental_intervention_cost_cents
        ),
        "price_x_price_importance": (1.0 - min(max(headroom, -1.0), 1.0))
        * max(w["price"], price_imp),
        "delivery_x_delivery_importance": delivery_speed * w["delivery"],
        "warranty_x_warranty_importance": (scored.warranty_months / 36.0)
        * max(w["warranty"], warranty_imp),
        "fit_x_product_importance": product_fit * w["product"],
        "buyer_profile": buyer_profile,
        "delivery_code": scored.delivery_code,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
    }

"""Simulated buyer utility is decomposable and deterministic."""

from app.decision.intent.models import (
    PreferenceDirection,
    PreferenceField,
    SoftPreference,
    TradeoffPreference,
)
from app.decision.intent.taxonomy import TradeoffDimension
from app.decision.utility.feature_mapping import (
    delivery_fit,
    price_fit,
    resolve_weights,
    warranty_fit,
)
from app.decision.utility.profiles import PROFILE_INTENT, PROFILES
from app.decision.utility.scorer import score_offer
from tests.offer_fixtures import travel_intent
from tests.qualification_fixtures import intent_with
from tests.test_economics import _offer


def test_profile_weights_sum_to_one() -> None:
    for weights in PROFILES.values():
        assert abs(weights.total() - 1.0) < 1e-9


def test_intent_adapted_boosts_delivery_and_cuts_price() -> None:
    intent = travel_intent()
    intent.tradeoffs.append(
        TradeoffPreference(
            preferred_dimension=TradeoffDimension.COMFORT,
            over_dimension=TradeoffDimension.PRICE,
            strength=0.8,
            source_phrase="comfort over cheapest",
        )
    )
    weights = resolve_weights(intent, PROFILE_INTENT)
    assert abs(weights.total() - 1.0) < 1e-9
    balanced = PROFILES["BALANCED"]
    assert weights.price < balanced.price
    assert weights.delivery > 0.2


def test_price_fit_prefers_lower() -> None:
    cheap = price_fit(30000, low_cents=30000, high_cents=35000, budget_cents=35000)
    dear = price_fit(35000, low_cents=30000, high_cents=35000, budget_cents=35000)
    assert cheap > dear
    assert 0 <= cheap <= 1
    assert 0 <= dear <= 1


def test_delivery_fit_same_day_highest() -> None:
    intent = travel_intent()
    assert delivery_fit(0, intent) > delivery_fit(1, intent) > delivery_fit(2, intent)


def test_warranty_fit_longer_higher_when_cared() -> None:
    intent = intent_with(
        soft_preferences=[
            SoftPreference(
                id="w",
                field=PreferenceField.WARRANTY,
                direction=PreferenceDirection.MAXIMIZE,
                importance=0.8,
                source_phrase="warranty",
            )
        ]
    )
    assert warranty_fit(36, intent) > warranty_fit(12, intent)


def test_score_decomposition_and_repeatability() -> None:
    offer = _offer(
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_merchant_cost_cents=800,
        delivery_customer_charge_cents=1000,
        total_customer_price_cents=33900,
    )
    intent = travel_intent()
    weights = resolve_weights(intent, PROFILE_INTENT)
    first = score_offer(
        offer,
        intent=intent,
        product_fit=0.91,
        price_low=30000,
        price_high=36000,
        weights=weights,
        profile_id=PROFILE_INTENT,
    )
    second = score_offer(
        offer,
        intent=intent,
        product_fit=0.91,
        price_low=30000,
        price_high=36000,
        weights=weights,
        profile_id=PROFILE_INTENT,
    )
    assert first.score == second.score
    weighted = sum(item.weighted for item in first.trace.components)
    assert abs(weighted - first.score) < 1e-6
    assert "probability" not in first.disclaimer.lower()
    assert first.score == first.trace.total

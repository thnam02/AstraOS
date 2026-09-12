"""Counteroffer search never promotes an unsafe offer."""

from uuid import uuid4

from app.decision.economics.calculator import compute_economics
from app.decision.negotiation.models import CounterConstraints, MerchantOutcome
from app.decision.negotiation.search import meets_request, search_counter
from app.decision.optimisation.models import ScoredOffer
from app.decision.policies.offer_policy_evaluator import OfferPolicyEvaluation
from app.decision.utility.models import (
    FitComponents,
    SimulatedBuyerUtility,
    UtilityTrace,
)
from app.decision.utility.profiles import PROFILES
from tests.test_economics import _offer


def _scored(*, price: int, safe: bool, variant=None, **kwargs: object) -> ScoredOffer:
    offer = _offer(total_customer_price_cents=price, **kwargs)
    eco = compute_economics(offer, cogs_cents=18000)
    utility = SimulatedBuyerUtility(
        score=0.7,
        fits=FitComponents(
            product=0.7,
            price=0.7,
            delivery=0.7,
            warranty=0.5,
            bundle=0.5,
            returns=0.5,
        ),
        weights=PROFILES["BALANCED"],
        trace=UtilityTrace(components=[], total=0.7),
        profile_id="BALANCED",
        disclaimer="sim",
    )
    return ScoredOffer(
        offer_id=offer.id,
        variant_id=variant or offer.variant_id,
        sku=offer.sku,
        product_name=offer.product_name,
        brand=offer.brand,
        product_price_cents=offer.final_product_price_cents,
        total_customer_price_cents=price,
        delivery_code=offer.delivery_code,
        delivery_name=offer.delivery_name,
        delivery_days=offer.delivery_days,
        warranty_code=offer.warranty_code,
        warranty_name=offer.warranty_name,
        warranty_months=offer.warranty_months,
        bundle_code=offer.bundle_code,
        bundle_name=offer.bundle_name,
        return_policy_code=offer.return_policy_code,
        return_window_days=30,
        economics=eco,
        policy=OfferPolicyEvaluation(
            policy_safe=safe, checks=[], rejection_codes=[]
        ),
        utility=utility,
        is_pareto_efficient=safe,
    )


def test_exact_counter_accepted() -> None:
    variant = uuid4()
    scored = [
        _scored(price=31900, safe=True, variant=variant),
        _scored(price=32900, safe=True, variant=variant),
    ]
    result = search_counter(
        scored,
        request=CounterConstraints(max_total_price_cents=32000),
        current_variant_id=variant,
    )
    assert result.outcome == MerchantOutcome.ACCEPT_BUYER_COUNTER
    assert result.offer is not None
    assert result.offer.total_customer_price_cents <= 32000


def test_impossible_price_counters() -> None:
    variant = uuid4()
    scored = [_scored(price=31900, safe=True, variant=variant)]
    result = search_counter(
        scored,
        request=CounterConstraints(max_total_price_cents=20000),
        current_variant_id=variant,
    )
    assert result.outcome == MerchantOutcome.COUNTEROFFER
    assert result.offer is not None
    assert result.offer.policy.policy_safe


def test_unsafe_never_selected() -> None:
    variant = uuid4()
    scored = [_scored(price=19900, safe=False, variant=variant)]
    result = search_counter(
        scored,
        request=CounterConstraints(max_total_price_cents=20000),
        current_variant_id=variant,
    )
    assert result.outcome == MerchantOutcome.DECLINE
    assert result.offer is None


def test_alternative_product() -> None:
    current = uuid4()
    other = uuid4()
    scored = [
        _scored(price=32900, safe=True, variant=current),
        _scored(price=27900, safe=True, variant=other, product_name="Nimbus"),
    ]
    result = search_counter(
        scored,
        request=CounterConstraints(max_total_price_cents=29000),
        current_variant_id=current,
    )
    assert result.outcome == MerchantOutcome.ALTERNATIVE_PRODUCT
    assert result.offer is not None
    assert result.offer.variant_id == other


def test_meets_request() -> None:
    offer = _scored(price=31900, safe=True)
    assert meets_request(offer, CounterConstraints(max_total_price_cents=31900))
    assert not meets_request(offer, CounterConstraints(max_total_price_cents=30000))

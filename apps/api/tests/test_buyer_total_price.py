"""Buyer max spend binds the complete offer, not only base catalogue price."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.intent.models import ConstraintField, ConstraintOperator, PriceBasis
from app.decision.intent.parser import parse_intent
from app.decision.negotiation.delta import apply_working_intent
from app.decision.negotiation.models import NegotiationDelta
from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant
from app.decision.offers.models import ConstructionLimits, FeasibilityStatus, RejectionCode
from app.decision.optimisation.engine import score_space
from app.decision.optimisation.explanation import explain_recommendation
from app.decision.transaction.models import TransactionFailureCode
from tests.offer_fixtures import wired_variant
from tests.qualification_fixtures import constraint, intent_with, snapshot
from tests.test_economics import _offer
from tests.test_revalidation import _pair, _policy, _run, _variant


def _budget_intent(
    cents: int = 10000,
    *,
    operator: ConstraintOperator = ConstraintOperator.LTE,
    applies_to: PriceBasis = PriceBasis.CUSTOMER_TOTAL,
    phrase: str = "under A$100",
    raw_text: str = "headphones under A$100",
):
    item = constraint(
        ConstraintField.PRICE,
        operator,
        cents,
        unit="AUD_CENTS",
        phrase=phrase,
    ).model_copy(update={"applies_to": applies_to})
    return intent_with(item, raw_text=raw_text)


def _priced_variant(
    *,
    base: int = 9200,
    same_day_charge: int = 0,
    warranty_price: int = 0,
    bundle_price: int = 0,
):
    variant, policy = wired_variant(base_price=base)
    variant.cogs_cents = 4000
    policy.minimum_margin_rate = Decimal("0.0500")
    for link in variant.delivery_options:
        charge = same_day_charge if link.delivery_option.code == "SAME_DAY" else 0
        link.delivery_option.customer_charge_cents = charge
    for link in variant.warranty_options:
        price = warranty_price if link.warranty_option.code == "EXTENDED_24" else 0
        link.warranty_option.customer_price_cents = price
    for link in variant.bundle_options:
        link.bundle_option.customer_price_cents = bundle_price
    return variant, policy


def _construct(intent, variant, policy):
    return construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=relevant_bundle_codes(intent),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )[0]


def _pick(offers, *, delivery: str, warranty: str, bundle: str | None):
    return next(
        item
        for item in offers
        if item.delivery_code == delivery
        and item.warranty_code == warranty
        and item.bundle_code == bundle
        and item.price_adjustment_type == "BASE"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text",
    [
        "headphones under A$100",
        "budget is A$100",
        "must cost less than A$100",
        "maximum A$100",
    ],
)
async def test_default_budget_language_is_customer_total(text: str) -> None:
    intent = await parse_intent(text)
    price = next(
        item for item in intent.hard_constraints if item.field == ConstraintField.PRICE
    )
    assert price.applies_to == PriceBasis.CUSTOMER_TOTAL
    assert price.normalized_value == 10000


@pytest.mark.asyncio
async def test_explicit_base_price_language() -> None:
    intent = await parse_intent(
        "base product price under A$100, extras are okay"
    )
    price = next(
        item for item in intent.hard_constraints if item.field == ConstraintField.PRICE
    )
    assert price.applies_to == PriceBasis.PRODUCT_BASE
    assert price.normalized_value == 10000


def test_qualification_uses_base_price_as_pruning_gate() -> None:
    evaluator = EligibilityEvaluator()
    intent = _budget_intent()
    cheap = evaluator.evaluate_variant(snapshot(price=9200), intent)
    expensive = evaluator.evaluate_variant(snapshot(price=12700), intent)
    assert cheap.eligible
    assert not expensive.eligible
    assert expensive.violated_count >= 1


def test_case_a_standard_total_under_cap_is_valid() -> None:
    intent = _budget_intent()
    variant, policy = _priced_variant(base=9200, same_day_charge=0, warranty_price=0)
    offer = _pick(
        _construct(intent, variant, policy),
        delivery="STANDARD",
        warranty="STANDARD_12",
        bundle=None,
    )
    assert offer.total_customer_price_cents == 9200
    assert offer.feasibility_status == FeasibilityStatus.FEASIBLE
    assert not any(
        item.code == RejectionCode.BUYER_MAX_TOTAL_EXCEEDED
        for item in offer.rejection_reasons
    )


def test_case_b_same_day_over_total_is_invalid() -> None:
    intent = _budget_intent()
    variant, policy = _priced_variant(base=9200, same_day_charge=1000)
    offer = _pick(
        _construct(intent, variant, policy),
        delivery="SAME_DAY",
        warranty="STANDARD_12",
        bundle=None,
    )
    assert offer.total_customer_price_cents == 10200
    assert offer.feasibility_status == FeasibilityStatus.FEASIBLE
    assert any(
        item.code == RejectionCode.BUYER_MAX_TOTAL_EXCEEDED
        for item in offer.rejection_reasons
    )


def test_case_c_warranty_over_total_is_invalid() -> None:
    intent = _budget_intent()
    variant, policy = _priced_variant(base=8000, warranty_price=2500)
    offer = _pick(
        _construct(intent, variant, policy),
        delivery="STANDARD",
        warranty="EXTENDED_24",
        bundle=None,
    )
    assert offer.total_customer_price_cents == 10500
    assert offer.feasibility_status == FeasibilityStatus.FEASIBLE
    assert any(
        item.code == RejectionCode.BUYER_MAX_TOTAL_EXCEEDED
        for item in offer.rejection_reasons
    )


def test_case_d_explicit_product_price_allows_extras() -> None:
    intent = _budget_intent(
        applies_to=PriceBasis.PRODUCT_BASE,
        phrase="base product price under A$100",
        raw_text="base product price under A$100, extras are okay",
    )
    variant, policy = _priced_variant(
        base=9200, same_day_charge=1000, warranty_price=2500
    )
    offer = _pick(
        _construct(intent, variant, policy),
        delivery="SAME_DAY",
        warranty="EXTENDED_24",
        bundle=None,
    )
    assert offer.final_product_price_cents == 9200
    assert offer.total_customer_price_cents == 12700
    assert offer.feasibility_status == FeasibilityStatus.FEASIBLE
    assert not any(
        item.code
        in {
            RejectionCode.BUYER_MAX_TOTAL_EXCEEDED,
            RejectionCode.BUYER_MAX_PRODUCT_PRICE_EXCEEDED,
        }
        for item in offer.rejection_reasons
    )


def test_case_e_higher_utility_over_budget_never_enters_pareto() -> None:
    intent = _budget_intent()
    variant, policy = _priced_variant(base=9200)
    cheap = _offer(
        variant_id=variant.id,
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=9200,
        delivery_code="STANDARD",
        delivery_days=2,
    )
    expensive = _offer(
        variant_id=variant.id,
        sku="EXP-127",
        product_name="High utility over budget",
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=12700,
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_customer_charge_cents=3500,
    )
    result = score_space(
        [cheap, expensive],
        intent=intent,
        policy=policy,
        variants={variant.id: variant},
        product_fits={variant.id: 0.95},
        profile_id="INTENT_ADAPTED",
    )
    over = next(
        item for item in result.scored if item.total_customer_price_cents == 12700
    )
    assert not over.all_mandatory_buyer_constraints_satisfied
    assert over.buyer_constraint_status.value == "VIOLATED"
    assert "BUYER_MAX_TOTAL_EXCEEDED" in over.buyer_constraint_codes
    assert not over.selectable
    assert not over.pareto_eligible
    assert not over.is_pareto_efficient
    assert not over.is_recommended
    assert result.recommended is not None
    assert result.recommended.all_mandatory_buyer_constraints_satisfied
    assert result.recommended.total_customer_price_cents <= 10000


def test_explanation_requires_complete_offer_validation() -> None:
    intent = _budget_intent()
    variant, policy = _priced_variant(base=9200)
    expensive = _offer(
        variant_id=variant.id,
        total_customer_price_cents=12700,
        final_product_price_cents=9200,
        base_price_cents=9200,
    )
    result = score_space(
        [expensive],
        intent=intent,
        policy=policy,
        variants={variant.id: variant},
        product_fits={variant.id: 0.95},
        profile_id="INTENT_ADAPTED",
    )
    scored = result.scored[0]
    reasons = explain_recommendation(
        scored,
        intent=intent,
        margin_floor=0.05,
        counterfactuals=[],
        frontier=False,
    )
    assert not any("mandatory requirements" in item.lower() for item in reasons)


def test_negotiation_preserves_total_until_explicit_relax() -> None:
    original = _budget_intent()
    tightened = apply_working_intent(
        original,
        [NegotiationDelta(price_constraint_change=8000, reconstruct_required=True)],
    )
    price = next(
        item for item in tightened.hard_constraints if item.field == ConstraintField.PRICE
    )
    assert price.normalized_value == 10000
    relaxed = apply_working_intent(
        original,
        [NegotiationDelta(price_constraint_change=15000, reconstruct_required=True)],
    )
    price = next(
        item for item in relaxed.hard_constraints if item.field == ConstraintField.PRICE
    )
    assert price.normalized_value == 15000
    assert price.applies_to == PriceBasis.CUSTOMER_TOTAL


def test_transaction_revalidation_rejects_over_total() -> None:
    offer = _offer(
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=12700,
        delivery_code="SAME_DAY",
        delivery_name="Same day",
        delivery_days=0,
        delivery_customer_charge_cents=3500,
    )
    session, proposal = _pair()
    intent = _budget_intent()
    session.working_intent = intent.model_dump(mode="json")
    session.original_intent = intent.model_dump(mode="json")
    variant = _variant()
    variant.base_price_cents = 9200
    variant.cogs_cents = 4000
    result = _run(
        session=session,
        proposal=proposal,
        variant=variant,
        policy=_policy(margin="0.0500"),
        offer=offer,
    )
    assert not result.valid
    assert TransactionFailureCode.BUYER_MAX_TOTAL_EXCEEDED in result.failure_codes
    assert any(item.check == "BUYER_PRICE" for item in result.checks)

"""Buyer hard constraints are gates before Pareto and selection."""

from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.intent.models import ConstraintField, ConstraintOperator, PriceBasis
from app.decision.negotiation.delta import apply_working_intent
from app.decision.negotiation.models import NegotiationDelta
from app.decision.optimisation.candidates import ensure_selected_offer_compliant
from app.decision.optimisation.engine import score_space
from tests.qualification_fixtures import constraint
from tests.test_buyer_total_price import _budget_intent, _offer, _priced_variant


def _run(offers, intent, variant, policy, fits=None):
    return score_space(
        offers,
        intent=intent,
        policy=policy,
        variants={variant.id: variant},
        product_fits=fits or {variant.id: 0.8},
        profile_id="INTENT_ADAPTED",
    )


def test_a_under_budget_is_buyer_safe_and_may_enter_pareto() -> None:
    intent = _budget_intent(10000)
    variant, policy = _priced_variant(base=9200)
    cheap = _offer(
        variant_id=variant.id,
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=9200,
    )
    result = _run([cheap], intent, variant, policy)
    scored = result.scored[0]
    assert scored.all_mandatory_buyer_constraints_satisfied
    assert scored.buyer_constraint_status.value == "SATISFIED"
    assert scored.selectable
    assert scored.pareto_eligible
    assert scored.is_pareto_efficient
    assert result.recommended is not None
    assert result.recommended.offer_id == scored.offer_id


def test_b_over_budget_is_not_pareto_or_selectable() -> None:
    intent = _budget_intent(10000)
    variant, policy = _priced_variant(base=9200)
    expensive = _offer(
        variant_id=variant.id,
        sku="ORION-MINI-106",
        product_name="Orion Mini 106",
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=12767,
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_customer_charge_cents=3567,
    )
    result = _run([expensive], intent, variant, policy)
    scored = result.scored[0]
    assert scored.total_customer_price_cents == 12767
    assert scored.buyer_constraint_status.value == "VIOLATED"
    assert "BUYER_MAX_TOTAL_EXCEEDED" in scored.buyer_constraint_codes
    assert not scored.all_mandatory_buyer_constraints_satisfied
    assert not scored.selectable
    assert not scored.pareto_eligible
    assert not scored.proposal_eligible
    assert not scored.is_pareto_efficient
    assert not scored.is_recommended
    assert result.recommended is None
    assert result.failure is not None
    assert result.failure.code == "NO_COMPLIANT_OFFER"


def test_c_all_offers_over_budget_returns_no_compliant_offer() -> None:
    intent = _budget_intent(10000)
    variant, policy = _priced_variant(base=9200)
    offers = [
        _offer(
            variant_id=variant.id,
            sku=f"OVER-{total}",
            total_customer_price_cents=total,
            final_product_price_cents=9200,
            base_price_cents=9200,
        )
        for total in (10420, 12767, 15000)
    ]
    result = _run(offers, intent, variant, policy)
    assert result.recommended is None
    assert result.failure is not None
    assert result.failure.code == "NO_COMPLIANT_OFFER"
    assert result.failure.blocked_by == "BUYER_CONSTRAINT"
    assert result.near_miss is not None
    assert result.near_miss.label == "NEAR_MISS"
    assert result.near_miss.relaxation == "REQUIRES_BUYER_RELAXATION"
    assert result.near_miss.total_customer_price_cents == 10420
    assert result.near_miss.gap_cents == 420
    assert not result.near_miss.selectable
    assert not result.near_miss.is_recommended
    assert not result.near_miss.is_pareto_efficient


def test_d_high_buyer_utility_does_not_override_budget() -> None:
    intent = _budget_intent(10000)
    variant, policy = _priced_variant(base=8000)
    cheap = _offer(
        variant_id=variant.id,
        sku="OK-92",
        base_price_cents=8000,
        final_product_price_cents=8000,
        total_customer_price_cents=9200,
        delivery_code="STANDARD",
        delivery_days=2,
    )
    expensive = _offer(
        variant_id=variant.id,
        sku="HIGH-U",
        product_name="Extremely high utility",
        base_price_cents=8000,
        final_product_price_cents=8000,
        total_customer_price_cents=12700,
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_customer_charge_cents=4700,
    )
    result = _run(
        [cheap, expensive],
        intent,
        variant,
        policy,
        fits={variant.id: 0.99},
    )
    over = next(item for item in result.scored if item.sku == "HIGH-U")
    assert over.utility.score >= 0
    assert not over.selectable
    assert not over.is_pareto_efficient
    assert result.recommended is not None
    assert result.recommended.sku == "OK-92"
    assert result.recommended.total_customer_price_cents <= 10000


def test_e_high_merchant_contribution_does_not_override_budget() -> None:
    intent = _budget_intent(10000)
    variant, policy = _priced_variant(base=4000)
    variant.cogs_cents = 500
    cheap = _offer(
        variant_id=variant.id,
        sku="OK-90",
        base_price_cents=4000,
        final_product_price_cents=4000,
        total_customer_price_cents=9000,
    )
    fat = _offer(
        variant_id=variant.id,
        sku="FAT-MARGIN",
        product_name="High contribution over budget",
        base_price_cents=4000,
        final_product_price_cents=4000,
        total_customer_price_cents=12700,
    )
    result = _run([cheap, fat], intent, variant, policy)
    over = next(item for item in result.scored if item.sku == "FAT-MARGIN")
    assert over.economics.contribution_margin_cents > 0
    assert not over.selectable
    assert result.recommended is not None
    assert result.recommended.sku == "OK-90"


def test_f_explicit_budget_relax_can_make_offer_selectable() -> None:
    original = _budget_intent(10000)
    variant, policy = _priced_variant(base=9200)
    near = _offer(
        variant_id=variant.id,
        sku="NEAR-104",
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=10420,
    )
    blocked = _run([near], original, variant, policy)
    assert blocked.recommended is None
    assert blocked.failure is not None
    assert blocked.failure.code == "NO_COMPLIANT_OFFER"

    relaxed = apply_working_intent(
        original,
        [NegotiationDelta(price_constraint_change=10500, reconstruct_required=True)],
    )
    price = next(
        item
        for item in relaxed.hard_constraints
        if item.field == ConstraintField.PRICE
    )
    assert price.normalized_value == 10500
    assert price.applies_to == PriceBasis.CUSTOMER_TOTAL

    allowed = _run([near], relaxed, variant, policy)
    assert allowed.recommended is not None
    assert allowed.recommended.sku == "NEAR-104"
    assert allowed.recommended.all_mandatory_buyer_constraints_satisfied
    assert allowed.recommended.selectable
    ensure_selected_offer_compliant(allowed.recommended)


def test_g_unknown_mandatory_evidence_is_not_selectable() -> None:
    intent = _budget_intent(20000).model_copy(
        update={
            "hard_constraints": [
                constraint(
                    ConstraintField.PRICE,
                    ConstraintOperator.LTE,
                    20000,
                    unit="AUD_CENTS",
                    phrase="under A$200",
                ).model_copy(update={"applies_to": PriceBasis.CUSTOMER_TOTAL}),
                constraint(
                    ConstraintField.ANC,
                    ConstraintOperator.EQ,
                    True,
                    cid="anc",
                    phrase="must have ANC",
                ),
            ]
        }
    )
    variant, policy = _priced_variant(base=9200)
    variant.attributes = {}
    variant.evidence = []
    snapshot = variant_to_snapshot(variant)
    assert "anc" not in snapshot.attributes
    offer = _offer(
        variant_id=variant.id,
        base_price_cents=9200,
        final_product_price_cents=9200,
        total_customer_price_cents=9200,
    )
    result = _run([offer], intent, variant, policy)
    scored = result.scored[0]
    assert scored.buyer_constraint_status.value == "UNKNOWN"
    assert not scored.all_mandatory_buyer_constraints_satisfied
    assert not scored.selectable
    assert not scored.pareto_eligible
    assert result.recommended is None
    assert result.failure is not None
    assert result.failure.code == "NO_COMPLIANT_OFFER"
    ensure_selected_offer_compliant(result.recommended)


def test_selection_invariant_rejects_buyer_unsafe_offer() -> None:
    variant, policy = _priced_variant(base=9200)
    result = _run(
        [
            _offer(
                variant_id=variant.id,
                total_customer_price_cents=12767,
                final_product_price_cents=9200,
            )
        ],
        _budget_intent(10000),
        variant,
        policy,
    )
    unsafe = result.scored[0]
    assert not unsafe.all_mandatory_buyer_constraints_satisfied
    try:
        ensure_selected_offer_compliant(unsafe)
    except RuntimeError as exc:
        assert "mandatory buyer constraints" in str(exc)
    else:
        raise AssertionError("expected invariant to reject the unsafe offer")

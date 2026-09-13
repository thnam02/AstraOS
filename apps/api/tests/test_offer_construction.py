"""Cartesian offer construction and static feasibility."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.decision.intent.models import ContextLabel, IntentContext
from app.decision.offers.bundles import relevant_bundle_codes
from app.decision.offers.constructor import construct_variant, estimate_count
from app.decision.offers.feasibility import sellable_units
from app.decision.offers.models import (
    ConstructionLimits,
    FeasibilityStatus,
    OfferCandidate,
    RejectionCode,
)
from tests.offer_fixtures import construction_intent, travel_intent, wired_variant
from tests.qualification_fixtures import intent_with


def _has(item: OfferCandidate, code: RejectionCode) -> bool:
    return any(reason.code == code for reason in item.rejection_reasons)


def _build(**kwargs):
    variant, policy = wired_variant(**kwargs)
    limits = ConstructionLimits()
    expires = datetime.now(UTC) + timedelta(minutes=5)
    intent = construction_intent()
    offers, dims = construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=relevant_bundle_codes(intent),
        limits=limits,
        expires_at=expires,
    )
    return offers, dims, variant


def test_cartesian_count_is_dynamic() -> None:
    offers, dims, _variant = _build()
    assert dims["estimated"] == estimate_count(
        dims["prices"],
        dims["deliveries"],
        dims["warranties"],
        dims["bundles"],
        dims["returns"],
    )
    assert len(offers) == dims["estimated"]
    assert len(offers) > 20


def test_total_price_composition() -> None:
    offers, _dims, variant = _build()
    feasible = [
        item for item in offers if item.feasibility_status == FeasibilityStatus.FEASIBLE
    ]
    assert feasible
    sample = next(
        item
        for item in feasible
        if item.bundle_code == "TRAVEL_ADAPTER" and item.delivery_code == "SAME_DAY"
    )
    assert sample.total_customer_price_cents == (
        sample.final_product_price_cents
        + sample.delivery_customer_charge_cents
        + sample.warranty_customer_price_cents
        + sample.bundle_customer_price_cents
    )
    assert sample.direct_intervention_cost_cents == (
        sample.price_adjustment_cents
        + sample.delivery_merchant_cost_cents
        + sample.warranty_merchant_cost_cents
        + sample.bundle_merchant_cost_cents
        + int(sample.return_policy_expected_cost_cents or 0)
    )
    assert sample.currency == "AUD"
    assert sample.base_price_cents == variant.base_price_cents


def test_same_day_unavailable_is_rejected_not_invented() -> None:
    offers, _dims, _variant = _build(same_day=False)
    same_day = [item for item in offers if item.delivery_code == "SAME_DAY"]
    assert same_day
    assert all(
        item.feasibility_status == FeasibilityStatus.REJECTED for item in same_day
    )
    assert all(_has(item, RejectionCode.DELIVERY_NOT_AVAILABLE) for item in same_day)


def test_standard_delivery_rejected_when_today_required() -> None:
    offers, _dims, _variant = _build()
    standard = [item for item in offers if item.delivery_code == "STANDARD"]
    assert standard
    assert all(_has(item, RejectionCode.DELIVERY_NOT_AVAILABLE) for item in standard)


def test_zero_stock_rejects() -> None:
    offers, _dims, variant = _build(stock=0)
    assert sellable_units(variant) == 0
    assert all(item.feasibility_status == FeasibilityStatus.REJECTED for item in offers)
    assert all(_has(item, RejectionCode.OUT_OF_STOCK) for item in offers)


def test_missing_inventory_is_unknown() -> None:
    variant, policy = wired_variant()
    variant.inventory = None
    intent = travel_intent()
    offers, _dims = construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=relevant_bundle_codes(intent),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC),
    )
    assert all(
        any(
            reason.code == RejectionCode.MISSING_OPERATIONAL_DATA
            for reason in item.rejection_reasons
        )
        for item in offers
    )


def test_discount_authority() -> None:
    offers, dims, _variant = _build(policy_discount=Decimal("0.05"))
    assert dims["prices"] == 3
    assert all(item.price_adjustment_rate <= Decimal("0.05") for item in offers)


def test_warranty_upgrade_disabled() -> None:
    offers, _dims, _variant = _build(warranty_upgrade_enabled=False)
    extended = [item for item in offers if item.warranty_code == "EXTENDED_24"]
    assert extended
    assert all(_has(item, RejectionCode.WARRANTY_NOT_AVAILABLE) for item in extended)


def test_bundles_disabled() -> None:
    offers, _dims, _variant = _build(bundle_enabled=False)
    bundled = [item for item in offers if item.bundle_code]
    assert bundled
    assert all(_has(item, RejectionCode.BUNDLE_INCOMPATIBLE) for item in bundled)


def test_none_bundle_always_present() -> None:
    offers, _dims, _variant = _build()
    assert any(item.bundle_code is None for item in offers)


def test_travel_bundle_relevant_for_long_haul() -> None:
    offers, _dims, _variant = _build()
    travel = [
        item
        for item in offers
        if item.bundle_code == "TRAVEL_ADAPTER"
        and item.feasibility_status == FeasibilityStatus.FEASIBLE
    ]
    assert travel
    assert travel[0].bundle_relevance is not None
    assert "long_haul_travel" in travel[0].bundle_relevance.triggered_by


def test_gaming_does_not_select_travel_adapter() -> None:
    variant, policy = wired_variant()
    intent = intent_with(
        context_items=[
            IntentContext(label=ContextLabel.GAMING, source_phrase="gaming")
        ]
    )
    offers, _dims = construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=relevant_bundle_codes(intent),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC),
    )
    travel = [item for item in offers if item.bundle_code == "TRAVEL_ADAPTER"]
    assert travel
    assert all(_has(item, RejectionCode.BUNDLE_INCOMPATIBLE) for item in travel)


def test_flex_returns_obey_policy() -> None:
    offers, _dims, _variant = _build(flexible_returns_enabled=False)
    flex = [item for item in offers if item.return_policy_code == "FLEX_60"]
    assert flex
    assert all(_has(item, RejectionCode.RETURN_POLICY_DISABLED) for item in flex)


def test_proof_attached() -> None:
    offers, _dims, _variant = _build()
    feasible = next(
        item for item in offers if item.feasibility_status == FeasibilityStatus.FEASIBLE
    )
    kinds = {item.type for item in feasible.proof}
    required = {
        "product",
        "price",
        "delivery",
        "warranty",
        "bundle",
        "returns",
        "inventory",
    }
    assert required <= kinds


def test_one_product_many_offers() -> None:
    offers, _dims, _variant = _build()
    feasible = [
        item for item in offers if item.feasibility_status == FeasibilityStatus.FEASIBLE
    ]
    assert {item.price_adjustment_type for item in feasible} >= {"BASE", "DISCOUNT"}
    assert {item.warranty_code for item in feasible} >= {"STANDARD_12", "EXTENDED_24"}
    assert None in {item.bundle_code for item in feasible}
    assert "TRAVEL_ADAPTER" in {item.bundle_code for item in feasible}
    assert {item.delivery_code for item in feasible} == {"SAME_DAY"}

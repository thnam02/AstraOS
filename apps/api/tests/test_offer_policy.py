"""Merchant policy guardrails exclude unsafe offers from the frontier."""

from decimal import Decimal

from app.decision.economics.calculator import compute_economics
from app.decision.policies.offer_policy_evaluator import evaluate_offer_policy
from app.decision.policies.rejection_codes import PolicyRejectionCode
from tests.offer_fixtures import travel_intent, wired_variant
from tests.test_economics import _offer


def test_margin_floor() -> None:
    offer = _offer(
        final_product_price_cents=22000,
        total_customer_price_cents=22000,
        price_adjustment_type="DISCOUNT",
        price_adjustment_rate=Decimal("0.10"),
    )
    _variant, policy = wired_variant()
    policy.minimum_margin_rate = Decimal("0.2500")
    eco = compute_economics(offer, cogs_cents=20000)
    result = evaluate_offer_policy(
        offer,
        economics=eco,
        policy=policy,
        intent=travel_intent(),
        sellable_units=4,
    )
    assert not result.policy_safe
    assert PolicyRejectionCode.MARGIN_BELOW_FLOOR.value in result.rejection_codes


def test_discount_limit() -> None:
    offer = _offer(
        price_adjustment_rate=Decimal("0.20"),
        price_adjustment_type="DISCOUNT",
        final_product_price_cents=26320,
        total_customer_price_cents=26320,
    )
    _variant, policy = wired_variant(policy_discount=Decimal("0.10"))
    eco = compute_economics(offer, cogs_cents=18000)
    result = evaluate_offer_policy(
        offer,
        economics=eco,
        policy=policy,
        intent=travel_intent(),
        sellable_units=4,
    )
    assert PolicyRejectionCode.DISCOUNT_EXCEEDS_LIMIT.value in result.rejection_codes


def test_out_of_stock() -> None:
    offer = _offer()
    _variant, policy = wired_variant()
    eco = compute_economics(offer, cogs_cents=18000)
    result = evaluate_offer_policy(
        offer,
        economics=eco,
        policy=policy,
        intent=travel_intent(),
        sellable_units=0,
    )
    assert PolicyRejectionCode.OUT_OF_STOCK.value in result.rejection_codes


def test_disabled_dimensions() -> None:
    offer = _offer(
        warranty_code="EXTENDED_24",
        bundle_code="TRAVEL_ADAPTER",
        return_policy_code="FLEX_60",
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_merchant_cost_cents=2000,
        delivery_customer_charge_cents=0,
        total_customer_price_cents=32900,
    )
    _variant, policy = wired_variant(
        warranty_upgrade_enabled=False,
        bundle_enabled=False,
        flexible_returns_enabled=False,
    )
    policy.delivery_subsidy_enabled = False
    eco = compute_economics(offer, cogs_cents=18000)
    result = evaluate_offer_policy(
        offer,
        economics=eco,
        policy=policy,
        intent=travel_intent(),
        sellable_units=3,
    )
    codes = set(result.rejection_codes)
    assert PolicyRejectionCode.WARRANTY_DISABLED.value in codes
    assert PolicyRejectionCode.BUNDLE_DISABLED.value in codes
    assert PolicyRejectionCode.RETURNS_DISABLED.value in codes
    assert PolicyRejectionCode.DELIVERY_DISABLED.value in codes


def test_safe_same_day_clears() -> None:
    offer = _offer(
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_merchant_cost_cents=800,
        delivery_customer_charge_cents=1000,
        total_customer_price_cents=33900,
    )
    _variant, policy = wired_variant()
    eco = compute_economics(offer, cogs_cents=18000)
    result = evaluate_offer_policy(
        offer,
        economics=eco,
        policy=policy,
        intent=travel_intent(),
        sellable_units=5,
    )
    assert result.policy_safe
    assert result.rejection_codes == []


def test_subsidy_cap() -> None:
    offer = _offer(
        delivery_code="SAME_DAY",
        delivery_days=0,
        delivery_merchant_cost_cents=2000,
        delivery_customer_charge_cents=0,
        total_customer_price_cents=32900,
    )
    _variant, policy = wired_variant()
    policy.maximum_delivery_subsidy_cents = 1000
    eco = compute_economics(offer, cogs_cents=18000)
    result = evaluate_offer_policy(
        offer,
        economics=eco,
        policy=policy,
        intent=travel_intent(),
        sellable_units=2,
    )
    assert (
        PolicyRejectionCode.DELIVERY_SUBSIDY_EXCEEDS_LIMIT.value
        in result.rejection_codes
    )

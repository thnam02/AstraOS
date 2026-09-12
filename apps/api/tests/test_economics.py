"""Contribution accounting uses integer cents and does not double-count discounts."""

from decimal import Decimal
from uuid import uuid4

from app.decision.economics.calculator import compute_economics
from app.decision.offers.models import (
    ConstructionStatus,
    FeasibilityStatus,
    OfferCandidate,
)


def _offer(**overrides: object) -> OfferCandidate:
    values: dict[str, object] = {
        "id": uuid4(),
        "product_id": uuid4(),
        "variant_id": uuid4(),
        "sku": "AUR-T01",
        "product_name": "Aurora Travel Pro",
        "brand": "Aurora",
        "base_price_cents": 32900,
        "price_adjustment_cents": 0,
        "final_product_price_cents": 32900,
        "price_adjustment_type": "BASE",
        "price_adjustment_rate": Decimal("0"),
        "delivery_code": "STANDARD",
        "delivery_name": "Standard",
        "delivery_days": 2,
        "delivery_customer_charge_cents": 0,
        "delivery_merchant_cost_cents": 0,
        "warranty_code": "STANDARD_12",
        "warranty_name": "12 months",
        "warranty_months": 12,
        "warranty_customer_price_cents": 0,
        "warranty_merchant_cost_cents": 0,
        "total_customer_price_cents": 32900,
        "direct_intervention_cost_cents": 0,
        "construction_status": ConstructionStatus.GENERATED,
        "feasibility_status": FeasibilityStatus.FEASIBLE,
        "return_policy_code": "STANDARD_30",
        "return_policy_expected_cost_cents": 400,
    }
    values.update(overrides)
    return OfferCandidate(**values)  # type: ignore[arg-type]


def test_contribution_base_offer() -> None:
    offer = _offer()
    eco = compute_economics(offer, cogs_cents=20000)
    assert eco.total_customer_revenue_cents == 32900
    assert eco.contribution_margin_cents == 32900 - 20000 - 400
    from app.decision.economics.normalization import ratio

    assert eco.contribution_margin_rate == ratio(12500, 32900)
    assert isinstance(eco.contribution_margin_cents, int)


def test_discount_reduces_revenue_once() -> None:
    offer = _offer(
        price_adjustment_cents=3290,
        final_product_price_cents=29610,
        price_adjustment_type="DISCOUNT",
        price_adjustment_rate=Decimal("0.10"),
        total_customer_price_cents=29610,
    )
    eco = compute_economics(offer, cogs_cents=20000, baseline_product_price_cents=32900)
    assert eco.product_selling_price_cents == 29610
    assert eco.revenue_forgone_vs_list_cents == 3290
    assert eco.contribution_margin_cents == 29610 - 20000 - 400
    # Discount is not also a merchant cost line.
    assert eco.merchant_delivery_cost_cents == 0


def test_same_day_costs_and_charges() -> None:
    offer = _offer(
        delivery_code="SAME_DAY",
        delivery_name="Same Day",
        delivery_days=0,
        delivery_customer_charge_cents=1000,
        delivery_merchant_cost_cents=800,
        total_customer_price_cents=33900,
    )
    eco = compute_economics(
        offer,
        cogs_cents=20000,
        baseline_delivery_cost_cents=0,
        baseline_return_cost_cents=400,
    )
    assert eco.contribution_margin_cents == 33900 - 20000 - 800 - 400
    assert eco.incremental_intervention_cost_cents == 800
    assert eco.delivery_subsidy_cents == 0


def test_warranty_and_bundle_economics() -> None:
    offer = _offer(
        warranty_code="EXTENDED_24",
        warranty_months=24,
        warranty_customer_price_cents=1900,
        warranty_merchant_cost_cents=900,
        bundle_code="TRAVEL_ADAPTER",
        bundle_name="Travel adapter",
        bundle_customer_price_cents=1500,
        bundle_merchant_cost_cents=700,
        total_customer_price_cents=32900 + 1900 + 1500,
    )
    eco = compute_economics(
        offer,
        cogs_cents=20000,
        baseline_warranty_cost_cents=0,
        baseline_bundle_cost_cents=0,
        baseline_return_cost_cents=400,
    )
    assert eco.contribution_margin_cents == (
        36300 - 20000 - 900 - 700 - 400
    )
    assert eco.incremental_intervention_cost_cents == 900 + 700


def test_returns_cost() -> None:
    offer = _offer(return_policy_expected_cost_cents=900)
    eco = compute_economics(
        offer, cogs_cents=20000, baseline_return_cost_cents=400
    )
    assert eco.expected_return_cost_cents == 900
    assert eco.incremental_intervention_cost_cents == 500
    assert eco.contribution_margin_cents == 32900 - 20000 - 900


def test_money_is_integer() -> None:
    eco = compute_economics(_offer(), cogs_cents=19999)
    assert isinstance(eco.contribution_margin_cents, int)
    assert isinstance(eco.total_customer_revenue_cents, int)

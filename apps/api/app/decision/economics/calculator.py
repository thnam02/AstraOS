"""Contribution-margin calculator. Discounts reduce revenue only once."""

from app.decision.economics.models import OfferEconomics
from app.decision.economics.normalization import ratio, subsidy_cents
from app.decision.offers.models import OfferCandidate


def compute_economics(
    offer: OfferCandidate,
    *,
    cogs_cents: int,
    baseline_product_price_cents: int | None = None,
    baseline_delivery_cost_cents: int = 0,
    baseline_warranty_cost_cents: int = 0,
    baseline_bundle_cost_cents: int = 0,
    baseline_return_cost_cents: int = 0,
) -> OfferEconomics:
    """Return contribution for one offer.

    contribution_margin_cents =
        total_customer_revenue
        - COGS
        - merchant delivery cost
        - merchant warranty cost
        - merchant bundle cost
        - expected return-policy cost

    The list-price discount is already in a lower product selling price.
    """
    revenue = int(offer.total_customer_price_cents)
    delivery_cost = int(offer.delivery_merchant_cost_cents)
    warranty_cost = int(offer.warranty_merchant_cost_cents)
    bundle_cost = int(offer.bundle_merchant_cost_cents)
    return_cost = int(offer.return_policy_expected_cost_cents or 0)
    cogs = int(cogs_cents)
    contribution = (
        revenue - cogs - delivery_cost - warranty_cost - bundle_cost - return_cost
    )
    list_price = (
        int(baseline_product_price_cents)
        if baseline_product_price_cents is not None
        else int(offer.base_price_cents)
    )
    forgone = max(0, list_price - int(offer.final_product_price_cents))
    intervention = (
        forgone
        + max(0, delivery_cost - int(baseline_delivery_cost_cents))
        + max(0, warranty_cost - int(baseline_warranty_cost_cents))
        + max(0, bundle_cost - int(baseline_bundle_cost_cents))
        + max(0, return_cost - int(baseline_return_cost_cents))
    )
    return OfferEconomics(
        product_selling_price_cents=int(offer.final_product_price_cents),
        delivery_charge_cents=int(offer.delivery_customer_charge_cents),
        warranty_price_cents=int(offer.warranty_customer_price_cents),
        bundle_price_cents=int(offer.bundle_customer_price_cents),
        total_customer_revenue_cents=revenue,
        cogs_cents=cogs,
        merchant_delivery_cost_cents=delivery_cost,
        merchant_warranty_cost_cents=warranty_cost,
        merchant_bundle_cost_cents=bundle_cost,
        expected_return_cost_cents=return_cost,
        contribution_margin_cents=contribution,
        contribution_margin_rate=ratio(contribution, revenue),
        revenue_forgone_vs_list_cents=forgone,
        incremental_intervention_cost_cents=intervention,
        delivery_subsidy_cents=subsidy_cents(
            delivery_cost, int(offer.delivery_customer_charge_cents)
        ),
        warranty_subsidy_cents=subsidy_cents(
            warranty_cost, int(offer.warranty_customer_price_cents)
        ),
        bundle_subsidy_cents=subsidy_cents(
            bundle_cost, int(offer.bundle_customer_price_cents)
        ),
    )

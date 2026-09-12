"""Merchant economics result models. Money is integer cents."""

from decimal import Decimal

from pydantic import BaseModel, Field


class OfferEconomics(BaseModel):
    """Contribution accounting for one commercial configuration.

    Convention: contribution is revenue minus product COGS and merchant-funded
    fulfilment / warranty / bundle / expected-return costs. A discount lowers
    product revenue; it is not subtracted again as a cost.
    """

    product_selling_price_cents: int
    delivery_charge_cents: int
    warranty_price_cents: int
    bundle_price_cents: int
    total_customer_revenue_cents: int

    cogs_cents: int
    merchant_delivery_cost_cents: int
    merchant_warranty_cost_cents: int
    merchant_bundle_cost_cents: int
    expected_return_cost_cents: int

    contribution_margin_cents: int
    contribution_margin_rate: Decimal

    revenue_forgone_vs_list_cents: int = 0
    incremental_intervention_cost_cents: int = 0
    delivery_subsidy_cents: int = 0
    warranty_subsidy_cents: int = 0
    bundle_subsidy_cents: int = 0


class BaselineEconomics(BaseModel):
    """Baseline configuration economics for one variant."""

    variant_id: str
    total_customer_revenue_cents: int
    contribution_margin_cents: int
    merchant_delivery_cost_cents: int
    merchant_warranty_cost_cents: int
    merchant_bundle_cost_cents: int
    expected_return_cost_cents: int
    product_selling_price_cents: int


class UtilityWeights(BaseModel):
    """Kept here only for shared decimal helpers; see utility.models."""

    product: float = Field(ge=0, le=1)
    price: float = Field(ge=0, le=1)
    delivery: float = Field(ge=0, le=1)
    warranty: float = Field(ge=0, le=1)
    bundle: float = Field(ge=0, le=1)
    returns: float = Field(ge=0, le=1)

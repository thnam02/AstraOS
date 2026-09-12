"""HTTP schemas for merchant-economics optimisation. Utility is not P(win)."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.optimisation.models import (
    CounterfactualRow,
    NamedComparison,
    OptimisationFailure,
    ScoredOffer,
    SelectionScore,
)
from app.decision.pareto.models import ObjectiveSpec
from app.decision.utility.models import UTILITY_DISCLAIMER

BuyerProfile = Literal[
    "INTENT_ADAPTED",
    "BALANCED",
    "URGENT_TRAVELLER",
    "BUDGET_SHOPPER",
    "ASSURANCE_BUYER",
    "QUALITY_FIRST",
]


class OptimiseRequest(BaseModel):
    offer_run_id: UUID
    buyer_profile: BuyerProfile = "INTENT_ADAPTED"
    alpha: float = Field(default=0.5, ge=0, le=1)


class DecisionRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    parser_mode: Literal["rule_based", "llm"] | None = None
    buyer_profile: BuyerProfile = "INTENT_ADAPTED"
    max_products: int = Field(default=8, ge=1, le=20)
    alpha: float = Field(default=0.5, ge=0, le=1)


class OptimisationSummary(BaseModel):
    offers_considered: int
    policy_safe: int
    policy_rejected: int
    pareto_efficient: int


class BuyerModelBlock(BaseModel):
    type: str = "SIMULATED_UTILITY"
    profile_id: str
    weights: dict[str, float]
    disclaimer: str = UTILITY_DISCLAIMER


class OptimisationTiming(BaseModel):
    economics_ms: float
    policy_filter_ms: float
    utility_ms: float
    pareto_ms: float
    selection_ms: float
    counterfactual_ms: float
    persistence_ms: float
    total_optimisation_ms: float


class PlotPoint(BaseModel):
    offer_id: UUID
    product_name: str
    sku: str
    total_price_cents: int
    delivery_code: str
    warranty_code: str
    bundle_code: str | None
    return_policy_code: str | None
    buyer_utility: float
    contribution_margin_cents: int
    intervention_cost_cents: int
    is_pareto_efficient: bool
    is_recommended: bool


class PublicScoredOffer(BaseModel):
    offer_id: UUID
    product_name: str
    brand: str
    sku: str
    variant_id: UUID
    pricing: dict[str, Any]
    delivery: dict[str, Any]
    warranty: dict[str, Any]
    bundle: dict[str, Any] | None
    returns: dict[str, Any] | None
    contribution_margin_cents: int
    contribution_margin_rate: float
    incremental_intervention_cost_cents: int
    buyer_utility: float
    utility_trace: dict[str, Any]
    policy_safe: bool
    policy_rejection_codes: list[str]
    is_pareto_efficient: bool
    dominated_by_offer_id: UUID | None
    is_recommended: bool
    is_baseline: bool
    product_fit: float
    learned_synthetic_score: float | None = None
    learned_score_label: str | None = None


class OptimisationResponse(BaseModel):
    optimisation_run_id: UUID
    offer_run_id: UUID
    match_run_id: UUID | None
    summary: OptimisationSummary
    buyer_model: BuyerModelBlock
    timing: OptimisationTiming
    recommended_offer: PublicScoredOffer | None
    selection: SelectionScore | None
    pareto_offers: list[PublicScoredOffer]
    alternative_pareto_offers: list[PublicScoredOffer]
    plot_points: list[PlotPoint]
    counterfactuals: list[CounterfactualRow]
    comparisons: list[NamedComparison]
    explanation: list[str]
    failure: OptimisationFailure | None
    objectives: list[ObjectiveSpec]
    created_at: datetime | None = None


def to_public_scored(item: ScoredOffer) -> PublicScoredOffer:
    return PublicScoredOffer(
        offer_id=item.offer_id,
        product_name=item.product_name,
        brand=item.brand,
        sku=item.sku,
        variant_id=item.variant_id,
        pricing={
            "product_price_cents": item.product_price_cents,
            "total_price_cents": item.total_customer_price_cents,
            "currency": item.currency,
        },
        delivery={
            "code": item.delivery_code,
            "name": item.delivery_name,
            "days": item.delivery_days,
        },
        warranty={
            "code": item.warranty_code,
            "name": item.warranty_name,
            "months": item.warranty_months,
        },
        bundle=(
            None
            if not item.bundle_code
            else {"code": item.bundle_code, "name": item.bundle_name}
        ),
        returns=(
            None
            if not item.return_policy_code
            else {
                "code": item.return_policy_code,
                "window_days": item.return_window_days,
            }
        ),
        contribution_margin_cents=item.economics.contribution_margin_cents,
        contribution_margin_rate=float(item.economics.contribution_margin_rate),
        incremental_intervention_cost_cents=(
            item.economics.incremental_intervention_cost_cents
        ),
        buyer_utility=item.utility.score,
        utility_trace=item.utility.trace.model_dump(),
        policy_safe=item.policy.policy_safe,
        policy_rejection_codes=item.policy.rejection_codes,
        is_pareto_efficient=item.is_pareto_efficient,
        dominated_by_offer_id=item.dominated_by_offer_id,
        is_recommended=item.is_recommended,
        is_baseline=item.is_baseline,
        product_fit=item.product_fit,
    )


def to_plot_point(item: ScoredOffer) -> PlotPoint:
    return PlotPoint(
        offer_id=item.offer_id,
        product_name=item.product_name,
        sku=item.sku,
        total_price_cents=item.total_customer_price_cents,
        delivery_code=item.delivery_code,
        warranty_code=item.warranty_code,
        bundle_code=item.bundle_code,
        return_policy_code=item.return_policy_code,
        buyer_utility=item.utility.score,
        contribution_margin_cents=item.economics.contribution_margin_cents,
        intervention_cost_cents=item.economics.incremental_intervention_cost_cents,
        is_pareto_efficient=item.is_pareto_efficient,
        is_recommended=item.is_recommended,
    )

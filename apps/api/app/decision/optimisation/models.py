"""In-memory optimisation artefacts. Not a negotiation or transaction."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.economics.models import OfferEconomics
from app.decision.offers.buyer_constraints import (
    BuyerConstraintReason,
    BuyerConstraintStatus,
)
from app.decision.policies.offer_policy_evaluator import OfferPolicyEvaluation
from app.decision.utility.models import SimulatedBuyerUtility

ALGORITHM_VERSION = "pareto.v1"
SELECTION_RULE = "normalized_weighted_sum"
DEFAULT_ALPHA = 0.5


class ScoredOffer(BaseModel):
    offer_id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    brand: str
    product_price_cents: int
    total_customer_price_cents: int
    currency: str = "AUD"
    delivery_code: str
    delivery_name: str
    delivery_days: int
    warranty_code: str
    warranty_name: str
    warranty_months: int
    bundle_code: str | None
    bundle_name: str | None
    return_policy_code: str | None
    return_window_days: int | None
    economics: OfferEconomics
    policy: OfferPolicyEvaluation
    utility: SimulatedBuyerUtility
    is_pareto_efficient: bool = False
    dominated_by_offer_id: UUID | None = None
    is_recommended: bool = False
    is_baseline: bool = False
    baseline_offer_id: UUID | None = None
    product_fit: float = 0.0
    feasible: bool = True
    buyer_constraint_status: BuyerConstraintStatus = BuyerConstraintStatus.SATISFIED
    buyer_constraint_reasons: list[BuyerConstraintReason] = Field(default_factory=list)
    buyer_constraint_codes: list[str] = Field(default_factory=list)
    all_mandatory_buyer_constraints_satisfied: bool = True
    selectable: bool = False
    pareto_eligible: bool = False
    proposal_eligible: bool = False


class SelectionScore(BaseModel):
    offer_id: UUID
    normalized_utility: float
    normalized_contribution: float
    score: float
    alpha: float
    rule: str = SELECTION_RULE
    mode: str | None = None
    buyer_weight: float | None = None
    merchant_weight: float | None = None
    version: str | None = None


class MerchantObjectiveSnapshot(BaseModel):
    mode: str
    buyer_weight: float
    merchant_weight: float
    version: str


class ObjectiveComparison(BaseModel):
    mode: str
    offer_id: UUID | None = None
    product_name: str | None = None
    sku: str | None = None
    buyer_utility: float | None = None
    contribution_margin_cents: int | None = None
    intervention_cost_cents: int | None = None
    score: float | None = None


class CounterfactualRow(BaseModel):
    lever: str
    label: str
    offer_id: UUID | None = None
    policy_safe: bool
    buyer_utility: float
    delta_utility: float
    contribution_margin_cents: int
    delta_contribution_cents: int
    incremental_intervention_cost_cents: int
    intervention_efficiency: float | None = None
    total_price_cents: int
    delivery_code: str
    warranty_code: str
    bundle_code: str | None
    return_policy_code: str | None


class NamedComparison(BaseModel):
    role: str
    offer_id: UUID | None = None
    label: str
    buyer_utility: float | None = None
    contribution_margin_cents: int | None = None
    policy_safe: bool = False


class NearMissCandidate(BaseModel):
    offer_id: UUID
    product_name: str
    sku: str
    total_customer_price_cents: int
    currency: str = "AUD"
    gap_cents: int | None = None
    requested_max_price_cents: int | None = None
    label: str = "NEAR_MISS"
    relaxation: str = "REQUIRES_BUYER_RELAXATION"
    blocked_codes: list[str] = Field(default_factory=list)
    reason: str
    is_pareto_efficient: bool = False
    is_recommended: bool = False
    selectable: bool = False


class OptimisationFailure(BaseModel):
    code: str
    message: str
    requested_max_price_cents: int | None = None
    lowest_constructed_price_cents: int | None = None
    lowest_policy_safe_price_cents: int | None = None
    blocked_by: str | None = None
    buyer_constraint_codes: list[str] = Field(default_factory=list)
    rejection_distribution: dict[str, int] = Field(default_factory=dict)


class EngineResult(BaseModel):
    scored: list[ScoredOffer]
    frontier: list[ScoredOffer]
    recommended: ScoredOffer | None
    selection: SelectionScore | None
    counterfactuals: list[CounterfactualRow]
    comparisons: list[NamedComparison]
    failure: OptimisationFailure | None
    explanation: list[str]
    timing: dict[str, float] = Field(default_factory=dict)
    merchant_objective: MerchantObjectiveSnapshot | None = None
    objective_comparisons: list[ObjectiveComparison] = Field(default_factory=list)
    near_miss: NearMissCandidate | None = None
    candidate_count: int = 0
    feasible_count: int = 0
    buyer_compliant_count: int = 0

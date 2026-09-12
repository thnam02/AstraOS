"""Arena DTOs. Scores are simulated, not conversion estimates."""

from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.arena import ARENA_DISCLAIMER
from app.decision.intent.models import ShoppingIntent
from app.decision.offers.models import OfferCandidate
from app.decision.optimisation.models import ScoredOffer
from app.decision.retrieval.models import RankedProductMatch
from app.decision.utility.models import UtilityTrace, UtilityWeights

StrategyName = Literal[
    "DEFAULT",
    "ALWAYS_DISCOUNT",
    "CHEAPEST_ELIGIBLE",
    "SEMANTIC_ONLY",
    "ASTRAOS",
]

STRATEGY_ORDER: tuple[str, ...] = (
    "DEFAULT",
    "ALWAYS_DISCOUNT",
    "CHEAPEST_ELIGIBLE",
    "SEMANTIC_ONLY",
    "ASTRAOS",
)


class BuyerMission(BaseModel):
    id: str
    raw_intent: str
    category: str = "headphones"
    buyer_profile: str
    scenario_tags: list[str] = Field(default_factory=list)
    expected_hard_constraints: list[str] = Field(default_factory=list)
    seed: int
    created_at: datetime | None = None


class StrategyResponse(BaseModel):
    strategy_name: str
    product_id: UUID | None = None
    variant_id: UUID | None = None
    offer_id: UUID | None = None
    sku: str | None = None
    product_name: str | None = None
    total_customer_price_cents: int | None = None
    currency: str = "AUD"
    delivery: str | None = None
    delivery_days: int | None = None
    warranty: str | None = None
    warranty_months: int | None = None
    bundle: str | None = None
    returns: str | None = None
    buyer_utility: float | None = None
    merchant_contribution_cents: int | None = None
    intervention_cost_cents: int | None = None
    hard_constraints_satisfied: bool = False
    policy_safe: bool = False
    transaction_possible: bool = False
    failure_reason: str | None = None
    utility_trace: UtilityTrace | None = None
    used_pareto: bool = False
    used_max_discount: bool = False
    is_cheapest_in_space: bool = False
    runtime_ms: float = 0


class BuyerSelection(BaseModel):
    selected_strategy: str | None
    selected_offer_id: UUID | None = None
    simulated_utility: float | None = None
    no_purchase: bool
    reason: str
    tie_break: str | None = None


class ArenaContext(BaseModel):
    """Shared merchant/buyer snapshot. Strategies must not mutate this."""

    model_config = {"arbitrary_types_allowed": True}

    mission: BuyerMission
    intent: ShoppingIntent
    buyer_profile: str
    weights: UtilityWeights
    matches: list[RankedProductMatch]
    offers: list[OfferCandidate]
    scored: list[ScoredOffer]
    eligible_count: int
    policy_id: UUID | None = None
    policy_margin: float = 0.15
    policy_max_discount: float = 0.10
    catalogue_variant_count: int = 0
    construction_count: int = 0
    feasible_count: int = 0
    policy_safe_count: int = 0
    inventory_fingerprint: str = ""
    recommended_offer_id: UUID | None = None
    optimisation_failure: str | None = None
    merchant_objective: dict[str, Any] | None = None


class MerchantStrategy(Protocol):
    name: str

    def generate_response(self, context: ArenaContext) -> StrategyResponse: ...


class ArenaMissionResult(BaseModel):
    mission: BuyerMission
    responses: list[StrategyResponse]
    selection: BuyerSelection
    runtime_ms: float = 0


class StrategyMetrics(BaseModel):
    strategy_name: str
    missions: int
    wins: int
    selection_rate: float
    avg_buyer_utility: float | None = None
    avg_contribution_when_selected: float | None = None
    contribution_per_opportunity_cents: float
    avg_intervention_cost_cents: float | None = None
    hard_constraint_violation_rate: float
    policy_violation_rate: float
    no_offer_rate: float
    transaction_completion_rate: float
    avg_utility_vs_default: float | None = None
    intervention_efficiency: float | None = None


class SegmentMetrics(BaseModel):
    scenario_tag: str
    buyer_profile: str
    strategy_name: str
    missions: int
    wins: int
    selection_rate: float
    avg_buyer_utility: float | None = None
    avg_contribution_cents: float | None = None


class PairwiseRow(BaseModel):
    left: str
    right: str
    left_wins: float
    right_wins: float
    no_purchase_or_other: float


class ArenaBenchmarkSummary(BaseModel):
    mission_count: int
    no_purchase_rate: float
    seed: int
    strategies: list[str]
    strategy_metrics: list[StrategyMetrics]
    segment_metrics: list[SegmentMetrics]
    pairwise: list[PairwiseRow]
    timing: dict[str, float] = Field(default_factory=dict)
    disclaimer: str = ARENA_DISCLAIMER
    config: dict[str, Any] = Field(default_factory=dict)

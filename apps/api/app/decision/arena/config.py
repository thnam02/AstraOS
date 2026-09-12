"""Explicit Arena benchmark assumptions. Do not hide these in callers."""

from typing import Literal

from pydantic import BaseModel, Field

from app.decision.arena.models import StrategyName
from app.decision.optimisation.objective import MerchantObjectiveConfig, preset

ArenaObjectiveMode = Literal["GROWTH", "BALANCED", "MARGIN"]

ABLATION_STRATEGIES: tuple[StrategyName, ...] = (
    "DEFAULT",
    "ALWAYS_DISCOUNT",
    "SEMANTIC_ONLY",
    "ASTRAOS",
)
EXTENDED_STRATEGIES: tuple[StrategyName, ...] = (
    "DEFAULT",
    "ALWAYS_DISCOUNT",
    "CHEAPEST_ELIGIBLE",
    "SEMANTIC_ONLY",
    "ASTRAOS",
)
DEFAULT_STRATEGIES: tuple[StrategyName, ...] = ABLATION_STRATEGIES
STRATEGY_VERSIONS: dict[str, str] = {
    "DEFAULT": "v1",
    "ALWAYS_DISCOUNT": "v1",
    "CHEAPEST_ELIGIBLE": "v1",
    "SEMANTIC_ONLY": "v1",
    "ASTRAOS": "v1",
}

SEGMENT_SHARES: dict[str, float] = {
    "budget": 0.20,
    "urgent": 0.20,
    "assurance": 0.15,
    "quality": 0.15,
    "balanced": 0.15,
    "gaming_studio": 0.10,
    "difficult": 0.05,
}

PROFILE_FOR_SEGMENT: dict[str, str] = {
    "budget": "BUDGET_SHOPPER",
    "urgent": "URGENT_TRAVELLER",
    "assurance": "ASSURANCE_BUYER",
    "quality": "QUALITY_FIRST",
    "balanced": "BALANCED",
    "gaming_studio": "INTENT_ADAPTED",
    "difficult": "INTENT_ADAPTED",
}


class ArenaBenchmarkConfig(BaseModel):
    mission_count: int = Field(default=100, ge=1, le=5000)
    seed: int = 2026
    strategies: list[StrategyName] = Field(
        default_factory=lambda: list(DEFAULT_STRATEGIES)
    )
    buyer_profile: str | None = None
    outside_option_utility: float = Field(default=0.42, ge=0, le=1)
    transaction_simulation_enabled: bool = False
    max_products: int = Field(default=8, ge=1, le=20)
    segment_shares: dict[str, float] = Field(
        default_factory=lambda: dict(SEGMENT_SHARES)
    )
    persist_missions: bool = True
    merchant_objective_mode: ArenaObjectiveMode = "BALANCED"

    def merchant_objective(self) -> MerchantObjectiveConfig:
        return preset(self.merchant_objective_mode)


class ArenaDuelRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    buyer_profile: str = "INTENT_ADAPTED"
    strategies: list[StrategyName] = Field(
        default_factory=lambda: list(DEFAULT_STRATEGIES)
    )
    outside_option_utility: float = Field(default=0.42, ge=0, le=1)
    seed: int = 2026
    merchant_objective_mode: ArenaObjectiveMode = "BALANCED"

    def merchant_objective(self) -> MerchantObjectiveConfig:
        return preset(self.merchant_objective_mode)

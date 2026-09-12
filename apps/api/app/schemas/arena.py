"""HTTP schemas for the synthetic Agent Arena."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.arena import ARENA_DISCLAIMER
from app.decision.arena.config import DEFAULT_STRATEGIES
from app.decision.arena.models import (
    BuyerSelection,
    SegmentMetrics,
    StrategyMetrics,
    StrategyName,
    StrategyResponse,
)


class ArenaRunRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    buyer_profile: str = "URGENT_TRAVELLER"
    strategies: list[StrategyName] = Field(
        default_factory=lambda: list(DEFAULT_STRATEGIES)
    )
    outside_option_utility: float = Field(default=0.42, ge=0, le=1)
    seed: int = 2026


class ArenaStrategyBlock(BaseModel):
    name: str
    response: StrategyResponse


class ArenaBuyerSelection(BaseModel):
    selected_strategy: str | None
    selected_offer_id: UUID | None = None
    simulated_utility: float | None = None
    no_purchase: bool
    reason: str
    tie_break: str | None = None


class ArenaRunResponse(BaseModel):
    arena_run_id: UUID
    mission_id: str
    buyer_profile: str
    strategies: list[ArenaStrategyBlock]
    buyer_selection: ArenaBuyerSelection
    explanation: dict[str, Any]
    disclaimer: str = ARENA_DISCLAIMER
    created_at: datetime


class ArenaBenchmarkRequest(BaseModel):
    mission_count: int = Field(default=100, ge=1, le=5000)
    seed: int = 2026
    strategies: list[StrategyName] = Field(
        default_factory=lambda: list(DEFAULT_STRATEGIES)
    )
    buyer_profile: str | None = None
    outside_option_utility: float = Field(default=0.42, ge=0, le=1)
    persist_missions: bool = False


class ArenaBenchmarkCreated(BaseModel):
    benchmark_id: UUID
    status: str
    mission_count: int
    seed: int
    disclaimer: str = ARENA_DISCLAIMER


class ArenaBenchmarkResponse(BaseModel):
    benchmark_id: UUID
    status: str
    seed: int
    mission_count: int
    strategies: list[str]
    buyer_model_version: str
    merchant_policy_version: str
    started_at: datetime
    completed_at: datetime | None
    summary: dict[str, Any]
    strategy_metrics: list[StrategyMetrics]
    segment_metrics: list[SegmentMetrics]
    pairwise: list[dict[str, Any]]
    timing: dict[str, float]
    config: dict[str, Any]
    disclaimer: str = ARENA_DISCLAIMER


def selection_to_api(selection: BuyerSelection) -> ArenaBuyerSelection:
    return ArenaBuyerSelection(
        selected_strategy=selection.selected_strategy,
        selected_offer_id=selection.selected_offer_id,
        simulated_utility=selection.simulated_utility,
        no_purchase=selection.no_purchase,
        reason=selection.reason,
        tie_break=selection.tie_break,
    )

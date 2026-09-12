"""Pareto result models. Dominated offers are retained for explanation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ObjectiveSpec(BaseModel):
    name: str
    sense: str  # maximize | minimize
    unit: str


class ParetoResult(BaseModel):
    total_policy_safe_offers: int
    efficient_offer_ids: list[UUID]
    dominated_offer_ids: list[UUID]
    dominated_by: dict[str, UUID | None] = Field(default_factory=dict)
    objective_metadata: list[ObjectiveSpec]
    epsilon: float
    generated_at: datetime

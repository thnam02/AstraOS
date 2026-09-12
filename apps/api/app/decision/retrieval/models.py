"""Semantic match result models. Scores are matching scores, not probabilities."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MatchFact(BaseModel):
    attribute: str
    value: Any
    display: str
    evidence_id: str | None = None
    source_name: str | None = None


class MatchReason(BaseModel):
    need: str
    kind: str
    facts: list[MatchFact] = Field(default_factory=list)


class RankedProductMatch(BaseModel):
    product_id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    brand: str
    variant_name: str | None = None
    base_price_cents: int
    rank: int
    semantic_similarity: float
    product_fit: float
    context_fit: float
    preference_fit: float
    evidence_coverage: float
    overall_semantic_fit: float
    matched_needs: list[str]
    unsupported_needs: list[str]
    reasons: list[MatchReason]
    evidence: list[MatchFact]

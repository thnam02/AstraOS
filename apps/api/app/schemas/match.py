"""HTTP schemas for deep intent analysis and semantic matching."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.intent.models import ShoppingIntent
from app.decision.retrieval.models import RankedProductMatch
from app.schemas.intent import QualificationSummary


class AnalyseRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    parser_mode: Literal["rule_based", "llm"] | None = None


class AnalyseResponse(BaseModel):
    intent: ShoppingIntent
    parse_ms: float


class MatchRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    parser_mode: Literal["rule_based", "llm"] | None = None
    limit: int = Field(default=10, ge=1, le=50)


class MatchTiming(BaseModel):
    intent_parse_ms: float
    qualification_ms: float
    embedding_ms: float
    rerank_ms: float
    total_ms: float


class SemanticMatchingBlock(BaseModel):
    model: str
    document_version: str
    matches: list[RankedProductMatch]
    provider_requested: str | None = None
    provider_used: str | None = None
    dimension: int | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    retrieval_version: str | None = None
    rerank_version: str | None = None


class MatchResponse(BaseModel):
    run_id: UUID
    status: str
    intent: ShoppingIntent
    qualification: QualificationSummary
    semantic_matching: SemanticMatchingBlock
    timing: MatchTiming


class MatchRunResponse(BaseModel):
    run_id: UUID
    status: str
    intent: ShoppingIntent
    qualification: dict[str, Any]
    semantic_matching: SemanticMatchingBlock
    timing: dict[str, Any]
    created_at: datetime

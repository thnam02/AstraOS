"""HTTP schemas for intent qualification. No offer payloads."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.eligibility.models import ConstraintEvaluation
from app.decision.intent.models import ShoppingIntent


class QualifyRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    parser_mode: Literal["rule_based", "llm"] | None = None


class QualificationTiming(BaseModel):
    parse_ms: float
    eligibility_ms: float
    total_ms: float


class QualificationSummary(BaseModel):
    variants_checked: int
    eligible: int
    violated: int
    uncertain: int


class VariantQualificationCard(BaseModel):
    product_id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    brand: str
    variant_name: str | None = None
    base_price_cents: int
    eligible: bool
    outcome: str
    violated_count: int
    unknown_count: int
    satisfied_count: int
    exclusion_reasons: list[str]
    evaluations: list[ConstraintEvaluation]


class QualifyResponse(BaseModel):
    run_id: UUID
    status: str
    intent: ShoppingIntent
    summary: QualificationSummary
    timing: QualificationTiming
    eligible_products: list[VariantQualificationCard]
    uncertain_products: list[VariantQualificationCard]
    rejected_products: list[VariantQualificationCard]
    rejected_truncated: bool = False
    uncertain_truncated: bool = False


class QualificationRunResponse(BaseModel):
    run_id: UUID
    status: str
    raw_intent: str
    intent: ShoppingIntent
    parser_type: str
    summary: dict[str, Any]
    created_at: datetime
    variants: list[VariantQualificationCard]
    total_variants: int
    limit: int
    offset: int


class QualificationVariantDetail(BaseModel):
    run_id: UUID
    variant: VariantQualificationCard

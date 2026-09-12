"""Eligibility result models. Soft preferences never appear here."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConstraintStatus(StrEnum):
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    UNKNOWN = "UNKNOWN"


class EvidenceFreshness(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    MISSING = "MISSING"
    OPERATIONAL = "OPERATIONAL"


class ConstraintEvaluation(BaseModel):
    """One hard-constraint outcome. Exactly SATISFIED, VIOLATED, or UNKNOWN."""

    constraint_id: str
    field: str
    operator: str
    expected_value: Any
    observed_value: Any | None = None
    status: ConstraintStatus
    reason: str
    source_reference: str | None = None
    source_name: str | None = None
    evidence_id: str | None = None
    evidence_freshness: EvidenceFreshness | None = None
    verification_status: str | None = None
    observed_at: datetime | None = None
    expires_at: datetime | None = None
    supporting_detail: str | None = None


class ProductEligibilityResult(BaseModel):
    """Deterministic qualification of one variant against mandatory constraints."""

    product_id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    brand: str
    variant_name: str | None = None
    base_price_cents: int = 0
    evaluations: list[ConstraintEvaluation] = Field(default_factory=list)
    eligible: bool
    violated_count: int
    unknown_count: int
    satisfied_count: int
    exclusion_reasons: list[str] = Field(default_factory=list)

    @property
    def outcome(self) -> str:
        if self.eligible:
            return "eligible"
        if self.violated_count > 0:
            return "rejected"
        return "uncertain"

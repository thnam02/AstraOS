"""Protocol-neutral agent commerce contract. Translation only."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.negotiation.models import CounterConstraints
from app.schemas.optimisation import BuyerProfile

AgentStatus = Literal[
    "PROPOSED",
    "COUNTERED",
    "DECLINED",
    "CLARIFICATION_REQUIRED",
    "NO_ELIGIBLE_PRODUCT",
    "NO_POLICY_SAFE_OFFER",
    "ACCEPTED",
    "CONFIRMED",
    "REVALIDATION_FAILED",
    "ERROR",
]


class StructuredConstraints(BaseModel):
    max_total_price_cents: int | None = None
    same_day_required: bool | None = None
    quantity: int | None = Field(default=None, ge=1, le=20)


class AgentOfferRequest(BaseModel):
    request_id: UUID | None = None
    buyer_agent_id: str | None = Field(default=None, max_length=80)
    natural_language_intent: str = Field(min_length=1, max_length=4000)
    structured_constraints: StructuredConstraints | None = None
    buyer_profile: BuyerProfile = "INTENT_ADAPTED"
    quantity: int = Field(default=1, ge=1, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentCounterRequest(BaseModel):
    session_id: UUID
    message: str | None = Field(default=None, max_length=4000)
    constraints: CounterConstraints | None = None


class AgentAcceptRequest(BaseModel):
    session_id: UUID
    proposal_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)
    quantity: int = Field(default=1, ge=1, le=20)


class EvidenceClaim(BaseModel):
    claim: str
    value: Any
    source_type: str
    source_reference: str | None = None
    observed_at: datetime | None = None
    freshness: Literal["CURRENT", "STALE", "UNKNOWN"] = "CURRENT"
    verification_status: Literal["VERIFIED", "UNVERIFIED", "CONFLICTED", "UNKNOWN"] = (
        "UNVERIFIED"
    )
    evidence_id: str | None = None
    display_claim: str | None = None
    derived: bool = False
    derivation_rule: str | None = None
    unit: str | None = None


class AgentProposalView(BaseModel):
    proposal_id: UUID
    product: dict[str, Any] | None = None
    pricing: dict[str, Any] | None = None
    delivery: dict[str, Any] | None = None
    warranty: dict[str, Any] | None = None
    bundle: dict[str, Any] | None = None
    returns: dict[str, Any] | None = None
    total: dict[str, Any] | None = None
    expiry: datetime | None = None
    outcome: str | None = None


class AgentErrorBody(BaseModel):
    error_code: str
    machine_message: str
    human_debug_message: str | None = None
    allowed_next_actions: list[str] = Field(default_factory=list)


class AgentOfferResponse(BaseModel):
    request_id: UUID
    decision_id: UUID | None = None
    negotiation_session_id: UUID | None = None
    status: AgentStatus
    understood_intent: dict[str, Any] | None = None
    qualification_summary: dict[str, Any] | None = None
    semantic_match_summary: dict[str, Any] | None = None
    proposal: AgentProposalView | None = None
    merchant_reasoning: list[str] = Field(default_factory=list)
    proof: list[EvidenceClaim] = Field(default_factory=list)
    policy_status: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    constraint_discrepancies: list[str] = Field(default_factory=list)
    lineage: dict[str, Any] = Field(default_factory=dict)
    timing: dict[str, float] = Field(default_factory=dict)
    error: AgentErrorBody | None = None
    disclaimer: str = (
        "AstraOS returns a merchant proposal, not a purchase probability. "
        "Buyer utility is a transparent cold-start simulation."
    )


class AgentTransactionResponse(BaseModel):
    request_id: UUID
    status: AgentStatus
    transaction_id: UUID | None = None
    order: dict[str, Any] | None = None
    revalidation: dict[str, Any] | None = None
    failure_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    lineage: dict[str, Any] = Field(default_factory=dict)
    timing: dict[str, float] = Field(default_factory=dict)
    error: AgentErrorBody | None = None


class AgentCapabilities(BaseModel):
    service: str = "astraos-agent-gateway"
    protocol_name: str = "astraos-agent"
    version: str = "1.0"
    operations: list[str]
    supported: list[str]
    not_supported: list[str]
    protocol: list[str]
    disclaimer: str


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    detail: str
    required: bool = True


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded", "not_ready"]
    service: str = "astraos-api"
    checks: list[ReadinessCheck]
    degraded_mode: list[str] = Field(default_factory=list)

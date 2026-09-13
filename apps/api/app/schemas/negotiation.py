"""HTTP schemas for B2A negotiation."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.negotiation.models import (
    BuyerAction,
    CounterConstraints,
    MerchantProposalDTO,
)
from app.schemas.match import MatchResponse
from app.schemas.offer import GenerateOffersResponse
from app.schemas.optimisation import BuyerProfile, OptimisationResponse

BuyerAgentType = Literal[
    "DETERMINISTIC_SIMULATION",
    "LLM_NEGOTIATION",
    "MANUAL",
]


class CreateNegotiationRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=4000)
    buyer_profile: BuyerProfile = "INTENT_ADAPTED"
    buyer_agent_type: BuyerAgentType = "MANUAL"
    parser_mode: Literal["rule_based", "llm"] | None = None
    max_products: int = Field(default=8, ge=1, le=20)
    channel: Literal["OPERATOR", "AGENT_API"] = "OPERATOR"
    request_id: str | None = Field(default=None, max_length=80)
    buyer_agent_id: str | None = Field(default=None, max_length=80)


class BuyerTurnRequest(BaseModel):
    message: str | None = Field(default=None, max_length=4000)
    action: BuyerAction | None = None
    constraints: CounterConstraints = Field(default_factory=CounterConstraints)
    interpreter: Literal["rule_based", "llm"] = "rule_based"


class SimulateBuyerRequest(BaseModel):
    mode: Literal["BUDGET", "URGENT", "ASSURANCE", "BALANCED", "TRAVEL"] = (
        "TRAVEL"
    )


class NegotiationTurnView(BaseModel):
    turn_id: UUID
    turn_number: int
    actor: str
    raw_message: str | None
    structured_action: str
    structured_payload: dict[str, Any]
    related_offer_id: UUID | None
    related_proposal_id: UUID | None = None
    created_at: datetime


class CommercialState(BaseModel):
    minimum_margin_rate: float
    maximum_discount_rate: float
    inventory_units: int | None = None
    expires_at: datetime | None = None
    current_sku: str | None = None


class NegotiationTiming(BaseModel):
    message_interpretation_ms: float = 0
    delta_application_ms: float = 0
    reoptimisation_ms: float = 0
    proposal_generation_ms: float = 0
    total_turn_ms: float = 0


class NegotiationResponse(BaseModel):
    session_id: UUID
    state: str
    proposal: MerchantProposalDTO | None
    previous_proposal: MerchantProposalDTO | None = None
    turns: list[NegotiationTurnView]
    proposals: list[MerchantProposalDTO]
    commercial: CommercialState | None = None
    timing: NegotiationTiming | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    original_intent: dict[str, Any] | None = None
    working_intent: dict[str, Any] | None = None
    merchant_policy_version: str | None = None
    match: MatchResponse | None = None
    construction: GenerateOffersResponse | None = None
    optimisation: OptimisationResponse | None = None

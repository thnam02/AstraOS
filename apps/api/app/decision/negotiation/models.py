"""Canonical negotiation DTOs. Future protocol adapters map onto these."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class NegotiationState(StrEnum):
    CREATED = "CREATED"
    BUYER_REQUEST_RECEIVED = "BUYER_REQUEST_RECEIVED"
    MERCHANT_PROPOSAL_CREATED = "MERCHANT_PROPOSAL_CREATED"
    BUYER_ACCEPTED = "BUYER_ACCEPTED"
    BUYER_REJECTED = "BUYER_REJECTED"
    BUYER_COUNTERED = "BUYER_COUNTERED"
    MERCHANT_COUNTER_CREATED = "MERCHANT_COUNTER_CREATED"
    NO_POLICY_SAFE_COUNTER = "NO_POLICY_SAFE_COUNTER"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    READY_FOR_CHECKOUT = "READY_FOR_CHECKOUT"
    NEGOTIATION_LIMIT_REACHED = "NEGOTIATION_LIMIT_REACHED"


class Actor(StrEnum):
    BUYER_AGENT = "BUYER_AGENT"
    MERCHANT_AGENT = "MERCHANT_AGENT"
    SYSTEM = "SYSTEM"


class BuyerAction(StrEnum):
    REQUEST = "REQUEST"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COUNTER = "COUNTER"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"


class MerchantAction(StrEnum):
    PROPOSE = "PROPOSE"
    COUNTER = "COUNTER"
    DECLINE = "DECLINE"
    CLARIFY = "CLARIFY"
    READY_FOR_CHECKOUT = "READY_FOR_CHECKOUT"


class ProposalType(StrEnum):
    INITIAL = "INITIAL"
    COUNTER = "COUNTER"
    ALTERNATIVE_PRODUCT = "ALTERNATIVE_PRODUCT"


class MerchantOutcome(StrEnum):
    ACCEPT_BUYER_COUNTER = "ACCEPT_BUYER_COUNTER"
    COUNTEROFFER = "COUNTEROFFER"
    DECLINE = "DECLINE"
    ALTERNATIVE_PRODUCT = "ALTERNATIVE_PRODUCT"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    NEGOTIATION_LIMIT_REACHED = "NEGOTIATION_LIMIT_REACHED"


class ReasonCode(StrEnum):
    EXACT_COUNTER_SATISFIED = "EXACT_COUNTER_SATISFIED"
    CLOSEST_POLICY_SAFE_COUNTER = "CLOSEST_POLICY_SAFE_COUNTER"
    REQUESTED_PRICE_BELOW_MARGIN_FLOOR = "REQUESTED_PRICE_BELOW_MARGIN_FLOOR"
    DISCOUNT_EXCEEDS_LIMIT = "DISCOUNT_EXCEEDS_LIMIT"
    NO_POLICY_SAFE_OFFER = "NO_POLICY_SAFE_OFFER"
    SAME_PRODUCT_UNAVAILABLE_AT_REQUEST = (
        "SAME_PRODUCT_UNAVAILABLE_AT_REQUEST"
    )
    ALTERNATIVE_PRODUCT_SELECTED = "ALTERNATIVE_PRODUCT_SELECTED"
    ORIGINAL_CONSTRAINTS_RETAINED = "ORIGINAL_CONSTRAINTS_RETAINED"
    REQUESTED_DELIVERY_UNAVAILABLE = "REQUESTED_DELIVERY_UNAVAILABLE"
    UNSUPPORTED_INSTRUCTION = "UNSUPPORTED_INSTRUCTION"
    AMBIGUOUS_REQUEST = "AMBIGUOUS_REQUEST"
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    NEGOTIATION_LIMIT_REACHED = "NEGOTIATION_LIMIT_REACHED"
    BUYER_ACCEPTED = "BUYER_ACCEPTED"
    BUYER_REJECTED = "BUYER_REJECTED"
    PROMPT_INJECTION_IGNORED = "PROMPT_INJECTION_IGNORED"


class CounterConstraints(BaseModel):
    """Machine-actionable buyer request. Never applied by an LLM to money."""

    max_total_price_cents: int | None = None
    requested_delivery_days: int | None = None
    relax_same_day: bool = False
    requested_warranty_months: int | None = None
    requested_bundle: str | None = None
    requested_return_window_days: int | None = None
    alternative_product_allowed: bool = True
    foldable_required: bool | None = None
    preference_changes: list[str] = Field(default_factory=list)


class BuyerTurnInput(BaseModel):
    action: BuyerAction | None = None
    constraints: CounterConstraints = Field(default_factory=CounterConstraints)
    message: str | None = None


class InterpretedBuyerTurn(BaseModel):
    action: BuyerAction
    constraints: CounterConstraints
    raw_message: str | None = None
    prompt_injection: bool = False
    ambiguous: bool = False
    source: Literal["rule_based", "llm", "structured"] = "rule_based"
    notes: list[str] = Field(default_factory=list)


class NegotiationDelta(BaseModel):
    """Incremental change over the original ShoppingIntent. History is kept."""

    price_constraint_change: int | None = None
    delivery_constraint_change: int | None = None
    relax_same_day: bool = False
    warranty_constraint_change: int | None = None
    bundle_change: str | None = None
    returns_change: int | None = None
    product_substitution_allowed: bool = True
    foldable_required: bool | None = None
    preference_adjustments: list[str] = Field(default_factory=list)
    rematch_required: bool = False
    reconstruct_required: bool = True


class CompromiseBreakdown(BaseModel):
    price_gap: float
    delivery_gap: float
    warranty_gap: float
    bundle_gap: float
    returns_gap: float
    score: float
    formula: str


class MerchantProposalDTO(BaseModel):
    proposal_id: UUID
    negotiation_session_id: UUID
    version: int
    proposal_type: str
    outcome: str
    offer_id: UUID | None
    offer: dict[str, Any] | None
    reason_codes: list[str]
    explanation: list[str]
    next_allowed_actions: list[str]
    compromise: dict[str, Any] | CompromiseBreakdown | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None

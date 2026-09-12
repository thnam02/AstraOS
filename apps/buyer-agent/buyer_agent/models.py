"""Buyer-side mission and decision types. Not merchant ShoppingIntent."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

BuyerAction = Literal["ACCEPT", "REJECT", "COUNTER", "INSPECT"]
BuyerMode = Literal["deterministic", "llm"]
Persona = Literal[
    "URGENT_TRAVELLER",
    "BUDGET_BUYER",
    "ASSURANCE_BUYER",
    "QUALITY_BUYER",
    "BALANCED",
]
EndState = Literal[
    "ACCEPTED",
    "REJECTED",
    "NO_SAFE_OFFER",
    "EXPIRED",
    "MAX_TURNS",
    "TRANSACTION_FAILED",
    "ERROR",
]


class BuyerProfile(BaseModel):
    urgency: Literal["low", "medium", "high"] = "medium"
    comfort: Literal["low", "medium", "high"] = "medium"
    reliability: Literal["low", "medium", "high"] = "medium"
    price_sensitivity: Literal["low", "medium", "high"] = "medium"
    quality: Literal["low", "medium", "high"] = "medium"


class BuyerHardRequirements(BaseModel):
    max_total_cents: int | None = None
    same_day_required: bool = False
    max_delivery_days: int | None = None
    require_anc: bool = False
    require_wireless: bool = False
    excluded_brands: list[str] = Field(default_factory=list)


class BuyerMission(BaseModel):
    mission_id: str
    request: str
    persona: Persona = "BALANCED"
    profile: BuyerProfile = Field(default_factory=BuyerProfile)
    hard: BuyerHardRequirements = Field(default_factory=BuyerHardRequirements)
    acceptance_threshold: float = 0.62
    max_turns: int = 4
    negotiation_style: str = "balanced"


class PublicCounter(BaseModel):
    """Buyer-requested changes. Never merchant selling prices."""

    max_total_price_cents: int | None = None
    requested_delivery_days: int | None = None
    relax_same_day: bool = False
    requested_warranty_months: int | None = None
    requested_bundle: str | None = None
    requested_return_window_days: int | None = None
    alternative_product_allowed: bool = True
    foldable_required: bool | None = None
    preference_changes: list[str] = Field(default_factory=list)
    message: str | None = None


class BuyerDecision(BaseModel):
    action: BuyerAction
    reason_summary: str
    counter: PublicCounter | None = None
    requested_proof: list[str] = Field(default_factory=list)


class PublicProposal(BaseModel):
    proposal_id: str | None = None
    session_id: str | None = None
    status: str = ""
    product_name: str | None = None
    sku: str | None = None
    brand: str | None = None
    total_cents: int | None = None
    currency: str = "AUD"
    delivery_days: int | None = None
    delivery_name: str | None = None
    warranty_months: int | None = None
    bundle_name: str | None = None
    expiry: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    proof: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class BuyerRunResult(BaseModel):
    run_id: str
    buyer_agent_version: str
    buyer_mode: BuyerMode
    fallback_used: bool = False
    fallback_reason: str | None = None
    mission: BuyerMission
    end_state: EndState
    turns: int = 0
    inspect_count: int = 0
    order_ref: str | None = None
    transaction_id: str | None = None
    proposal_id: str | None = None
    session_id: str | None = None
    final_total_cents: int | None = None
    final_product: str | None = None
    latencies_ms: dict[str, float] = Field(default_factory=dict)
    token_usage: dict[str, int] | None = None
    actions: list[str] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

"""HTTP schemas for proposal acceptance and local order execution."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.decision.negotiation.models import MerchantProposalDTO
from app.decision.transaction.models import TransactionTiming


class AcceptProposalRequest(BaseModel):
    """Buyer Agent submits a proposal id only. Prices are ignored."""

    model_config = ConfigDict(extra="ignore")

    proposal_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=128)
    quantity: int = Field(default=1, ge=1, le=20)
    generate_recovery: bool = True


class RevalidationView(BaseModel):
    status: str
    checks: list[dict[str, Any]] = Field(default_factory=list)
    failure_codes: list[str] = Field(default_factory=list)
    current_state_snapshot: dict[str, Any] = Field(default_factory=dict)
    validated_at: datetime | None = None


class ReservationView(BaseModel):
    reservation_id: UUID
    status: str
    variant_id: UUID | None = None
    quantity: int | None = None


class OrderView(BaseModel):
    order_id: UUID
    order_number: str
    status: str
    sku: str
    product_name: str
    quantity: int
    product_price_cents: int
    delivery_charge_cents: int
    warranty_price_cents: int
    bundle_price_cents: int
    total_amount_cents: int
    currency: str
    delivery_code: str | None = None
    warranty_code: str | None = None
    bundle_code: str | None = None
    return_policy_code: str | None = None
    warranty_months: int | None = None
    payment_mode: str
    payment_status: str
    confirmation: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    confirmed_at: datetime | None = None


class AcceptProposalResponse(BaseModel):
    transaction_id: UUID
    state: str
    negotiation_state: str | None = None
    proposal_id: UUID
    offer_id: UUID | None = None
    revalidation: RevalidationView | None = None
    reservation: ReservationView | None = None
    order: OrderView | None = None
    failure_codes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    recovery_proposal: MerchantProposalDTO | None = None
    timing: TransactionTiming | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    lineage: dict[str, Any] = Field(default_factory=dict)


class TransactionDetailResponse(AcceptProposalResponse):
    session_id: UUID
    proposal: MerchantProposalDTO | None = None


class DemoInventoryRequest(BaseModel):
    sku: str | None = None
    variant_id: UUID | None = None
    units_available: int = Field(ge=0)


class DemoDeliveryCapacityRequest(BaseModel):
    sku: str | None = None
    variant_id: UUID | None = None
    delivery_code: str = "SAME_DAY"
    available: bool


class DemoPolicyRequest(BaseModel):
    minimum_margin_rate: float | None = Field(default=None, ge=0, lt=1)
    maximum_discount_rate: float | None = Field(default=None, ge=0, le=1)


class DemoStateResponse(BaseModel):
    sku: str
    variant_id: UUID
    units_available: int
    units_reserved: int
    sellable_units: int
    delivery_code: str | None = None
    delivery_available: bool | None = None
    minimum_margin_rate: float
    note: str = "HACKATHON DEMO CONTROL — mutates live merchant state."

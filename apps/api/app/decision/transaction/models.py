"""Transaction, reservation, and revalidation domain types."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TransactionState(StrEnum):
    PENDING = "PENDING"
    REVALIDATING = "REVALIDATING"
    REVALIDATION_FAILED = "REVALIDATION_FAILED"
    READY_TO_RESERVE = "READY_TO_RESERVE"
    RESERVING = "RESERVING"
    RESERVATION_FAILED = "RESERVATION_FAILED"
    RESERVED = "RESERVED"
    CREATING_ORDER = "CREATING_ORDER"
    ORDER_FAILED = "ORDER_FAILED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ReservationStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class TransactionFailureCode(StrEnum):
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    PROPOSAL_NOT_CURRENT = "PROPOSAL_NOT_CURRENT"
    PROPOSAL_NOT_FOUND = "PROPOSAL_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_NOT_ACCEPTABLE = "SESSION_NOT_ACCEPTABLE"
    PRODUCT_INACTIVE = "PRODUCT_INACTIVE"
    VARIANT_INACTIVE = "VARIANT_INACTIVE"
    PRICE_CHANGED = "PRICE_CHANGED"
    DISCOUNT_NO_LONGER_ALLOWED = "DISCOUNT_NO_LONGER_ALLOWED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    DELIVERY_NO_LONGER_AVAILABLE = "DELIVERY_NO_LONGER_AVAILABLE"
    WARRANTY_NO_LONGER_AVAILABLE = "WARRANTY_NO_LONGER_AVAILABLE"
    BUNDLE_NO_LONGER_AVAILABLE = "BUNDLE_NO_LONGER_AVAILABLE"
    RETURN_POLICY_CHANGED = "RETURN_POLICY_CHANGED"
    MARGIN_POLICY_VIOLATION = "MARGIN_POLICY_VIOLATION"
    MERCHANT_POLICY_CHANGED = "MERCHANT_POLICY_CHANGED"
    BUYER_MAX_TOTAL_EXCEEDED = "BUYER_MAX_TOTAL_EXCEEDED"
    BUYER_MAX_PRODUCT_PRICE_EXCEEDED = "BUYER_MAX_PRODUCT_PRICE_EXCEEDED"
    RESERVATION_FAILED = "RESERVATION_FAILED"
    ORDER_CREATION_FAILED = "ORDER_CREATION_FAILED"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    ALREADY_TRANSACTED = "ALREADY_TRANSACTED"


class RevalidationCheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class RevalidationCheck(BaseModel):
    check: str
    status: RevalidationCheckStatus
    available_units: int | None = None
    observed: str | int | float | None = None
    message: str | None = None


class TransactionRevalidationResult(BaseModel):
    valid: bool
    checks: list[RevalidationCheck] = Field(default_factory=list)
    failure_codes: list[TransactionFailureCode] = Field(default_factory=list)
    current_state_snapshot: dict[str, Any] = Field(default_factory=dict)
    validated_at: datetime


class TransactionEvent(BaseModel):
    type: str
    at: datetime
    state: str
    details: dict[str, Any] = Field(default_factory=dict)


class TransactionTiming(BaseModel):
    revalidation_ms: float = 0
    reservation_ms: float = 0
    order_creation_ms: float = 0
    total_transaction_ms: float = 0


class ReservationResult(BaseModel):
    reservation_id: UUID
    status: ReservationStatus
    variant_id: UUID
    quantity: int
    reserved_at: datetime | None = None
    expires_at: datetime | None = None


class OrderSnapshot(BaseModel):
    order_id: UUID
    order_number: str
    status: OrderStatus
    variant_id: UUID
    sku: str
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
    payment_mode: str = "SIMULATED"
    payment_status: str = "NOT_REQUIRED_FOR_DEMO"
    created_at: datetime | None = None
    confirmed_at: datetime | None = None

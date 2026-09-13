"""Offer construction domain models. No optimisation or buyer utility."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConstructionStatus(StrEnum):
    GENERATED = "GENERATED"
    BLOCKED = "BLOCKED"


class FeasibilityStatus(StrEnum):
    FEASIBLE = "FEASIBLE"
    REJECTED = "REJECTED"


class RejectionCode(StrEnum):
    OUT_OF_STOCK = "OUT_OF_STOCK"
    DELIVERY_NOT_AVAILABLE = "DELIVERY_NOT_AVAILABLE"
    WARRANTY_NOT_AVAILABLE = "WARRANTY_NOT_AVAILABLE"
    BUNDLE_INCOMPATIBLE = "BUNDLE_INCOMPATIBLE"
    RETURN_POLICY_DISABLED = "RETURN_POLICY_DISABLED"
    DISCOUNT_EXCEEDS_AUTHORITY = "DISCOUNT_EXCEEDS_AUTHORITY"
    MISSING_OPERATIONAL_DATA = "MISSING_OPERATIONAL_DATA"
    PRODUCT_INACTIVE = "PRODUCT_INACTIVE"
    CANDIDATE_LIMIT_PRUNED = "CANDIDATE_LIMIT_PRUNED"
    BUYER_MAX_TOTAL_EXCEEDED = "BUYER_MAX_TOTAL_EXCEEDED"
    BUYER_MAX_PRODUCT_PRICE_EXCEEDED = "BUYER_MAX_PRODUCT_PRICE_EXCEEDED"


class RejectionReason(BaseModel):
    code: RejectionCode
    message: str


class PriceOption(BaseModel):
    adjustment_type: str
    adjustment_rate: Decimal
    adjustment_cents: int
    final_price_cents: int


class OfferProof(BaseModel):
    type: str
    value: Any
    source: str
    source_name: str | None = None
    evidence_id: str | None = None
    updated_at: datetime | None = None


class BundleRelevance(BaseModel):
    code: str
    name: str
    triggered_by: list[str] = Field(default_factory=list)
    variant_compatible: bool
    merchant_available: bool


class OfferCandidate(BaseModel):
    """One commercial configuration. Not a recommended or winning offer."""

    id: UUID
    offer_run_id: UUID | None = None
    product_id: UUID
    variant_id: UUID
    sku: str
    product_name: str
    brand: str
    variant_name: str | None = None
    currency: str = "AUD"

    base_price_cents: int
    price_adjustment_cents: int
    final_product_price_cents: int
    price_adjustment_type: str
    price_adjustment_rate: Decimal

    delivery_option_id: UUID | None = None
    delivery_code: str
    delivery_name: str
    delivery_days: int
    delivery_customer_charge_cents: int
    delivery_merchant_cost_cents: int

    warranty_option_id: UUID | None = None
    warranty_code: str
    warranty_name: str
    warranty_months: int
    warranty_customer_price_cents: int
    warranty_merchant_cost_cents: int

    bundle_option_id: UUID | None = None
    bundle_code: str | None = None
    bundle_name: str | None = None
    bundle_customer_price_cents: int = 0
    bundle_merchant_cost_cents: int = 0
    bundle_relevance: BundleRelevance | None = None

    return_policy_id: UUID | None = None
    return_policy_code: str | None = None
    return_policy_name: str | None = None
    return_window_days: int | None = None
    return_policy_expected_cost_cents: int | None = None

    total_customer_price_cents: int
    direct_intervention_cost_cents: int

    construction_status: ConstructionStatus
    feasibility_status: FeasibilityStatus
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    proof: list[OfferProof] = Field(default_factory=list)
    construction_metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None
    created_at: datetime | None = None


class ConstructionLimits(BaseModel):
    max_products: int = 8
    max_price_options: int = 5
    max_delivery_options: int = 3
    max_warranty_options: int = 3
    max_bundles_per_product: int = 4
    max_return_options: int = 2
    max_total_candidates: int = 5000
    offer_ttl_seconds: int = 300


CONSTRUCTION_VERSION = "offer.v1"
CURRENCY = "AUD"

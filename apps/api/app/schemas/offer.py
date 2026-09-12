"""HTTP schemas for offer construction. No recommended-offer fields."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.intent.models import ShoppingIntent
from app.decision.offers.models import OfferCandidate


class GenerateOffersRequest(BaseModel):
    intent: str | None = Field(default=None, max_length=4000)
    match_run_id: UUID | None = None
    parser_mode: Literal["rule_based", "llm"] | None = None
    max_products: int = Field(default=8, ge=1, le=20)
    status: Literal["FEASIBLE", "REJECTED", "ALL"] = "FEASIBLE"
    limit: int = Field(default=50, ge=1, le=200)


class OfferTiming(BaseModel):
    matching_load_ms: float
    dimension_load_ms: float
    combination_generation_ms: float
    feasibility_filter_ms: float
    persistence_ms: float
    total_ms: float


class OfferDimensions(BaseModel):
    price_options: int
    delivery_options: int
    warranty_options: int
    bundle_options: int
    return_options: int


class OfferSummary(BaseModel):
    estimated_candidates: int
    generated_candidates: int
    feasible_candidates: int
    rejected_candidates: int
    pruning_reason: str | None = None
    rejection_distribution: dict[str, int] = Field(default_factory=dict)


class PublicOffer(BaseModel):
    offer_id: UUID
    product: dict[str, Any]
    pricing: dict[str, Any]
    delivery: dict[str, Any]
    warranty: dict[str, Any]
    bundle: dict[str, Any] | None
    returns: dict[str, Any] | None
    proof: list[dict[str, Any]]
    expires_at: datetime | None
    feasibility_status: str
    construction_status: str
    rejection_reasons: list[dict[str, Any]] = Field(default_factory=list)
    direct_intervention_cost_cents: int
    bundle_relevance: dict[str, Any] | None = None


class GenerateOffersResponse(BaseModel):
    offer_run_id: UUID
    match_run_id: UUID | None
    intent: ShoppingIntent
    input: dict[str, Any]
    summary: OfferSummary
    dimensions: OfferDimensions
    timing: OfferTiming
    offers: list[PublicOffer]
    truncated: bool = False


class OfferRunResponse(BaseModel):
    offer_run_id: UUID
    match_run_id: UUID | None
    intent: ShoppingIntent
    summary: OfferSummary
    dimensions: OfferDimensions
    timing: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None
    offers: list[PublicOffer]
    total_offers: int
    limit: int
    offset: int


class OfferDetailResponse(BaseModel):
    offer: OfferCandidate
    public: PublicOffer


def to_public(offer: OfferCandidate) -> PublicOffer:
    return PublicOffer(
        offer_id=offer.id,
        product={
            "variant_id": str(offer.variant_id),
            "product_id": str(offer.product_id),
            "sku": offer.sku,
            "name": offer.product_name,
            "brand": offer.brand,
            "variant_name": offer.variant_name,
        },
        pricing={
            "product_price_cents": offer.final_product_price_cents,
            "base_price_cents": offer.base_price_cents,
            "adjustment_cents": offer.price_adjustment_cents,
            "adjustment_type": offer.price_adjustment_type,
            "delivery_charge_cents": offer.delivery_customer_charge_cents,
            "warranty_price_cents": offer.warranty_customer_price_cents,
            "bundle_price_cents": offer.bundle_customer_price_cents,
            "total_price_cents": offer.total_customer_price_cents,
            "currency": offer.currency,
        },
        delivery={
            "code": offer.delivery_code,
            "name": offer.delivery_name,
            "days": offer.delivery_days,
        },
        warranty={
            "code": offer.warranty_code,
            "name": offer.warranty_name,
            "months": offer.warranty_months,
        },
        bundle=(
            None
            if not offer.bundle_code
            else {"code": offer.bundle_code, "name": offer.bundle_name}
        ),
        returns=(
            None
            if not offer.return_policy_code
            else {
                "code": offer.return_policy_code,
                "name": offer.return_policy_name,
                "window_days": offer.return_window_days,
            }
        ),
        proof=[item.model_dump(mode="json") for item in offer.proof],
        expires_at=offer.expires_at,
        feasibility_status=offer.feasibility_status.value,
        construction_status=offer.construction_status.value,
        rejection_reasons=[
            item.model_dump(mode="json") for item in offer.rejection_reasons
        ],
        direct_intervention_cost_cents=offer.direct_intervention_cost_cents,
        bundle_relevance=(
            offer.bundle_relevance.model_dump(mode="json")
            if offer.bundle_relevance
            else None
        ),
    )

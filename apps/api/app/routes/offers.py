"""Offer construction HTTP routes. No ranking or recommendation."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.offer import (
    GenerateOffersRequest,
    GenerateOffersResponse,
    OfferDetailResponse,
    OfferRunResponse,
)
from app.services.offers import OfferConstructionService

router = APIRouter(prefix="/offers", tags=["offers"])


def _service(db: AsyncSession = Depends(get_db)) -> OfferConstructionService:
    return OfferConstructionService(db)


@router.post("/generate", response_model=GenerateOffersResponse)
async def generate_offers(
    payload: GenerateOffersRequest,
    service: OfferConstructionService = Depends(_service),
) -> GenerateOffersResponse:
    if not payload.intent and payload.match_run_id is None:
        raise HTTPException(
            status_code=422, detail="intent or match_run_id is required"
        )
    try:
        return await service.generate(
            intent_text=payload.intent,
            match_run_id=payload.match_run_id,
            parser_mode=payload.parser_mode,
            max_products=payload.max_products,
            preview_status=payload.status,
            preview_limit=payload.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{offer_run_id}", response_model=OfferRunResponse)
async def get_offer_run(
    offer_run_id: uuid.UUID,
    product_id: uuid.UUID | None = Query(default=None),
    delivery: str | None = Query(default=None),
    warranty: str | None = Query(default=None),
    bundle: str | None = Query(default=None),
    returns: str | None = Query(default=None),
    max_price_cents: int | None = Query(default=None),
    status: str = Query(default="FEASIBLE"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: OfferConstructionService = Depends(_service),
) -> OfferRunResponse:
    detail = await service.get_run(
        offer_run_id,
        product_id=product_id,
        delivery_code=delivery,
        warranty_code=warranty,
        bundle_code=bundle,
        return_policy_code=returns,
        max_price_cents=max_price_cents,
        status=status,
        limit=limit,
        offset=offset,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Offer run not found")
    return detail


@router.get("/{offer_id}", response_model=OfferDetailResponse)
async def get_offer(
    offer_id: uuid.UUID,
    service: OfferConstructionService = Depends(_service),
) -> OfferDetailResponse:
    detail = await service.get_offer(offer_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return detail

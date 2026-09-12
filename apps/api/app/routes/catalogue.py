"""Catalogue inspection routes. No commercial decisions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.product import (
    CatalogueStatsResponse,
    ProductDetail,
    ProductListResponse,
    ProductVariantDetail,
)
from app.services.catalogue import CatalogueService

router = APIRouter(prefix="/catalogue", tags=["catalogue"])


def _service(db: AsyncSession = Depends(get_db)) -> CatalogueService:
    return CatalogueService(db)


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    category: str | None = None,
    brand: str | None = None,
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: CatalogueService = Depends(_service),
) -> ProductListResponse:
    return await service.list_products(
        category=category,
        brand=brand,
        active_only=active_only,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{product_id}", response_model=ProductDetail)
async def get_product(
    product_id: uuid.UUID,
    service: CatalogueService = Depends(_service),
) -> ProductDetail:
    detail = await service.get_product(product_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return detail


@router.get("/variants/{variant_id}", response_model=ProductVariantDetail)
async def get_variant(
    variant_id: uuid.UUID,
    service: CatalogueService = Depends(_service),
) -> ProductVariantDetail:
    detail = await service.get_variant(variant_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    return detail


@router.get("/stats", response_model=CatalogueStatsResponse)
async def get_stats(
    service: CatalogueService = Depends(_service),
) -> CatalogueStatsResponse:
    return await service.stats()

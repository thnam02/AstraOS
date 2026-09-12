"""Merchant-side catalogue ingestion. Not part of /api/v1/agent/*."""

from __future__ import annotations

import base64
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.ingestion.constants import SOURCE_CSV, SOURCE_JSON
from app.ingestion.pipeline import IngestionPayloadError
from app.ingestion.service import MerchantIngestionService
from app.models import Merchant, Product, ProductVariant
from app.schemas.ingestion import (
    IngestionRequest,
    IngestionResultResponse,
    IngestionRunDetail,
    IngestionRunListResponse,
    IngestionRunSummary,
    MerchantDataStatusResponse,
)

router = APIRouter(prefix="/merchant/ingestion", tags=["merchant-ingestion"])


def _service(db: AsyncSession = Depends(get_db)) -> MerchantIngestionService:
    return MerchantIngestionService(db)


def _source_type(value: str) -> str:
    key = value.strip().lower()
    if key in {"json", SOURCE_JSON}:
        return SOURCE_JSON
    if key in {"csv", "zip", SOURCE_CSV}:
        return SOURCE_CSV
    raise HTTPException(status_code=422, detail="source_type must be json or csv")


def _payload(body: IngestionRequest) -> bytes:
    if body.snapshot is not None:
        return json.dumps(body.snapshot).encode("utf-8")
    if body.content_base64:
        try:
            return base64.b64decode(body.content_base64, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=422, detail="Invalid base64 content"
            ) from exc
    raise HTTPException(
        status_code=422, detail="Provide snapshot JSON or content_base64."
    )


@router.post("/validate", response_model=IngestionResultResponse)
async def validate_ingestion(
    body: IngestionRequest,
    service: MerchantIngestionService = Depends(_service),
) -> IngestionResultResponse:
    try:
        result = await service.run(
            _payload(body),
            source_type=_source_type(body.source_type),
            source_name=body.source_name,
            snapshot_mode=body.snapshot_mode,
            deactivate_scope=body.deactivate_scope,
            dry_run=True,
            initiated_by=body.initiated_by or "merchant_api",
        )
    except IngestionPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestionResultResponse.model_validate(result.as_dict())


@router.post("/import", response_model=IngestionResultResponse)
async def import_ingestion(
    body: IngestionRequest,
    service: MerchantIngestionService = Depends(_service),
) -> IngestionResultResponse:
    try:
        result = await service.run(
            _payload(body),
            source_type=_source_type(body.source_type),
            source_name=body.source_name,
            snapshot_mode=body.snapshot_mode,
            deactivate_scope=body.deactivate_scope,
            dry_run=False,
            initiated_by=body.initiated_by or "merchant_api",
        )
    except IngestionPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestionResultResponse.model_validate(result.as_dict())


@router.get("/runs", response_model=IngestionRunListResponse)
async def list_ingestion_runs(
    service: MerchantIngestionService = Depends(_service),
) -> IngestionRunListResponse:
    rows = await service.list_runs()
    return IngestionRunListResponse(
        items=[
            IngestionRunSummary.model_validate(row, from_attributes=True)
            for row in rows
        ],
    )


@router.get("/runs/{run_id}", response_model=IngestionRunDetail)
async def get_ingestion_run(
    run_id: uuid.UUID,
    service: MerchantIngestionService = Depends(_service),
) -> IngestionRunDetail:
    row = await service.get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return IngestionRunDetail.model_validate(row, from_attributes=True)


@router.get("/status", response_model=MerchantDataStatusResponse)
async def merchant_data_status(
    db: AsyncSession = Depends(get_db),
    service: MerchantIngestionService = Depends(_service),
) -> MerchantDataStatusResponse:
    merchant = (await db.scalars(select(Merchant).limit(1))).first()
    products = int(
        await db.scalar(
            select(func.count()).select_from(Product).where(Product.is_active.is_(True))
        )
        or 0
    )
    variants = int(
        await db.scalar(
            select(func.count())
            .select_from(ProductVariant)
            .where(ProductVariant.is_active.is_(True))
        )
        or 0
    )
    runs = await service.list_runs(limit=1)
    last = (
        IngestionRunSummary.model_validate(runs[0], from_attributes=True)
        if runs
        else None
    )
    return MerchantDataStatusResponse(
        data_mode=merchant.data_mode if merchant is not None else "EMPTY",
        active_products=products,
        active_variants=variants,
        last_run=last,
    )

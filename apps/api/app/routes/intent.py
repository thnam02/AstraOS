"""Intent qualification HTTP routes. Decision logic lives in services."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.intent import (
    QualificationRunResponse,
    QualificationVariantDetail,
    QualifyRequest,
    QualifyResponse,
)
from app.services.qualification import IntentQualificationService

router = APIRouter(prefix="/intent", tags=["intent"])


def _service(db: AsyncSession = Depends(get_db)) -> IntentQualificationService:
    return IntentQualificationService(db)


@router.post("/qualify", response_model=QualifyResponse)
async def qualify_intent(
    payload: QualifyRequest,
    service: IntentQualificationService = Depends(_service),
) -> QualifyResponse:
    return await service.qualify(payload.intent, payload.parser_mode)


@router.get("/qualification/{run_id}", response_model=QualificationRunResponse)
async def get_qualification_run(
    run_id: uuid.UUID,
    outcome: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: IntentQualificationService = Depends(_service),
) -> QualificationRunResponse:
    detail = await service.get_run(run_id, outcome=outcome, limit=limit, offset=offset)
    if detail is None:
        raise HTTPException(status_code=404, detail="Qualification run not found")
    return detail


@router.get(
    "/qualification/{run_id}/variants/{variant_id}",
    response_model=QualificationVariantDetail,
)
async def get_qualification_variant(
    run_id: uuid.UUID,
    variant_id: uuid.UUID,
    service: IntentQualificationService = Depends(_service),
) -> QualificationVariantDetail:
    detail = await service.get_variant(run_id, variant_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Qualification variant not found")
    return detail

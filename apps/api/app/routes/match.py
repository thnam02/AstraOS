"""Semantic matching routes. Eligibility stays in the decision layer."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.match import MatchRequest, MatchResponse, MatchRunResponse
from app.services.matching import SemanticMatchingService

router = APIRouter(prefix="/match", tags=["match"])


def _service(db: AsyncSession = Depends(get_db)) -> SemanticMatchingService:
    return SemanticMatchingService(db)


@router.post("", response_model=MatchResponse)
async def match_intent(
    payload: MatchRequest,
    service: SemanticMatchingService = Depends(_service),
) -> MatchResponse:
    return await service.match(payload.intent, payload.parser_mode, payload.limit)


@router.get("/{run_id}", response_model=MatchRunResponse)
async def get_match_run(
    run_id: uuid.UUID,
    service: SemanticMatchingService = Depends(_service),
) -> MatchRunResponse:
    detail = await service.get_run(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Match run not found")
    return detail

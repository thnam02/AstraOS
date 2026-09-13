"""Optimisation HTTP routes. No negotiation."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.optimisation import OptimisationResponse, OptimiseRequest
from app.services.optimisation import OptimisationService

router = APIRouter(prefix="/optimisation", tags=["optimisation"])


def _service(db: AsyncSession = Depends(get_db)) -> OptimisationService:
    return OptimisationService(db)


@router.post("/run", response_model=OptimisationResponse)
async def run_optimisation(
    payload: OptimiseRequest,
    service: OptimisationService = Depends(_service),
) -> OptimisationResponse:
    try:
        return await service.run(
            payload.offer_run_id,
            buyer_profile=payload.buyer_profile,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=OptimisationResponse)
async def get_optimisation_run(
    run_id: uuid.UUID,
    service: OptimisationService = Depends(_service),
) -> OptimisationResponse:
    detail = await service.get_run(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Optimisation run not found")
    return detail


@router.get("/runs/{run_id}/frontier", response_model=OptimisationResponse)
async def get_frontier(
    run_id: uuid.UUID,
    service: OptimisationService = Depends(_service),
) -> OptimisationResponse:
    return await get_optimisation_run(run_id, service)


@router.get("/runs/{run_id}/counterfactuals", response_model=OptimisationResponse)
async def get_counterfactuals(
    run_id: uuid.UUID,
    service: OptimisationService = Depends(_service),
) -> OptimisationResponse:
    return await get_optimisation_run(run_id, service)


@router.post("/runs/{run_id}/reselect", response_model=OptimisationResponse)
async def reselect_optimisation(
    run_id: uuid.UUID,
    service: OptimisationService = Depends(_service),
) -> OptimisationResponse:
    try:
        return await service.reselect(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

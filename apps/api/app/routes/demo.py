"""Hackathon demo controls. These mutate live merchant state."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.transaction import (
    DemoDeliveryCapacityRequest,
    DemoInventoryRequest,
    DemoPolicyRequest,
    DemoStateResponse,
)
from app.services.demo_state import DemoStateError, DemoStateService

router = APIRouter(prefix="/demo", tags=["demo"])


def _service(db: AsyncSession = Depends(get_db)) -> DemoStateService:
    return DemoStateService(db)


@router.post("/inventory", response_model=DemoStateResponse)
async def set_inventory(
    payload: DemoInventoryRequest,
    service: DemoStateService = Depends(_service),
) -> DemoStateResponse:
    try:
        return await service.set_inventory(payload)
    except DemoStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/delivery-capacity", response_model=DemoStateResponse)
async def set_delivery_capacity(
    payload: DemoDeliveryCapacityRequest,
    service: DemoStateService = Depends(_service),
) -> DemoStateResponse:
    try:
        return await service.set_delivery_capacity(payload)
    except DemoStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/policy", response_model=DemoStateResponse)
async def set_demo_policy(
    payload: DemoPolicyRequest,
    service: DemoStateService = Depends(_service),
) -> DemoStateResponse:
    try:
        return await service.set_policy(payload)
    except DemoStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

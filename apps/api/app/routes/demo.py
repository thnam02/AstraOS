"""Hackathon demo controls. These mutate live merchant state."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.demo.scenarios import SCENARIOS
from app.schemas.objective import MerchantObjectiveUpdate
from app.schemas.transaction import (
    DemoDeliveryCapacityRequest,
    DemoInventoryRequest,
    DemoPolicyRequest,
    DemoStateResponse,
)
from app.services.demo_state import DemoStateError, DemoStateService
from app.services.objective import MerchantObjectiveService, ObjectiveValidationError

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


@router.get("/scenarios")
async def list_demo_scenarios() -> list[dict[str, str]]:
    return [
        {
            "id": item.id,
            "title": item.title,
            "buyer_intent": item.buyer_intent,
            "buyer_profile": item.buyer_profile,
            "expected_behavior": item.expected_behavior,
        }
        for item in SCENARIOS.values()
    ]


@router.post("/reset-state", response_model=DemoStateResponse)
async def reset_demo_state(
    service: DemoStateService = Depends(_service),
    db: AsyncSession = Depends(get_db),
) -> DemoStateResponse:
    """Restore seed policy guardrails and Balanced objective without remigrating."""
    try:
        await MerchantObjectiveService(db).update(
            MerchantObjectiveUpdate(mode="BALANCED")
        )
    except ObjectiveValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await service.set_policy(
        DemoPolicyRequest(minimum_margin_rate=0.15, maximum_discount_rate=0.10)
    )


@router.post("/policy", response_model=DemoStateResponse)
async def set_demo_policy(
    payload: DemoPolicyRequest,
    service: DemoStateService = Depends(_service),
) -> DemoStateResponse:
    try:
        return await service.set_policy(payload)
    except DemoStateError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

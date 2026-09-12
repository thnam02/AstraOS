"""Merchant policy inspection and update routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.merchant import MerchantPolicyResponse, MerchantPolicyUpdate
from app.services.policy import MerchantPolicyService, PolicyValidationError

router = APIRouter(prefix="/merchant", tags=["merchant"])


def _service(db: AsyncSession = Depends(get_db)) -> MerchantPolicyService:
    return MerchantPolicyService(db)


@router.get("/policy", response_model=MerchantPolicyResponse)
async def get_policy(
    service: MerchantPolicyService = Depends(_service),
) -> MerchantPolicyResponse:
    policy = await service.get_active()
    if policy is None:
        raise HTTPException(status_code=404, detail="Merchant policy not found")
    return policy


@router.patch("/policy", response_model=MerchantPolicyResponse)
async def patch_policy(
    payload: MerchantPolicyUpdate,
    service: MerchantPolicyService = Depends(_service),
) -> MerchantPolicyResponse:
    try:
        return await service.update_active(payload)
    except PolicyValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

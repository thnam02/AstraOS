"""Transaction inspection routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.transaction import TransactionDetailResponse
from app.services.transaction import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


@router.get("/{transaction_id}", response_model=TransactionDetailResponse)
async def get_transaction(
    transaction_id: uuid.UUID,
    service: TransactionService = Depends(_service),
) -> TransactionDetailResponse:
    detail = await service.get(transaction_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return detail

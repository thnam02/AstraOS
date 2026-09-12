"""Order snapshot routes. No fulfilment lifecycle."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.transaction import OrderView
from app.services.transaction import TransactionService

router = APIRouter(prefix="/orders", tags=["orders"])


def _service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)


@router.get("/by-number/{order_number}", response_model=OrderView)
async def get_order_by_number(
    order_number: str,
    service: TransactionService = Depends(_service),
) -> OrderView:
    detail = await service.get_order_by_number(order_number)
    if detail is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return detail


@router.get("/{order_id}", response_model=OrderView)
async def get_order(
    order_id: uuid.UUID,
    service: TransactionService = Depends(_service),
) -> OrderView:
    detail = await service.get_order(order_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return detail

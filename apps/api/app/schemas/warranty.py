"""Warranty option schemas."""

import uuid

from pydantic import BaseModel, ConfigDict


class WarrantyOptionResponse(BaseModel):
    """Warranty term as stored by the merchant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    months: int
    merchant_cost_cents: int
    customer_price_cents: int
    enabled: bool
    available: bool = True

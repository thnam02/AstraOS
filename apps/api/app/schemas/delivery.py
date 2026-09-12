"""Delivery option schemas."""

import uuid
from datetime import time

from pydantic import BaseModel, ConfigDict


class DeliveryOptionResponse(BaseModel):
    """Fulfilment method as stored by the merchant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    delivery_days: int
    merchant_cost_cents: int
    customer_charge_cents: int
    enabled: bool
    available: bool = True
    merchant_cost_override_cents: int | None = None
    customer_charge_override_cents: int | None = None
    cutoff_time: time | None = None

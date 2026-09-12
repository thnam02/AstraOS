"""Inventory response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InventoryResponse(BaseModel):
    """On-hand inventory for one variant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_id: uuid.UUID
    units_available: int
    units_reserved: int
    warehouse_code: str
    updated_at: datetime

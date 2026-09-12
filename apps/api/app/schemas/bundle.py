"""Bundle option schemas."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class BundleOptionResponse(BaseModel):
    """Accessory bundle as stored by the merchant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    merchant_cost_cents: int
    customer_price_cents: int
    enabled: bool
    attributes: dict[str, Any] | None
    available: bool = True

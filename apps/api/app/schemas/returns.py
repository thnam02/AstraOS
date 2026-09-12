"""Return policy schemas."""

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReturnPolicyResponse(BaseModel):
    """Return window as stored by the merchant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    return_window_days: int
    restocking_fee_rate: Decimal | None
    conditions: str | None
    merchant_expected_cost_cents: int | None
    enabled: bool
    available: bool = True

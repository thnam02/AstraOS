"""Merchant and policy schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MerchantResponse(BaseModel):
    """Single MVP merchant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    currency: str


class MerchantPolicyResponse(BaseModel):
    """Stored merchant policy. Not evaluated in Stage 1."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    is_active: bool
    minimum_margin_rate: float
    maximum_discount_rate: float
    delivery_subsidy_enabled: bool
    warranty_upgrade_enabled: bool
    bundle_enabled: bool
    flexible_returns_enabled: bool
    loyalty_enabled: bool
    maximum_delivery_subsidy_cents: int | None
    maximum_warranty_subsidy_cents: int | None
    maximum_bundle_subsidy_cents: int | None
    created_at: datetime
    updated_at: datetime


class MerchantPolicyUpdate(BaseModel):
    """Partial policy update. Does not trigger offer recomputation."""

    minimum_margin_rate: float | None = Field(default=None, ge=0, lt=1)
    maximum_discount_rate: float | None = Field(default=None, ge=0, le=1)
    delivery_subsidy_enabled: bool | None = None
    warranty_upgrade_enabled: bool | None = None
    bundle_enabled: bool | None = None
    flexible_returns_enabled: bool | None = None

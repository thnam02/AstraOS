"""Provenance response schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DataSourceResponse(BaseModel):
    """Origin of a stored fact."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source_type: str
    reference: str | None
    description: str | None


class AttributeEvidenceResponse(BaseModel):
    """One observed attribute value and its source."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_id: uuid.UUID | None
    attribute_name: str
    value: Any
    source: DataSourceResponse
    source_reference: str | None
    confidence: float | None
    verification_status: str
    observed_at: datetime
    expires_at: datetime | None
    is_stale: bool

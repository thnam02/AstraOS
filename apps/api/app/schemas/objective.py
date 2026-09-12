"""Merchant commercial objective HTTP schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.optimisation.objective import (
    MODE_BLURBS,
    MODE_LABELS,
    OBJECTIVE_VERSION,
    PRESETS,
)

ObjectiveMode = Literal["GROWTH", "BALANCED", "MARGIN", "CUSTOM"]


class MerchantObjectiveResponse(BaseModel):
    id: UUID | None = None
    merchant_id: UUID | None = None
    mode: ObjectiveMode
    buyer_weight: float
    merchant_weight: float
    version: str = OBJECTIVE_VERSION
    label: str
    blurb: str
    presets: dict[str, dict[str, float | str]]
    is_active: bool = True
    updated_at: datetime | None = None


class MerchantObjectiveUpdate(BaseModel):
    mode: ObjectiveMode
    buyer_weight: float | None = Field(default=None, ge=0, le=1)
    merchant_weight: float | None = Field(default=None, ge=0, le=1)


def preset_catalog() -> dict[str, dict[str, float | str]]:
    return {
        mode: {
            "buyer_weight": weights[0],
            "merchant_weight": weights[1],
            "label": MODE_LABELS[mode],
            "blurb": MODE_BLURBS[mode],
        }
        for mode, weights in PRESETS.items()
    }

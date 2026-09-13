"""Merchant commercial objective. Preference among policy-safe Pareto offers."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.decision.optimisation.models import DEFAULT_ALPHA

OBJECTIVE_VERSION = "merchant-objective-v1"
OBJECTIVE_MODES = ("GROWTH", "BALANCED", "MARGIN", "CUSTOM")
ObjectiveMode = Literal["GROWTH", "BALANCED", "MARGIN", "CUSTOM"]

PRESETS: dict[str, tuple[float, float]] = {
    "GROWTH": (0.70, 0.30),
    "BALANCED": (0.50, 0.50),
    "MARGIN": (0.30, 0.70),
}

MODE_LABELS = {
    "GROWTH": "Growth",
    "BALANCED": "Balanced",
    "MARGIN": "Margin",
    "CUSTOM": "Custom",
}

MODE_BLURBS = {
    "GROWTH": "Prioritise stronger buyer fit while remaining policy-safe.",
    "BALANCED": "Balance buyer fit and merchant contribution.",
    "MARGIN": "Prioritise contribution preservation among efficient offers.",
    "CUSTOM": "Merchant-specified weighting of buyer fit and contribution.",
}


class MerchantObjectiveConfig(BaseModel):
    """Soft merchant preference. Never overrides policy or Pareto dominance."""

    mode: ObjectiveMode = "BALANCED"
    buyer_weight: float = Field(default=DEFAULT_ALPHA, ge=0.0, le=1.0)
    merchant_weight: float = Field(default=DEFAULT_ALPHA, ge=0.0, le=1.0)
    version: str = OBJECTIVE_VERSION

    @field_validator("buyer_weight", "merchant_weight")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Objective weights must be finite.")
        return value

    @model_validator(mode="after")
    def _normalize(self) -> MerchantObjectiveConfig:
        if self.mode in PRESETS and self.mode != "CUSTOM":
            buyer, merchant = PRESETS[self.mode]
            self.buyer_weight = buyer
            self.merchant_weight = merchant
            return self
        total = self.buyer_weight + self.merchant_weight
        if total <= 0:
            raise ValueError("Objective weights must sum to a positive value.")
        self.buyer_weight = round(self.buyer_weight / total, 6)
        self.merchant_weight = round(1.0 - self.buyer_weight, 6)
        return self

    @property
    def alpha(self) -> float:
        """Buyer-utility weight in the existing normalized weighted sum."""
        return self.buyer_weight

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "buyer_weight": self.buyer_weight,
            "merchant_weight": self.merchant_weight,
            "version": self.version,
        }

    def label(self) -> str:
        return MODE_LABELS[self.mode]


def preset(mode: ObjectiveMode) -> MerchantObjectiveConfig:
    return MerchantObjectiveConfig(mode=mode)


def default_objective() -> MerchantObjectiveConfig:
    return preset("BALANCED")


def resolve_objective(
    *,
    mode: str | None = None,
    buyer_weight: float | None = None,
    merchant_weight: float | None = None,
) -> MerchantObjectiveConfig:
    chosen = (mode or "BALANCED").strip().upper()
    if chosen not in OBJECTIVE_MODES:
        raise ValueError(f"Unknown merchant objective: {mode}")
    if chosen == "CUSTOM":
        if buyer_weight is None or merchant_weight is None:
            raise ValueError(
                "CUSTOM objective requires buyer_weight and merchant_weight."
            )
        return MerchantObjectiveConfig(
            mode="CUSTOM",
            buyer_weight=buyer_weight,
            merchant_weight=merchant_weight,
        )
    return preset(chosen)  # type: ignore[arg-type]


def from_snapshot(payload: dict[str, Any] | None) -> MerchantObjectiveConfig:
    if not payload:
        return default_objective()
    return MerchantObjectiveConfig.model_validate(payload)


def explain_objective(objective: MerchantObjectiveConfig) -> str:
    name = objective.label()
    buyer = f"{objective.buyer_weight:.0%}"
    merchant = f"{objective.merchant_weight:.0%}"
    if objective.mode == "GROWTH":
        return (
            f"Selected from the Pareto frontier using the merchant's {name} "
            f"objective ({buyer} buyer fit / {merchant} contribution), which "
            "places greater weight on simulated buyer utility."
        )
    if objective.mode == "MARGIN":
        return (
            f"Selected from the same efficient frontier using the merchant's "
            f"{name} objective ({buyer} buyer fit / {merchant} contribution), "
            "which places greater weight on contribution preservation."
        )
    if objective.mode == "CUSTOM":
        return (
            f"Selected from the Pareto frontier using a custom merchant "
            f"objective ({buyer} buyer fit / {merchant} contribution)."
        )
    return (
        f"Selected from the Pareto frontier using the merchant's {name} "
        f"objective, which equally weights simulated buyer utility and "
        "contribution."
    )

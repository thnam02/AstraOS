"""Intermediate LLM extraction schema. Provider objects never enter the domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.decision.intent.models import ConstraintOperator, PreferenceDirection
from app.decision.intent.taxonomy import (
    ContextLabel,
    OutcomeLabel,
    TradeoffDimension,
    ValueField,
)


class LLMHardConstraint(BaseModel):
    field: str
    operator: ConstraintOperator
    value: Any
    unit: str | None = None
    source_phrase: str
    explicit_mandatory: bool = True


class LLMSoftPreference(BaseModel):
    field: str
    direction: PreferenceDirection = PreferenceDirection.MAXIMIZE
    importance: float = Field(default=0.6, ge=0, le=1)
    source_phrase: str


class LLMContext(BaseModel):
    label: ContextLabel
    importance: float = Field(default=0.7, ge=0, le=1)
    source_phrase: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class LLMOutcome(BaseModel):
    label: OutcomeLabel
    importance: float = Field(default=0.7, ge=0, le=1)
    source_phrase: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class LLMValue(BaseModel):
    field: ValueField
    direction: PreferenceDirection = PreferenceDirection.MAXIMIZE
    importance: float = Field(default=0.6, ge=0, le=1)
    source_phrase: str


class LLMTradeoff(BaseModel):
    preferred_dimension: TradeoffDimension
    over_dimension: TradeoffDimension
    strength: float = Field(default=0.7, ge=0, le=1)
    source_phrase: str


class LLMAmbiguity(BaseModel):
    source_phrase: str
    reason: str
    suggested_resolution: str | None = None
    appears_mandatory: bool = False


class LLMUnsupportedNeed(BaseModel):
    label: str
    source_phrase: str
    reason: str = "unsupported_semantic_need"


class LLMIntentExtraction(BaseModel):
    """Typed JSON the LLM must return. Normalized later into ShoppingIntent."""

    category: str | None = None
    hard_constraints: list[LLMHardConstraint] = Field(default_factory=list)
    soft_preferences: list[LLMSoftPreference] = Field(default_factory=list)
    context_items: list[LLMContext] = Field(default_factory=list)
    desired_outcomes: list[LLMOutcome] = Field(default_factory=list)
    values: list[LLMValue] = Field(default_factory=list)
    tradeoffs: list[LLMTradeoff] = Field(default_factory=list)
    ambiguities: list[LLMAmbiguity] = Field(default_factory=list)
    unsupported_semantic_needs: list[LLMUnsupportedNeed] = Field(default_factory=list)
    context_tags: list[str] = Field(default_factory=list)

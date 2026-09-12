"""Typed shopping-intent models. Eligibility is decided elsewhere."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.decision.intent.taxonomy import (
    ContextLabel,
    OutcomeLabel,
    TradeoffDimension,
    ValueField,
)


class ConstraintOperator(StrEnum):
    """Safe comparison operators. No expression evaluation."""

    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    IN = "IN"
    NOT_IN = "NOT_IN"


class ConstraintField(StrEnum):
    """Allow-listed hard-constraint fields for the headphone MVP."""

    CATEGORY = "category"
    BRAND = "brand"
    PRICE = "price"
    ANC = "anc"
    BATTERY_HOURS = "battery_hours"
    WEIGHT_G = "weight_g"
    FOLDABLE = "foldable"
    WIRELESS = "wireless"
    MICROPHONE = "microphone"
    DELIVERY_DAYS = "delivery_days"
    SAME_DAY_DELIVERY = "same_day_delivery"
    IN_STOCK = "in_stock"


class PreferenceField(StrEnum):
    """Soft-preference fields. Not used for eligibility."""

    COMFORT = "comfort"
    TRAVEL = "travel"
    RELIABILITY = "reliability"
    PRICE = "price"
    BATTERY = "battery"
    WEIGHT = "weight"
    DELIVERY = "delivery"
    WARRANTY = "warranty"


class PreferenceDirection(StrEnum):
    MAXIMIZE = "MAXIMIZE"
    MINIMIZE = "MINIMIZE"


class IntentStatus(StrEnum):
    READY = "READY"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNSUPPORTED = "UNSUPPORTED"


class HardConstraint(BaseModel):
    """A mandatory condition. Soft preferences must not live here."""

    id: str
    field: ConstraintField
    operator: ConstraintOperator
    value: Any
    unit: str | None = None
    source_phrase: str
    normalized_value: Any | None = None
    importance: Literal["MANDATORY"] = "MANDATORY"


class SoftPreference(BaseModel):
    """Interpretation metadata only. Never used to accept or reject a SKU."""

    id: str
    field: PreferenceField
    direction: PreferenceDirection
    importance: float = Field(ge=0, le=1)
    source_phrase: str


class IntentAmbiguity(BaseModel):
    """An unsupported or unclear phrase. Never silently dropped."""

    source_phrase: str
    reason: str
    suggested_resolution: str | None = None
    appears_mandatory: bool = False


class IntentContext(BaseModel):
    """Usage or lifestyle situation. Not a hard constraint."""

    label: ContextLabel
    importance: float = Field(default=0.7, ge=0, le=1)
    source_phrase: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class DesiredOutcome(BaseModel):
    """What the shopper is trying to achieve."""

    label: OutcomeLabel
    importance: float = Field(ge=0, le=1)
    source_phrase: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class ValuePreference(BaseModel):
    """Value only when merchant data can potentially support it."""

    field: ValueField
    direction: PreferenceDirection = PreferenceDirection.MAXIMIZE
    importance: float = Field(ge=0, le=1)
    source_phrase: str


class TradeoffPreference(BaseModel):
    """Relative importance between two competing goals."""

    preferred_dimension: TradeoffDimension
    over_dimension: TradeoffDimension
    strength: float = Field(default=0.7, ge=0, le=1)
    source_phrase: str


class UnsupportedSemanticNeed(BaseModel):
    """A semantic request the catalogue cannot represent."""

    label: str
    source_phrase: str
    reason: str = "unsupported_semantic_need"


class ParserMetadata(BaseModel):
    """Technical parser provenance. Never contains secrets or chain-of-thought."""

    parser_requested: str
    parser_used: str
    fallback_used: bool = False
    fallback_reason: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    repair_count: int = 0
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ShoppingIntent(BaseModel):
    """Structured buyer request produced by an IntentParser."""

    raw_text: str
    category: str | None = None
    hard_constraints: list[HardConstraint] = Field(default_factory=list)
    soft_preferences: list[SoftPreference] = Field(default_factory=list)
    context_tags: list[str] = Field(default_factory=list)
    context_items: list[IntentContext] = Field(default_factory=list)
    desired_outcomes: list[DesiredOutcome] = Field(default_factory=list)
    values: list[ValuePreference] = Field(default_factory=list)
    tradeoffs: list[TradeoffPreference] = Field(default_factory=list)
    unsupported_semantic_needs: list[UnsupportedSemanticNeed] = Field(
        default_factory=list
    )
    ambiguities: list[IntentAmbiguity] = Field(default_factory=list)
    parser_type: str
    parser_version: str
    status: IntentStatus = IntentStatus.READY
    parser_metadata: ParserMetadata | None = None


SUPPORTED_CONSTRAINT_FIELDS = {item.value for item in ConstraintField}
SUPPORTED_OPERATORS = {item.value for item in ConstraintOperator}
PARSER_VERSION_RULE = "rule_based.v2"
PARSER_VERSION_LLM = "llm.v2"
PROMPT_VERSION = "intent-parser-v2"
EXTRACTION_SCHEMA_VERSION = "llm-extraction.v1"

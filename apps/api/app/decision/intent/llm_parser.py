"""Structured LLM parser. Interprets language; never decides eligibility."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.config import settings
from app.decision.intent.exceptions import (
    LLMParserUnavailable,
    UnsupportedIntentFieldError,
)
from app.decision.intent.extraction import LLMIntentExtraction
from app.decision.intent.faithfulness import apply_faithfulness
from app.decision.intent.models import (
    EXTRACTION_SCHEMA_VERSION,
    PARSER_VERSION_LLM,
    PROMPT_VERSION,
    SUPPORTED_CONSTRAINT_FIELDS,
    SUPPORTED_OPERATORS,
    ConstraintField,
    ConstraintOperator,
    DesiredOutcome,
    HardConstraint,
    IntentAmbiguity,
    IntentContext,
    ParserMetadata,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
    TradeoffPreference,
    UnsupportedSemanticNeed,
    ValuePreference,
)
from app.decision.intent.prompts import SYSTEM_PROMPT_V2, repair_prompt
from app.decision.intent.provider import (
    StructuredLLMProvider,
    optional_live_client,
)
from app.decision.intent.taxonomy import (
    CANONICAL_CONTEXTS,
    CANONICAL_OUTCOMES,
    CANONICAL_TRADEOFFS,
    CANONICAL_VALUES,
    ContextLabel,
    OutcomeLabel,
    TradeoffDimension,
    ValueField,
)


class LLMIntentParser:
    """Schema-constrained parser with one structured repair attempt."""

    parser_type = "llm"

    def __init__(self, client: StructuredLLMProvider | None = None) -> None:
        self.client = client if client is not None else optional_live_client()
        self.repair_count = 0
        self.last_usage: dict[str, int | str | None] = {}

    def available(self) -> bool:
        return self.client is not None

    async def parse(self, text: str) -> ShoppingIntent:
        if not self.available() or self.client is None:
            raise LLMParserUnavailable(
                "LLM parser requested but no client or credentials are configured."
            )
        self.repair_count = 0
        last_error: Exception | None = None
        attempts = 1 + max(0, settings.llm_max_retries)
        user = text
        for attempt in range(attempts):
            try:
                payload = await self.client.complete_json(
                    system=SYSTEM_PROMPT_V2,
                    user=user,
                    schema=LLMIntentExtraction.model_json_schema(),
                )
                self._capture_usage()
                intent = self._to_intent(text, payload)
                return apply_faithfulness(intent)
            except (
                UnsupportedIntentFieldError,
                ValidationError,
                ValueError,
                LLMParserUnavailable,
            ) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                self.repair_count += 1
                user = f"{text}\n\n{repair_prompt(_safe_error(exc))}"
        raise LLMParserUnavailable(
            f"LLM extraction failed after repair: {_safe_error(last_error)}"
        )

    def metadata_fields(self) -> dict[str, Any]:
        usage = self.last_usage
        provider = getattr(self.client, "provider_name", None)
        model = getattr(self.client, "model_name", None) or usage.get("model")
        return {
            "provider": provider,
            "model": model,
            "prompt_version": PROMPT_VERSION,
            "schema_version": EXTRACTION_SCHEMA_VERSION,
            "repair_count": self.repair_count,
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    def _capture_usage(self) -> None:
        usage = getattr(self.client, "last_usage", None)
        if usage is None:
            self.last_usage = {}
            return
        self.last_usage = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "model": getattr(usage, "model", None),
        }

    def _to_intent(self, raw_text: str, payload: dict[str, Any]) -> ShoppingIntent:
        extracted = LLMIntentExtraction.model_validate(payload)
        constraints: list[HardConstraint] = []
        ambiguities: list[IntentAmbiguity] = [
            IntentAmbiguity(
                source_phrase=row.source_phrase,
                reason=row.reason,
                suggested_resolution=row.suggested_resolution,
                appears_mandatory=row.appears_mandatory,
            )
            for row in extracted.ambiguities
        ]
        for index, constraint in enumerate(extracted.hard_constraints):
            field = constraint.field
            if field not in SUPPORTED_CONSTRAINT_FIELDS:
                raise UnsupportedIntentFieldError(f"Unsupported field: {field}")
            if constraint.operator.value not in SUPPORTED_OPERATORS:
                raise UnsupportedIntentFieldError(
                    f"Unsupported operator: {constraint.operator}"
                )
            if not constraint.explicit_mandatory:
                ambiguities.append(
                    IntentAmbiguity(
                        source_phrase=constraint.source_phrase,
                        reason="not_explicitly_mandatory",
                        suggested_resolution=(
                            "Recorded as ambiguity, not a hard constraint."
                        ),
                        appears_mandatory=False,
                    )
                )
                continue
            constraints.append(
                HardConstraint(
                    id=f"c_{index + 1}",
                    field=ConstraintField(field),
                    operator=ConstraintOperator(constraint.operator),
                    value=constraint.value,
                    unit=constraint.unit,
                    source_phrase=constraint.source_phrase or raw_text,
                    normalized_value=constraint.value,
                )
            )
        preferences: list[SoftPreference] = []
        for index, preference in enumerate(extracted.soft_preferences):
            if preference.field not in {item.value for item in PreferenceField}:
                continue
            preferences.append(
                SoftPreference(
                    id=f"p_{index + 1}",
                    field=PreferenceField(preference.field),
                    direction=preference.direction,
                    importance=preference.importance,
                    source_phrase=preference.source_phrase or raw_text,
                )
            )
        context_items: list[IntentContext] = []
        for context in extracted.context_items:
            if context.label.value not in CANONICAL_CONTEXTS:
                continue
            context_items.append(
                IntentContext(
                    label=ContextLabel(context.label),
                    importance=context.importance,
                    source_phrase=context.source_phrase or raw_text,
                    confidence=context.confidence,
                )
            )
        outcomes = [
            DesiredOutcome(
                label=OutcomeLabel(outcome.label),
                importance=outcome.importance,
                source_phrase=outcome.source_phrase or raw_text,
                confidence=outcome.confidence,
            )
            for outcome in extracted.desired_outcomes
            if outcome.label.value in CANONICAL_OUTCOMES
        ]
        values = [
            ValuePreference(
                field=ValueField(value.field),
                direction=value.direction,
                importance=value.importance,
                source_phrase=value.source_phrase or raw_text,
            )
            for value in extracted.values
            if value.field.value in CANONICAL_VALUES
        ]
        tradeoffs = [
            TradeoffPreference(
                preferred_dimension=TradeoffDimension(tradeoff.preferred_dimension),
                over_dimension=TradeoffDimension(tradeoff.over_dimension),
                strength=tradeoff.strength,
                source_phrase=tradeoff.source_phrase or raw_text,
            )
            for tradeoff in extracted.tradeoffs
            if tradeoff.preferred_dimension.value in CANONICAL_TRADEOFFS
            and tradeoff.over_dimension.value in CANONICAL_TRADEOFFS
        ]
        unsupported = [
            UnsupportedSemanticNeed(
                label=need.label,
                source_phrase=need.source_phrase,
                reason=need.reason,
            )
            for need in extracted.unsupported_semantic_needs
        ]
        tags = [str(tag) for tag in extracted.context_tags]
        for item in context_items:
            if item.label.value not in tags:
                tags.append(item.label.value)
        return ShoppingIntent(
            raw_text=raw_text,
            category=extracted.category,
            hard_constraints=constraints,
            soft_preferences=preferences,
            context_tags=tags,
            context_items=context_items,
            desired_outcomes=outcomes,
            values=values,
            tradeoffs=tradeoffs,
            unsupported_semantic_needs=unsupported,
            ambiguities=ambiguities,
            parser_type=self.parser_type,
            parser_version=PARSER_VERSION_LLM,
            parser_metadata=ParserMetadata(
                parser_requested="llm",
                parser_used="llm",
                provider=getattr(self.client, "provider_name", None),
                model=getattr(self.client, "model_name", None),
                prompt_version=PROMPT_VERSION,
                schema_version=EXTRACTION_SCHEMA_VERSION,
                repair_count=self.repair_count,
            ),
        )


def _safe_error(exc: Exception | None) -> str:
    if exc is None:
        return "unknown_validation_error"
    text = str(exc)
    lowered = text.lower()
    if "api key" in lowered or "bearer" in lowered or "sk-" in lowered:
        return "provider_error"
    return text[:240]


# Backwards-compatible aliases for existing tests.
StructuredLLMClient = StructuredLLMProvider
_optional_live_client = optional_live_client

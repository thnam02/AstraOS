"""Optional structured LLM parser. Never decides eligibility."""

from __future__ import annotations

import json
from typing import Any, Protocol

from app.config import settings
from app.decision.intent.exceptions import (
    LLMParserUnavailable,
    UnsupportedIntentFieldError,
)
from app.decision.intent.models import (
    PARSER_VERSION_LLM,
    SUPPORTED_CONSTRAINT_FIELDS,
    SUPPORTED_OPERATORS,
    ConstraintField,
    ConstraintOperator,
    DesiredOutcome,
    HardConstraint,
    IntentAmbiguity,
    IntentContext,
    PreferenceDirection,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
    TradeoffPreference,
    UnsupportedSemanticNeed,
    ValuePreference,
)
from app.decision.intent.rule_based_parser import RuleBasedIntentParser
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

SYSTEM_PROMPT = """You extract a structured shopping intent for AstraOS.
Return JSON only. Use only allow-listed fields, operators, and canonical labels.
Do not decide product eligibility, prices, discounts, or merchant policy.
Do not invent product facts.
Preserve source_phrase from the buyer's text.
Populate hard_constraints, soft_preferences, context_items, desired_outcomes,
values, and tradeoffs when the text supports them.
If a mandatory requirement has no supported field, record it as an ambiguity
with reason unsupported_attribute and appears_mandatory true.
If a semantic need cannot be represented by merchant data, record
unsupported_semantic_needs rather than inventing a score.
"""


class StructuredLLMClient(Protocol):
    """Provider-agnostic structured completion."""

    async def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


def _configured_api_key() -> str:
    return settings.llm_api_key or settings.openai_api_key


class OpenAICompatibleJSONClient:
    """Optional OpenAI-compatible structured JSON client. Tests inject fakes."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:
            raise LLMParserUnavailable("httpx is required for the LLM parser.") from exc

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output was not a JSON object.")
        _ = schema
        return parsed


class LLMIntentParser:
    """Schema-constrained parser with a single validation retry."""

    parser_type = "llm"

    def __init__(self, client: StructuredLLMClient | None = None) -> None:
        self.client = client or _optional_live_client()

    def available(self) -> bool:
        return self.client is not None

    async def parse(self, text: str) -> ShoppingIntent:
        if not self.available():
            raise LLMParserUnavailable(
                "LLM parser requested but no client or credentials are configured."
            )
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                payload = await self._complete(text)
                return self._validate(text, payload)
            except (UnsupportedIntentFieldError, ValueError) as exc:
                last_error = exc
        fallback = await RuleBasedIntentParser().parse(text)
        if last_error is not None:
            fallback.ambiguities.append(
                IntentAmbiguity(
                    source_phrase=text[:120],
                    reason="llm_validation_failed",
                    suggested_resolution=str(last_error),
                    appears_mandatory=False,
                )
            )
        return fallback

    async def _complete(self, text: str) -> dict[str, Any]:
        if self.client is None:
            raise LLMParserUnavailable("No structured LLM client bound.")
        return await self.client.complete_json(
            system=SYSTEM_PROMPT,
            user=text,
            schema=ShoppingIntent.model_json_schema(),
        )

    def _validate(self, raw_text: str, payload: dict[str, Any]) -> ShoppingIntent:
        constraints: list[HardConstraint] = []
        for index, row in enumerate(payload.get("hard_constraints") or []):
            field = str(row.get("field", ""))
            operator = str(row.get("operator", ""))
            if field not in SUPPORTED_CONSTRAINT_FIELDS:
                raise UnsupportedIntentFieldError(f"Unsupported field: {field}")
            if operator not in SUPPORTED_OPERATORS:
                raise UnsupportedIntentFieldError(f"Unsupported operator: {operator}")
            constraints.append(
                HardConstraint(
                    id=str(row.get("id") or f"c_{index + 1}"),
                    field=ConstraintField(field),
                    operator=ConstraintOperator(operator),
                    value=row.get("value"),
                    unit=row.get("unit"),
                    source_phrase=str(row.get("source_phrase") or raw_text),
                    normalized_value=row.get("normalized_value"),
                )
            )
        preferences: list[SoftPreference] = []
        for index, row in enumerate(payload.get("soft_preferences") or []):
            field = str(row.get("field", ""))
            if field not in {item.value for item in PreferenceField}:
                continue
            preferences.append(
                SoftPreference(
                    id=str(row.get("id") or f"p_{index + 1}"),
                    field=PreferenceField(field),
                    direction=PreferenceDirection(
                        str(row.get("direction", "MAXIMIZE"))
                    ),
                    importance=float(row.get("importance", 0.5)),
                    source_phrase=str(row.get("source_phrase") or raw_text),
                )
            )
        ambiguities = [
            IntentAmbiguity.model_validate(row)
            for row in payload.get("ambiguities") or []
        ]
        context_items: list[IntentContext] = []
        for row in payload.get("context_items") or []:
            label = str(row.get("label", ""))
            if label not in CANONICAL_CONTEXTS:
                continue
            context_items.append(
                IntentContext(
                    label=ContextLabel(label),
                    importance=float(row.get("importance", 0.7)),
                    source_phrase=str(row.get("source_phrase") or raw_text),
                    confidence=row.get("confidence"),
                )
            )
        outcomes: list[DesiredOutcome] = []
        for row in payload.get("desired_outcomes") or []:
            label = str(row.get("label", ""))
            if label not in CANONICAL_OUTCOMES:
                continue
            outcomes.append(
                DesiredOutcome(
                    label=OutcomeLabel(label),
                    importance=float(row.get("importance", 0.7)),
                    source_phrase=str(row.get("source_phrase") or raw_text),
                    confidence=row.get("confidence"),
                )
            )
        values: list[ValuePreference] = []
        for row in payload.get("values") or []:
            field = str(row.get("field", ""))
            if field not in CANONICAL_VALUES:
                continue
            values.append(
                ValuePreference(
                    field=ValueField(field),
                    direction=PreferenceDirection(
                        str(row.get("direction", "MAXIMIZE"))
                    ),
                    importance=float(row.get("importance", 0.6)),
                    source_phrase=str(row.get("source_phrase") or raw_text),
                )
            )
        tradeoffs: list[TradeoffPreference] = []
        for row in payload.get("tradeoffs") or []:
            preferred = str(row.get("preferred_dimension", ""))
            over = str(row.get("over_dimension", ""))
            if preferred not in CANONICAL_TRADEOFFS or over not in CANONICAL_TRADEOFFS:
                continue
            tradeoffs.append(
                TradeoffPreference(
                    preferred_dimension=TradeoffDimension(preferred),
                    over_dimension=TradeoffDimension(over),
                    strength=float(row.get("strength", 0.7)),
                    source_phrase=str(row.get("source_phrase") or raw_text),
                )
            )
        unsupported = [
            UnsupportedSemanticNeed.model_validate(row)
            for row in payload.get("unsupported_semantic_needs") or []
        ]
        tags = [str(tag) for tag in payload.get("context_tags") or []]
        for item in context_items:
            if item.label.value not in tags:
                tags.append(item.label.value)
        category = payload.get("category")
        return ShoppingIntent(
            raw_text=raw_text,
            category=str(category) if category else None,
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
        )


def _optional_live_client() -> StructuredLLMClient | None:
    key = _configured_api_key()
    if not key:
        return None
    return OpenAICompatibleJSONClient(
        api_key=key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
    )

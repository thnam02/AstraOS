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
    HardConstraint,
    IntentAmbiguity,
    PreferenceDirection,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
)
from app.decision.intent.rule_based_parser import RuleBasedIntentParser

SYSTEM_PROMPT = """You extract a structured shopping intent for AstraOS.
Return JSON only. Use only allow-listed fields and operators.
Do not decide product eligibility, prices, discounts, or merchant policy.
Preserve source_phrase from the buyer's text.
If a mandatory requirement has no supported field, record it as an ambiguity
with reason unsupported_attribute and appears_mandatory true.
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
        category = payload.get("category")
        return ShoppingIntent(
            raw_text=raw_text,
            category=str(category) if category else None,
            hard_constraints=constraints,
            soft_preferences=preferences,
            context_tags=[str(tag) for tag in payload.get("context_tags") or []],
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

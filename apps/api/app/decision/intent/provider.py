"""Narrow structured-LLM provider. Domain code never imports SDK types."""

from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.config import settings
from app.decision.intent.exceptions import LLMParserUnavailable


class LLMUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    model: str | None = None


class LLMCompletion(BaseModel):
    payload: dict[str, Any]
    usage: LLMUsage = Field(default_factory=LLMUsage)


class StructuredLLMProvider(Protocol):
    """Provider-agnostic structured completion."""

    provider_name: str
    model_name: str

    async def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


class OpenAICompatibleJSONClient:
    """OpenAI-compatible JSON object client. Tests inject fakes."""

    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self.last_usage = LLMUsage(model=model)

    async def complete_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as exc:
            raise LLMParserUnavailable("httpx is required for the LLM parser.") from exc

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        _ = schema
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                raise LLMParserUnavailable("LLM request timed out.") from exc
            except httpx.RequestError as exc:
                raise LLMParserUnavailable("LLM provider unavailable.") from exc
        if response.status_code in {401, 403}:
            raise LLMParserUnavailable("LLM authentication failed.")
        if response.status_code >= 400:
            raise LLMParserUnavailable("LLM provider returned an error.")
        body = response.json()
        usage = body.get("usage") or {}
        self.last_usage = LLMUsage(
            input_tokens=_as_int(usage.get("prompt_tokens")),
            output_tokens=_as_int(usage.get("completion_tokens")),
            total_tokens=_as_int(usage.get("total_tokens")),
            model=body.get("model") or self.model,
        )
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMParserUnavailable("LLM response was empty.") from exc
        if not content:
            raise LLMParserUnavailable("LLM response was empty.")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM output was not valid JSON.") from exc
        if not isinstance(parsed, dict):
            raise ValueError("LLM output was not a JSON object.")
        return parsed


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def configured_api_key() -> str:
    return settings.llm_api_key or settings.openai_api_key


def optional_live_client() -> OpenAICompatibleJSONClient | None:
    key = configured_api_key()
    if not key:
        return None
    return OpenAICompatibleJSONClient(
        api_key=key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def provider_configured() -> bool:
    return bool(configured_api_key())

"""Independent OpenAI-compatible client. Not the merchant intent provider."""

from __future__ import annotations

from typing import Any

import httpx

from buyer_agent.errors import BuyerAgentError


class BuyerLLMClient:
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.last_usage: dict[str, int] = {}

    def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise BuyerAgentError(
                "LLM_UNAVAILABLE",
                "Buyer LLM request failed.",
                retryable=True,
            ) from exc
        if response.status_code >= 400:
            raise BuyerAgentError(
                "LLM_UNAVAILABLE",
                f"Buyer LLM HTTP {response.status_code}.",
                retryable=response.status_code >= 500,
            )
        body = response.json()
        choice = (body.get("choices") or [{}])[0]
        content = ((choice.get("message") or {}).get("content")) or "{}"
        usage = body.get("usage") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        import json

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise BuyerAgentError(
                "LLM_INVALID_JSON",
                "Buyer LLM did not return JSON.",
            ) from exc
        if not isinstance(parsed, dict):
            raise BuyerAgentError(
                "LLM_INVALID_JSON",
                "Buyer LLM JSON was not an object.",
            )
        return parsed

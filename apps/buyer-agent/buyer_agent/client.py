"""HTTP client for the public AstraOS agent protocol only."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import httpx

from buyer_agent.config import BuyerAgentSettings
from buyer_agent.errors import BuyerAgentError, parse_error_body
from buyer_agent.version import BUYER_AGENT_VERSION

SAFE_GET_RETRIES = 2


class AstraOSAgentClient:
    """External machine client. Never imports AstraOS internals."""

    def __init__(
        self,
        settings: BuyerAgentSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.base = settings.astraos_agent_base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base,
            timeout=settings.buyer_agent_timeout,
            transport=transport,
        )
        self.last_latencies_ms: dict[str, float] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AstraOSAgentClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def capabilities(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/agent/capabilities", retry=True)

    def request_offer(
        self,
        intent: str,
        *,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/agent/offers/request",
            json={
                "request_id": request_id or str(uuid4()),
                "buyer_agent_id": (
                    f"{self.settings.buyer_agent_id}/{BUYER_AGENT_VERSION}"
                ),
                "natural_language_intent": intent,
                "metadata": metadata or {},
            },
        )

    def inspect_offer(self, proposal_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/api/v1/agent/offers/{proposal_id}", retry=True
        )

    def counter_offer(
        self,
        session_id: str,
        *,
        message: str | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"session_id": session_id}
        if message:
            payload["message"] = message
        if constraints:
            payload["constraints"] = constraints
        return self._request("POST", "/api/v1/agent/offers/counter", json=payload)

    def accept_offer(
        self,
        session_id: str,
        proposal_id: str,
        idempotency_key: str,
        *,
        quantity: int = 1,
    ) -> dict[str, Any]:
        return self._mutating_with_idempotent_retry(
            "POST",
            "/api/v1/agent/offers/accept",
            json={
                "session_id": session_id,
                "proposal_id": proposal_id,
                "idempotency_key": idempotency_key,
                "quantity": quantity,
            },
        )

    def get_order(self, ref: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/agent/orders/{ref}", retry=True)

    def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/api/v1/agent/transactions/{transaction_id}", retry=True
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        retry: bool = False,
    ) -> dict[str, Any]:
        attempts = SAFE_GET_RETRIES + 1 if retry else 1
        last_error: BuyerAgentError | None = None
        for attempt in range(attempts):
            started = time.perf_counter()
            try:
                response = self._client.request(method, path, json=json)
            except httpx.TimeoutException as exc:
                last_error = BuyerAgentError(
                    "TIMEOUT",
                    "AstraOS request timed out.",
                    retryable=True,
                )
                if attempt + 1 == attempts:
                    raise last_error from exc
                continue
            except httpx.ConnectError as exc:
                last_error = BuyerAgentError(
                    "CONNECTION_REFUSED",
                    "AstraOS agent API is unreachable.",
                    retryable=True,
                )
                if attempt + 1 == attempts:
                    raise last_error from exc
                continue
            self.last_latencies_ms[f"{method} {path}"] = (
                time.perf_counter() - started
            ) * 1000
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = {"machine_message": response.text}
            if response.status_code >= 400:
                error = parse_error_body(response.status_code, body)
                if error.retryable and attempt + 1 < attempts:
                    last_error = error
                    continue
                raise error
            if not isinstance(body, dict):
                raise BuyerAgentError(
                    "MALFORMED_RESPONSE",
                    "Public response was not a JSON object.",
                )
            return body
        assert last_error is not None
        raise last_error

    def _mutating_with_idempotent_retry(
        self, method: str, path: str, *, json: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            return self._request(method, path, json=json)
        except BuyerAgentError as exc:
            if exc.retryable or exc.code == "TIMEOUT":
                return self._request(method, path, json=json)
            raise

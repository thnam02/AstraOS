"""Machine-readable Buyer Agent / public protocol errors."""

from __future__ import annotations

from typing import Any


class BuyerAgentError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        http_status: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.http_status = http_status
        self.payload = payload or {}

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


def parse_error_body(status: int, body: Any) -> BuyerAgentError:
    payload: dict[str, Any]
    if isinstance(body, dict) and isinstance(body.get("detail"), dict):
        payload = body["detail"]
    elif isinstance(body, dict):
        payload = body
    else:
        payload = {"machine_message": str(body)}
    code = str(
        payload.get("error_code")
        or payload.get("code")
        or ("SERVER_ERROR" if status >= 500 else "PROTOCOL_ERROR")
    )
    message = str(
        payload.get("machine_message") or payload.get("message") or "Request failed"
    )
    retryable = bool(payload.get("retryable", status >= 500 or status == 429))
    return BuyerAgentError(
        code, message, retryable=retryable, http_status=status, payload=payload
    )

"""Minimal MCP stdio adapter. Calls the public REST agent interface only.

This process contains no pricing, eligibility, matching, Pareto, or policy
logic. If the MCP client is unavailable, use POST /api/v1/agent/* instead.
"""

from __future__ import annotations

import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import settings

TOOLS = [
    {
        "name": "astraos_request_offer",
        "description": "Submit shopping intent and receive a merchant proposal.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "buyer_profile": {"type": "string"},
            },
            "required": ["intent"],
        },
    },
    {
        "name": "astraos_inspect_offer",
        "description": "Inspect an existing merchant proposal.",
        "inputSchema": {
            "type": "object",
            "properties": {"proposal_id": {"type": "string"}},
            "required": ["proposal_id"],
        },
    },
    {
        "name": "astraos_counter_offer",
        "description": "Send a natural-language or structured counter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "astraos_accept_offer",
        "description": "Accept a proposal. Client prices are ignored.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "proposal_id": {"type": "string"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["session_id", "proposal_id", "idempotency_key"],
        },
    },
    {
        "name": "astraos_get_order",
        "description": "Fetch a machine-readable order confirmation.",
        "inputSchema": {
            "type": "object",
            "properties": {"ref": {"type": "string"}},
            "required": ["ref"],
        },
    },
]


def _base() -> str:
    return f"http://127.0.0.1:{settings.api_port}"


def _http(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        f"{_base()}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"error": payload, "status": exc.code}
    except URLError as exc:
        return {
            "error_code": "ADAPTER_UNAVAILABLE",
            "machine_message": "REST agent interface is unreachable.",
            "human_debug_message": str(exc),
            "allowed_next_actions": ["RETRY"],
        }


def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "astraos_request_offer":
        return _http(
            "POST",
            "/api/v1/agent/offers/request",
            {
                "natural_language_intent": arguments["intent"],
                "buyer_profile": arguments.get("buyer_profile", "INTENT_ADAPTED"),
            },
        )
    if name == "astraos_inspect_offer":
        return _http("GET", f"/api/v1/agent/offers/{arguments['proposal_id']}")
    if name == "astraos_counter_offer":
        return _http("POST", "/api/v1/agent/offers/counter", arguments)
    if name == "astraos_accept_offer":
        return _http("POST", "/api/v1/agent/offers/accept", arguments)
    if name == "astraos_get_order":
        return _http("GET", f"/api/v1/agent/orders/{arguments['ref']}")
    return {"error_code": "UNKNOWN_TOOL", "machine_message": name}


def _reply(message_id: Any, result: Any) -> None:
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message_id, "result": result}))
    sys.stdout.write("\n")
    sys.stdout.flush()


def main() -> None:
    """MCP stdio loop. Requires the AstraOS API to be running."""
    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        message = json.loads(line)
        method = message.get("method")
        message_id = message.get("id")
        if method == "initialize":
            _reply(
                message_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "astraos", "version": "1.0"},
                },
            )
        elif method == "tools/list":
            _reply(message_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = message.get("params") or {}
            _reply(
                message_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                _call_tool(
                                    params.get("name", ""),
                                    params.get("arguments") or {},
                                )
                            ),
                        }
                    ]
                },
            )
        elif method == "notifications/initialized":
            continue
        elif message_id is not None:
            _reply(message_id, {"ok": True})


if __name__ == "__main__":
    main()

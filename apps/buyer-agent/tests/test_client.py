from uuid import uuid4

import httpx
import pytest
from buyer_agent.client import AstraOSAgentClient
from buyer_agent.config import BuyerAgentSettings
from buyer_agent.errors import BuyerAgentError


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/capabilities"):
        return httpx.Response(
            200,
            json={
                "protocol_name": "astraos-agent",
                "version": "1.0",
                "operations": ["request_offer", "inspect_offer"],
                "supported": [],
                "not_supported": [],
                "protocol": ["REST"],
                "disclaimer": "x",
            },
        )
    if path.endswith("/offers/request"):
        return httpx.Response(
            200,
            json={
                "request_id": str(uuid4()),
                "status": "PROPOSED",
                "negotiation_session_id": str(uuid4()),
                "proposal": {
                    "proposal_id": str(uuid4()),
                    "product": {"name": "Demo", "sku": "DEM-1", "brand": "Demo"},
                    "pricing": {"total_price_cents": 10000, "currency": "AUD"},
                    "total": {"amount_cents": 10000, "currency": "AUD"},
                    "delivery": {"days": 0, "name": "Same Day"},
                },
                "allowed_actions": ["ACCEPT", "COUNTER"],
                "proof": [],
            },
        )
    return httpx.Response(
        404,
        json={"detail": {"error_code": "NOT_FOUND", "machine_message": "no"}},
    )


def test_capabilities_and_request() -> None:
    settings = BuyerAgentSettings(astraos_agent_base_url="http://astraos.test")
    transport = httpx.MockTransport(_handler)
    with AstraOSAgentClient(settings, transport=transport) as client:
        caps = client.capabilities()
        assert caps["protocol_name"] == "astraos-agent"
        offered = client.request_offer("need headphones today please")
        assert offered["status"] == "PROPOSED"


def test_timeout_is_machine_readable() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    settings = BuyerAgentSettings(astraos_agent_base_url="http://astraos.test")
    with AstraOSAgentClient(
        settings, transport=httpx.MockTransport(boom)
    ) as client:
        with pytest.raises(BuyerAgentError) as exc:
            client.capabilities()
        assert exc.value.code == "TIMEOUT"
        assert exc.value.retryable is True


def test_connection_refused_is_machine_readable() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    settings = BuyerAgentSettings(astraos_agent_base_url="http://astraos.test")
    with AstraOSAgentClient(
        settings, transport=httpx.MockTransport(boom)
    ) as client:
        with pytest.raises(BuyerAgentError) as exc:
            client.capabilities()
        assert exc.value.code == "CONNECTION_REFUSED"
        assert exc.value.retryable is True


def test_malformed_object_response() -> None:
    def bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"])

    settings = BuyerAgentSettings(astraos_agent_base_url="http://astraos.test")
    with AstraOSAgentClient(settings, transport=httpx.MockTransport(bad)) as client:
        with pytest.raises(BuyerAgentError) as exc:
            client.capabilities()
        assert exc.value.code == "MALFORMED_RESPONSE"


def test_malformed_error() -> None:
    def bad(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="nope")

    settings = BuyerAgentSettings(astraos_agent_base_url="http://astraos.test")
    with AstraOSAgentClient(settings, transport=httpx.MockTransport(bad)) as client:
        with pytest.raises(BuyerAgentError) as exc:
            client.capabilities()
        assert exc.value.retryable is True

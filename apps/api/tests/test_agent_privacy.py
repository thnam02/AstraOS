"""Public /agent/* must not leak merchant-private economics."""

from buyer_agent.proposal import contains_private_keys
from fastapi.testclient import TestClient

from tests.agent_client import ExternalAgentClient


def test_public_offer_hides_margin(client: TestClient) -> None:
    offered = ExternalAgentClient(client).request_offer(
        "wireless ANC headphones under A$350 delivered today for a flight"
    )
    assert offered.get("proposal")
    leaks = contains_private_keys(offered)
    assert leaks == []
    pricing = (offered["proposal"].get("pricing") or {})
    assert "contribution_margin_cents" not in pricing
    assert set(pricing).issubset(
        {"product_price_cents", "total_price_cents", "currency"}
    )
    blob = str(offered.get("merchant_reasoning") or "").lower()
    assert "margin" not in blob
    assert "cogs" not in blob
    assert "contribution" not in blob


def test_capabilities_advertise_protocol(client: TestClient) -> None:
    caps = ExternalAgentClient(client).capabilities()
    assert caps["protocol_name"] == "astraos-agent"
    assert caps["version"] == "1.0"
    assert "request_offer" in caps["operations"]
    assert "accept_offer" in caps["operations"]

"""Read-only agent activity listing for merchant Integrations views."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.agent_client import ExternalAgentClient

HERO = (
    "I need wireless ANC headphones under A$350 for a long-haul flight. "
    "I need them today. Comfort and reliability matter more than buying "
    "the cheapest option."
)


def test_activity_empty_or_list(client: TestClient) -> None:
    response = client.get("/api/v1/agent/activity")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert isinstance(body["items"], list)


def test_activity_includes_agent_request(client: TestClient) -> None:
    agent = ExternalAgentClient(client)
    offered = agent.request_offer(HERO)
    session_id = offered["negotiation_session_id"]
    response = client.get("/api/v1/agent/activity?limit=10")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    match = next(
        (item for item in items if item["negotiation_session_id"] == session_id),
        None,
    )
    assert match is not None
    assert match["channel"] == "AGENT_API"
    assert match["request_id"] == offered["request_id"]
    assert match["intent_summary"]
    # Public activity must not leak private economics keys.
    blob = str(match).lower()
    assert "cogs" not in blob
    assert "margin" not in blob
    assert "contribution" not in blob

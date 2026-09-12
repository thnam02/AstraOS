"""External Buyer Agent client. Talks only to the public agent HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


class ExternalAgentClient:
    """Must not import AstraOS services or decision modules."""

    def __init__(self, client: TestClient) -> None:
        self.client = client

    def capabilities(self) -> dict[str, Any]:
        response = self.client.get("/api/v1/agent/capabilities")
        assert response.status_code == 200
        return response.json()

    def request_offer(
        self, intent: str, buyer_profile: str = "INTENT_ADAPTED"
    ) -> dict[str, Any]:
        response = self.client.post(
            "/api/v1/agent/offers/request",
            json={
                "natural_language_intent": intent,
                "buyer_profile": buyer_profile,
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    def inspect_offer(self, proposal_id: str) -> dict[str, Any]:
        response = self.client.get(f"/api/v1/agent/offers/{proposal_id}")
        assert response.status_code == 200, response.text
        return response.json()

    def counter_offer(self, session_id: str, message: str) -> dict[str, Any]:
        response = self.client.post(
            "/api/v1/agent/offers/counter",
            json={"session_id": session_id, "message": message},
        )
        assert response.status_code == 200, response.text
        return response.json()

    def accept_offer(
        self, session_id: str, proposal_id: str, idempotency_key: str
    ) -> Any:
        return self.client.post(
            "/api/v1/agent/offers/accept",
            json={
                "session_id": session_id,
                "proposal_id": proposal_id,
                "idempotency_key": idempotency_key,
            },
        )

    def get_order(self, ref: str) -> dict[str, Any]:
        response = self.client.get(f"/api/v1/agent/orders/{ref}")
        assert response.status_code == 200, response.text
        return response.json()

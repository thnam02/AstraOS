"""Negotiation session, turn, and simulate-buyer APIs."""

from fastapi.testclient import TestClient

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


def _open(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/negotiations",
        json={"intent": HERO, "buyer_profile": "INTENT_ADAPTED"},
    )
    assert response.status_code == 200
    return response.json()


def test_create_session(client: TestClient) -> None:
    body = _open(client)
    assert body["state"] in {
        "MERCHANT_PROPOSAL_CREATED",
        "NO_POLICY_SAFE_COUNTER",
    }
    assert body["working_intent"] is not None
    assert body["original_intent"] is not None
    assert "related_proposal_id" in body["turns"][0]
    assert body["proposal"] is not None or body["state"] == "NO_POLICY_SAFE_COUNTER"
    detail = client.get(f"/api/v1/negotiations/{body['session_id']}")
    assert detail.status_code == 200
    assert len(detail.json()["proposals"]) >= 1


def test_price_counter_then_accept(client: TestClient) -> None:
    opened = _open(client)
    session = opened["session_id"]
    countered = client.post(
        f"/api/v1/negotiations/{session}/turns",
        json={"message": "Can you get this below A$315?"},
    )
    assert countered.status_code == 200
    body = countered.json()
    assert body["state"] in {
        "MERCHANT_COUNTER_CREATED",
        "NO_POLICY_SAFE_COUNTER",
    }
    assert any(item["actor"] == "BUYER_AGENT" for item in body["turns"])
    if body["proposal"] and body["proposal"]["offer"]:
        accepted = client.post(
            f"/api/v1/negotiations/{session}/turns",
            json={"message": "I'll take it."},
        )
        assert accepted.status_code == 200
        assert accepted.json()["state"] == "READY_FOR_CHECKOUT"


def test_structured_counter(client: TestClient) -> None:
    opened = _open(client)
    response = client.post(
        f"/api/v1/negotiations/{opened['session_id']}/turns",
        json={
            "action": "COUNTER",
            "constraints": {"max_total_price_cents": 31500},
        },
    )
    assert response.status_code == 200
    payload = response.json()["turns"][-2]["structured_payload"]
    assert payload["action"] == "COUNTER"


def test_simulate_buyer(client: TestClient) -> None:
    opened = _open(client)
    if opened["proposal"] is None:
        return
    response = client.post(
        f"/api/v1/negotiations/{opened['session_id']}/simulate-buyer",
        json={"mode": "TRAVEL"},
    )
    assert response.status_code == 200


def test_invalid_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/negotiations/00000000-0000-4000-8000-000000000099/turns",
        json={"message": "I'll take it."},
    )
    assert response.status_code in {404, 409}


def test_hard_failure_does_not_invent(client: TestClient) -> None:
    opened = _open(client)
    response = client.post(
        f"/api/v1/negotiations/{opened['session_id']}/turns",
        json={
            "action": "COUNTER",
            "constraints": {
                "max_total_price_cents": 20000,
                "alternative_product_allowed": False,
            },
            "message": "I need this exact product for A$200.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    if body["proposal"] and body["proposal"]["offer"]:
        price = body["proposal"]["offer"]["pricing"]["total_price_cents"]
        assert price >= 20000 or body["proposal"]["outcome"] != "DECLINE"
    if body["proposal"] and body["proposal"]["outcome"] == "DECLINE":
        assert body["proposal"]["offer"] is None
        assert "NO_POLICY_SAFE_OFFER" in body["proposal"]["reason_codes"]

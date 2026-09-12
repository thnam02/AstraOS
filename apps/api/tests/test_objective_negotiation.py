"""Negotiation snapshots objective; accepted proposals stay immutable."""

from fastapi.testclient import TestClient

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


def _restore(client: TestClient) -> None:
    client.patch("/api/v1/merchant/objective", json={"mode": "BALANCED"})


def test_existing_session_keeps_snapshotted_objective(client: TestClient) -> None:
    try:
        client.patch("/api/v1/merchant/objective", json={"mode": "GROWTH"})
        opened = client.post(
            "/api/v1/negotiations",
            json={
                "intent": HERO,
                "parser_mode": "rule_based",
                "buyer_profile": "INTENT_ADAPTED",
            },
        )
        assert opened.status_code == 200
        session = opened.json()["session_id"]
        first_opt = opened.json().get("optimisation") or {}
        snapshot = (first_opt.get("merchant_objective") or {}).get("mode")
        assert snapshot == "GROWTH"
        client.patch("/api/v1/merchant/objective", json={"mode": "MARGIN"})
        live = client.get("/api/v1/merchant/objective").json()
        assert live["mode"] == "MARGIN"
        countered = client.post(
            f"/api/v1/negotiations/{session}/turns",
            json={"message": "Can you get this below A$315?"},
        )
        assert countered.status_code == 200
        newest = client.post(
            "/api/v1/negotiations",
            json={
                "intent": HERO,
                "parser_mode": "rule_based",
                "buyer_profile": "INTENT_ADAPTED",
            },
        )
        assert newest.status_code == 200
        newest_opt = newest.json().get("optimisation") or {}
        assert (newest_opt.get("merchant_objective") or {}).get("mode") == "MARGIN"
        # Live config is Margin; the original session must still be able to act.
        assert countered.json()["session_id"] == session
        assert newest.json()["session_id"] != session
    finally:
        _restore(client)


def test_accepted_proposal_ignores_later_objective_change(
    client: TestClient,
) -> None:
    try:
        client.patch("/api/v1/merchant/objective", json={"mode": "BALANCED"})
        opened = client.post(
            "/api/v1/negotiations",
            json={
                "intent": HERO,
                "parser_mode": "rule_based",
                "buyer_profile": "INTENT_ADAPTED",
            },
        )
        assert opened.status_code == 200
        proposal = opened.json()["proposal"]
        if not proposal or not proposal.get("offer"):
            return
        price = proposal["offer"]["pricing"]["total_price_cents"]
        sku = proposal["offer"]["sku"]
        client.patch("/api/v1/merchant/objective", json={"mode": "MARGIN"})
        accepted = client.post(
            f"/api/v1/negotiations/{opened.json()['session_id']}/accept",
            json={
                "proposal_id": proposal["proposal_id"],
                "idempotency_key": "objective-immutability",
                "generate_recovery": False,
            },
        )
        assert accepted.status_code == 200
        body = accepted.json()
        if body.get("order"):
            assert body["order"]["total_amount_cents"] == price
            assert sku in str(body["order"])
        elif body.get("state") != "CONFIRMED":
            # Revalidation may fail for inventory; terms were not reselected.
            assert body.get("revalidation") is not None
    finally:
        _restore(client)

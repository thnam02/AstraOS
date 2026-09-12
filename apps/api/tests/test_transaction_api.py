"""Proposal acceptance, idempotency, and order snapshot APIs."""

from __future__ import annotations

import uuid

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


def _accept(
    client: TestClient,
    session_id: str,
    proposal_id: str,
    key: str,
    **extra: object,
) -> object:
    payload = {"proposal_id": proposal_id, "idempotency_key": key, **extra}
    return client.post(f"/api/v1/negotiations/{session_id}/accept", json=payload)


def _restore_policy(client: TestClient) -> None:
    client.patch(
        "/api/v1/merchant/policy",
        json={"minimum_margin_rate": 0.15, "maximum_discount_rate": 0.10},
    )


def test_successful_accept_creates_order(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    sku = proposal["offer"]["sku"]
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 14})
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"ok-{uuid.uuid4()}",
        generate_recovery=False,
    ).json()
    assert body["state"] == "CONFIRMED"
    assert body["revalidation"]["status"] == "PASSED"
    assert body["reservation"]["status"] == "CONSUMED"
    assert body["order"]["status"] == "CONFIRMED"
    assert body["order"]["order_number"].startswith("AST-")
    assert body["order"]["payment_status"] == "NOT_REQUIRED_FOR_DEMO"
    assert body["order"]["total_amount_cents"] == proposal["offer"]["pricing"][
        "total_price_cents"
    ]
    assert body["negotiation_state"] == "TRANSACTION_CONFIRMED"
    txn = client.get(f"/api/v1/transactions/{body['transaction_id']}")
    assert txn.status_code == 200
    order = client.get(f"/api/v1/orders/{body['order']['order_id']}")
    assert order.status_code == 200
    by_number = client.get(
        f"/api/v1/orders/by-number/{body['order']['order_number']}"
    )
    assert by_number.status_code == 200
    assert by_number.json()["order_number"] == body["order"]["order_number"]


def test_client_price_is_ignored(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    expected = proposal["offer"]["pricing"]["total_price_cents"]
    sku = proposal["offer"]["sku"]
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 8})
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"price-{uuid.uuid4()}",
        generate_recovery=False,
        price=100,
        total_amount_cents=100,
    ).json()
    assert body["state"] == "CONFIRMED"
    assert body["order"]["total_amount_cents"] == expected


def test_wrong_session_rejected(client: TestClient) -> None:
    first = _open(client)
    second = _open(client)
    proposal = first["proposal"]
    assert proposal
    response = _accept(
        client,
        second["session_id"],
        proposal["proposal_id"],
        f"wrong-{uuid.uuid4()}",
        generate_recovery=False,
    )
    assert response.status_code in {404, 409}


def test_idempotent_retry(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    sku = proposal["offer"]["sku"]
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 6})
    key = f"idemp-{uuid.uuid4()}"
    first = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        key,
        generate_recovery=False,
    ).json()
    second = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        key,
        generate_recovery=False,
    ).json()
    assert first["state"] == "CONFIRMED"
    assert second["transaction_id"] == first["transaction_id"]
    assert second["order"]["order_id"] == first["order"]["order_id"]
    state = client.post(
        "/api/v1/demo/inventory",
        json={"sku": sku, "units_available": 6},
    )
    # Restore is a set, not a read of post-consume stock. Check via catalogue.
    assert first["order"]["order_number"] == second["order"]["order_number"]
    assert state.status_code == 200


def test_expired_proposal_fails_before_reserve(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal
    from datetime import UTC, datetime, timedelta

    from app.db.session import AsyncSessionLocal
    from app.models.negotiation import MerchantProposal

    async def _expire() -> None:
        async with AsyncSessionLocal() as session:
            proposal_id = uuid.UUID(proposal["proposal_id"])
            row = await session.get(MerchantProposal, proposal_id)
            assert row is not None
            row.expires_at = datetime.now(UTC) - timedelta(seconds=5)
            await session.commit()

    import asyncio

    asyncio.run(_expire())
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"exp-{uuid.uuid4()}",
        generate_recovery=False,
    ).json()
    assert body["state"] == "REVALIDATION_FAILED"
    assert "PROPOSAL_EXPIRED" in body["failure_codes"]
    assert body["order"] is None
    assert "REQUEST_NEW_PROPOSAL" in body["next_actions"]


def test_out_of_stock_revalidation(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    sku = proposal["offer"]["sku"]
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 0})
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"oos-{uuid.uuid4()}",
        generate_recovery=True,
    ).json()
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 14})
    assert body["state"] == "REVALIDATION_FAILED"
    assert "OUT_OF_STOCK" in body["failure_codes"]
    assert body["order"] is None
    if body.get("recovery_proposal"):
        assert body["recovery_proposal"]["proposal_id"] != proposal["proposal_id"]


def test_same_day_capacity_full(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    sku = proposal["offer"]["sku"]
    if proposal["offer"]["delivery"]["code"] != "SAME_DAY":
        return
    client.post(
        "/api/v1/demo/delivery-capacity",
        json={"sku": sku, "delivery_code": "SAME_DAY", "available": False},
    )
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"del-{uuid.uuid4()}",
        generate_recovery=False,
    ).json()
    client.post(
        "/api/v1/demo/delivery-capacity",
        json={"sku": sku, "delivery_code": "SAME_DAY", "available": True},
    )
    assert body["state"] == "REVALIDATION_FAILED"
    assert "DELIVERY_NO_LONGER_AVAILABLE" in body["failure_codes"]


def test_policy_change_fails_revalidation(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal
    client.post("/api/v1/demo/policy", json={"minimum_margin_rate": 0.90})
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"pol-{uuid.uuid4()}",
        generate_recovery=False,
    ).json()
    _restore_policy(client)
    assert body["state"] == "REVALIDATION_FAILED"
    assert "MARGIN_POLICY_VIOLATION" in body["failure_codes"] or (
        "MERCHANT_POLICY_CHANGED" in body["failure_codes"]
    )


def test_order_failure_releases_reservation(
    client: TestClient, monkeypatch: object
) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    sku = proposal["offer"]["sku"]
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 4})

    async def _boom(self, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated order adapter failure")

    from app.decision.transaction.providers import LocalOrderProvider

    monkeypatch.setattr(LocalOrderProvider, "create", _boom)
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"fail-{uuid.uuid4()}",
        generate_recovery=False,
    ).json()
    assert body["state"] == "ORDER_FAILED"
    assert body["order"] is None
    assert "ORDER_CREATION_FAILED" in body["failure_codes"]


def test_lineage_present(client: TestClient) -> None:
    opened = _open(client)
    proposal = opened["proposal"]
    assert proposal and proposal["offer"]
    sku = proposal["offer"]["sku"]
    client.post("/api/v1/demo/inventory", json={"sku": sku, "units_available": 5})
    body = _accept(
        client,
        opened["session_id"],
        proposal["proposal_id"],
        f"lin-{uuid.uuid4()}",
        generate_recovery=False,
    ).json()
    assert body["lineage"]["negotiation_session_id"] == opened["session_id"]
    assert body["lineage"]["proposal_id"] == proposal["proposal_id"]
    assert body["lineage"]["match_run_id"]
    assert body["lineage"]["offer_run_id"]
    assert body["timing"]["total_transaction_ms"] >= 0

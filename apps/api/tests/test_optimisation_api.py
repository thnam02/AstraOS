"""Optimisation and full decision HTTP APIs."""

from fastapi.testclient import TestClient

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)

BUDGET = "cheapest wireless ANC headphones under A$200 delivered in two days"
TIGHT = "ANC headphones under A$80 delivered today"


def test_full_decision_run(client: TestClient) -> None:
    response = client.post(
        "/api/v1/decision/run",
        json={
            "intent": HERO,
            "parser_mode": "rule_based",
            "buyer_profile": "INTENT_ADAPTED",
        },
    )
    assert response.status_code == 200
    body = response.json()
    opt = body["optimisation"]
    assert "p_win" not in str(body).lower()
    assert "win probability" not in str(body).lower()
    assert opt["buyer_model"]["type"] == "SIMULATED_UTILITY"
    assert "cold-start" in opt["buyer_model"]["disclaimer"].lower()
    assert opt["summary"]["offers_considered"] > 0
    if opt["recommended_offer"]:
        rec = opt["recommended_offer"]
        assert rec["is_pareto_efficient"]
        assert rec["is_recommended"]
        assert rec["policy_safe"]
        assert rec["utility_trace"]["components"]
        assert all(item["is_pareto_efficient"] for item in opt["pareto_offers"])


def test_optimisation_from_offer_run(client: TestClient) -> None:
    created = client.post(
        "/api/v1/offers/generate",
        json={"intent": HERO, "max_products": 4, "limit": 10},
    )
    assert created.status_code == 200
    offer_run = created.json()["offer_run_id"]
    first = client.post(
        "/api/v1/optimisation/run",
        json={"offer_run_id": offer_run, "buyer_profile": "BUDGET_SHOPPER"},
    )
    second = client.post(
        "/api/v1/optimisation/run",
        json={"offer_run_id": offer_run, "buyer_profile": "URGENT_TRAVELLER"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["optimisation_run_id"] != second.json()["optimisation_run_id"]
    detail = client.get(
        f"/api/v1/optimisation/runs/{first.json()['optimisation_run_id']}"
    )
    assert detail.status_code == 200
    frontier = client.get(
        f"/api/v1/optimisation/runs/{first.json()['optimisation_run_id']}/frontier"
    )
    assert frontier.status_code == 200


def test_missing_offer_run(client: TestClient) -> None:
    response = client.post(
        "/api/v1/optimisation/run",
        json={"offer_run_id": "00000000-0000-4000-8000-000000000099"},
    )
    assert response.status_code == 404


def test_no_policy_safe_is_explicit(client: TestClient) -> None:
    response = client.post(
        "/api/v1/decision/run",
        json={"intent": TIGHT, "buyer_profile": "BUDGET_SHOPPER", "max_products": 6},
    )
    assert response.status_code == 200
    opt = response.json()["optimisation"]
    if opt["recommended_offer"] is None:
        assert opt["failure"] is not None
        assert opt["failure"]["code"] in {
            "NO_POLICY_SAFE_OFFER",
            "NO_COMPLIANT_OFFER",
        }


def test_margin_floor_changes_frontier(client: TestClient) -> None:
    constructed = client.post(
        "/api/v1/offers/generate",
        json={"intent": HERO, "max_products": 3, "limit": 5},
    )
    offer_run = constructed.json()["offer_run_id"]
    loose = client.post(
        "/api/v1/optimisation/run",
        json={"offer_run_id": offer_run, "buyer_profile": "INTENT_ADAPTED"},
    )
    try:
        client.patch("/api/v1/merchant/policy", json={"minimum_margin_rate": 0.45})
        tight = client.post(
            "/api/v1/optimisation/run",
            json={"offer_run_id": offer_run, "buyer_profile": "INTENT_ADAPTED"},
        )
        assert loose.status_code == 200
        assert tight.status_code == 200
        loose_safe = loose.json()["summary"]["policy_safe"]
        tight_safe = tight.json()["summary"]["policy_safe"]
        assert tight_safe <= loose_safe
    finally:
        client.patch("/api/v1/merchant/policy", json={"minimum_margin_rate": 0.15})

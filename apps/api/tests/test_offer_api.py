"""Offer construction HTTP APIs."""

from fastapi.testclient import TestClient

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


def test_generate_from_intent(client: TestClient) -> None:
    response = client.post(
        "/api/v1/offers/generate",
        json={
            "intent": HERO,
            "parser_mode": "rule_based",
            "max_products": 4,
            "limit": 20,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]
    assert summary["generated_candidates"] > 0
    assert summary["feasible_candidates"] >= 1
    assert summary["generated_candidates"] == (
        summary["feasible_candidates"] + summary["rejected_candidates"]
    )
    assert payload["dimensions"]["price_options"] >= 2
    offers = payload["offers"]
    assert offers
    first = offers[0]
    assert first["feasibility_status"] == "FEASIBLE"
    pricing = first["pricing"]
    assert pricing["total_price_cents"] == (
        pricing["product_price_cents"]
        + pricing["delivery_charge_cents"]
        + pricing["warranty_price_cents"]
        + pricing["bundle_price_cents"]
    )
    assert "recommended" not in str(payload).lower()
    assert "pareto" not in str(payload).lower()
    assert first["proof"]


def test_generate_requires_input(client: TestClient) -> None:
    response = client.post("/api/v1/offers/generate", json={})
    assert response.status_code == 422


def test_generate_from_match_run(client: TestClient) -> None:
    matched = client.post(
        "/api/v1/match",
        json={"intent": HERO, "parser_mode": "rule_based", "limit": 3},
    )
    assert matched.status_code == 200
    run_id = matched.json()["run_id"]
    created = client.post(
        "/api/v1/offers/generate",
        json={"match_run_id": run_id, "max_products": 3, "limit": 10},
    )
    assert created.status_code == 200
    assert created.json()["match_run_id"] == run_id
    assert created.json()["input"]["matched_products"] == 3


def test_offer_run_and_detail(client: TestClient) -> None:
    created = client.post(
        "/api/v1/offers/generate",
        json={
            "intent": "wireless ANC headphones under $300 delivered today",
            "limit": 5,
        },
    )
    assert created.status_code == 200
    run_id = created.json()["offer_run_id"]
    listed = client.get(
        f"/api/v1/offers/runs/{run_id}",
        params={"status": "FEASIBLE", "limit": 5},
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["total_offers"] >= 1
    offer_id = body["offers"][0]["offer_id"]
    detail = client.get(f"/api/v1/offers/{offer_id}")
    assert detail.status_code == 200
    offer = detail.json()["offer"]
    assert offer["sku"]
    assert offer["expires_at"]
    assert "buyer_utility" not in offer
    assert "p_win" not in offer


def test_offer_run_filters(client: TestClient) -> None:
    created = client.post(
        "/api/v1/offers/generate",
        json={"intent": HERO, "max_products": 2, "limit": 5},
    )
    run_id = created.json()["offer_run_id"]
    filtered = client.get(
        f"/api/v1/offers/runs/{run_id}",
        params={"delivery": "SAME_DAY", "status": "FEASIBLE"},
    )
    assert filtered.status_code == 200
    for card in filtered.json()["offers"]:
        assert card["delivery"]["code"] == "SAME_DAY"


def test_missing_run(client: TestClient) -> None:
    response = client.get(
        "/api/v1/offers/runs/00000000-0000-4000-8000-000000000099"
    )
    assert response.status_code == 404


def test_second_run_does_not_replace_first(client: TestClient) -> None:
    first = client.post(
        "/api/v1/offers/generate",
        json={"intent": "ANC headphones under $200", "max_products": 2, "limit": 3},
    )
    second = client.post(
        "/api/v1/offers/generate",
        json={"intent": HERO, "max_products": 2, "limit": 3},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["offer_run_id"] != second.json()["offer_run_id"]
    replay = client.get(f"/api/v1/offers/runs/{first.json()['offer_run_id']}")
    assert replay.status_code == 200

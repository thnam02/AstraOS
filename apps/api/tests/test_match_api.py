"""Analyse and match HTTP APIs."""

from fastapi.testclient import TestClient

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


def test_analyse_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intent/analyse",
        json={"intent": HERO, "parser_mode": "rule_based"},
    )
    assert response.status_code == 200
    intent = response.json()["intent"]
    assert intent["category"] == "headphones"
    assert intent["context_items"]
    assert intent["desired_outcomes"]
    assert intent["tradeoffs"]


def test_match_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/match",
        json={"intent": HERO, "parser_mode": "rule_based", "limit": 8},
    )
    assert response.status_code == 200
    payload = response.json()
    qual = payload["qualification"]
    assert qual["variants_checked"] > 200
    assert qual["eligible"] >= 1
    matches = payload["semantic_matching"]["matches"]
    assert matches
    assert matches[0]["rank"] == 1
    for card in matches:
        assert card["reasons"]
        for reason in card["reasons"]:
            assert reason["facts"]
            assert "great for travel" not in str(reason).lower()
        assert 0 <= card["overall_semantic_fit"] <= 1
        assert "probability" not in card


def test_match_invalid_payload(client: TestClient) -> None:
    response = client.post("/api/v1/match", json={"intent": ""})
    assert response.status_code == 422


def test_match_no_eligible(client: TestClient) -> None:
    response = client.post(
        "/api/v1/match",
        json={"intent": "must look luxurious"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["qualification"]["eligible"] == 0
    assert payload["semantic_matching"]["matches"] == []


def test_match_run_detail(client: TestClient) -> None:
    created = client.post(
        "/api/v1/match",
        json={"intent": "wireless ANC headphones under $300", "limit": 5},
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    detail = client.get(f"/api/v1/match/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["semantic_matching"]["matches"]


def test_match_missing_run(client: TestClient) -> None:
    response = client.get("/api/v1/match/00000000-0000-4000-8000-000000000099")
    assert response.status_code == 404


def test_qualify_still_works(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intent/qualify",
        json={"intent": "must have ANC", "parser_mode": "rule_based"},
    )
    assert response.status_code == 200
    assert response.json()["summary"]["variants_checked"] > 0

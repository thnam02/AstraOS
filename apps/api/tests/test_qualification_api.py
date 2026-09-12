"""Qualification HTTP API."""

from fastapi.testclient import TestClient

from tests.qualification_fixtures import HERO_INTENT


def test_qualify_hero_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intent/qualify",
        json={"intent": HERO_INTENT, "parser_mode": "rule_based"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "READY"
    assert payload["intent"]["category"] == "headphones"
    fields = {item["field"] for item in payload["intent"]["hard_constraints"]}
    assert {"anc", "price", "delivery_days"} <= fields
    summary = payload["summary"]
    assert summary["variants_checked"] > 200
    assert summary["eligible"] >= 1
    assert summary["violated"] >= 1
    assert summary["uncertain"] >= 1
    assert (
        summary["eligible"] + summary["violated"] + summary["uncertain"]
        == summary["variants_checked"]
    )
    assert payload["timing"]["total_ms"] >= 0
    assert payload["eligible_products"]
    for card in payload["eligible_products"]:
        assert card["eligible"] is True
        assert card["violated_count"] == 0
        assert card["unknown_count"] == 0
    for card in payload["uncertain_products"]:
        assert card["eligible"] is False
        assert card["unknown_count"] >= 1
        assert card["violated_count"] == 0
    for card in payload["rejected_products"]:
        assert card["eligible"] is False
        assert card["violated_count"] >= 1


def test_qualify_invalid_payload(client: TestClient) -> None:
    response = client.post("/api/v1/intent/qualify", json={"intent": ""})
    assert response.status_code == 422


def test_qualify_unsupported_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intent/qualify",
        json={"intent": "must look luxurious"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"NEEDS_CLARIFICATION", "UNSUPPORTED"}
    assert payload["intent"]["ambiguities"]
    assert payload["summary"]["eligible"] == 0


def test_qualification_detail_endpoints(client: TestClient) -> None:
    created = client.post(
        "/api/v1/intent/qualify",
        json={"intent": "must have ANC and in stock", "parser_mode": "rule_based"},
    )
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    listing = client.get(f"/api/v1/intent/qualification/{run_id}", params={"limit": 20})
    assert listing.status_code == 200
    body = listing.json()
    assert body["run_id"] == run_id
    assert body["variants"]
    variant_id = body["variants"][0]["variant_id"]
    detail = client.get(f"/api/v1/intent/qualification/{run_id}/variants/{variant_id}")
    assert detail.status_code == 200
    evaluations = detail.json()["variant"]["evaluations"]
    assert evaluations
    assert {item["status"] for item in evaluations} <= {
        "SATISFIED",
        "VIOLATED",
        "UNKNOWN",
    }


def test_qualification_run_missing(client: TestClient) -> None:
    response = client.get(
        "/api/v1/intent/qualification/00000000-0000-4000-8000-000000000099"
    )
    assert response.status_code == 404


def test_qualify_battery_case(client: TestClient) -> None:
    response = client.post(
        "/api/v1/intent/qualify",
        json={"intent": "headphones with battery >= 40h"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["variants_checked"] > 0
    battery = payload["intent"]["hard_constraints"][0]
    assert battery["field"] == "battery_hours"
    assert battery["operator"] == "GTE"

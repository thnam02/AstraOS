"""Arena HTTP APIs carry the synthetic disclaimer."""

from fastapi.testclient import TestClient

HERO = (
    "I need ANC headphones under A$350 for a long-haul flight. "
    "Delivered today. Comfort and reliability matter more than "
    "getting the cheapest option."
)


def test_live_duel(client: TestClient) -> None:
    response = client.post(
        "/api/v1/arena/run",
        json={"intent": HERO, "buyer_profile": "URGENT_TRAVELLER"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "synthetic" in body["disclaimer"].lower()
    assert "conversion uplift" in body["disclaimer"].lower()
    names = [item["name"] for item in body["strategies"]]
    assert "DEFAULT" in names
    assert "ASTRAOS" in names
    assert "p_win" not in str(body).lower()
    assert "increases conversion" not in str(body).lower()


def test_small_benchmark_and_export(client: TestClient) -> None:
    created = client.post(
        "/api/v1/arena/benchmarks",
        json={"mission_count": 8, "seed": 2026},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "COMPLETED"
    assert "synthetic" in body["disclaimer"].lower()
    detail = client.get(f"/api/v1/arena/benchmarks/{body['benchmark_id']}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["mission_count"] == 8
    assert payload["strategy_metrics"]
    assert all(row["policy_violation_rate"] == 0 for row in payload["strategy_metrics"])
    exported = client.get(
        f"/api/v1/arena/benchmarks/{body['benchmark_id']}/export?format=csv"
    )
    assert exported.status_code == 200
    assert "selection_rate" in exported.text
    latest = client.get("/api/v1/arena/benchmarks/latest")
    assert latest.status_code == 200
    assert latest.json()["benchmark_id"] == body["benchmark_id"]

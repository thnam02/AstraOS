"""Arena snapshots merchant objective and stays reproducible."""

from fastapi.testclient import TestClient

HERO = (
    "I need ANC headphones under A$350 for a long-haul flight. "
    "Delivered today. Comfort and reliability matter more than "
    "getting the cheapest option."
)


def test_benchmark_snapshots_balanced_by_default(client: TestClient) -> None:
    created = client.post(
        "/api/v1/arena/benchmarks",
        json={"mission_count": 6, "seed": 2026},
    )
    assert created.status_code == 200
    detail = client.get(
        f"/api/v1/arena/benchmarks/{created.json()['benchmark_id']}"
    )
    assert detail.status_code == 200
    payload = detail.json()
    config = payload["config"]
    snapshot = config.get("merchant_objective") or {}
    assert config.get("merchant_objective_mode") == "BALANCED"
    assert snapshot.get("mode") == "BALANCED"
    assert snapshot.get("buyer_weight") == 0.5
    assert all(row["policy_violation_rate"] == 0 for row in payload["strategy_metrics"])


def test_same_seed_and_objective_is_reproducible(client: TestClient) -> None:
    first = client.post(
        "/api/v1/arena/run",
        json={
            "intent": HERO,
            "buyer_profile": "URGENT_TRAVELLER",
            "seed": 2026,
            "merchant_objective_mode": "BALANCED",
        },
    )
    second = client.post(
        "/api/v1/arena/run",
        json={
            "intent": HERO,
            "buyer_profile": "URGENT_TRAVELLER",
            "seed": 2026,
            "merchant_objective_mode": "BALANCED",
        },
    )
    assert first.status_code == 200
    assert second.status_code == 200
    a = {
        item["name"]: item["response"].get("sku")
        for item in first.json()["strategies"]
    }
    b = {
        item["name"]: item["response"].get("sku")
        for item in second.json()["strategies"]
    }
    assert a["DEFAULT"] == b["DEFAULT"]
    assert a["ALWAYS_DISCOUNT"] == b["ALWAYS_DISCOUNT"]
    assert a["SEMANTIC_ONLY"] == b["SEMANTIC_ONLY"]
    assert a["ASTRAOS"] == b["ASTRAOS"]


def test_changing_objective_can_change_astraos_only(client: TestClient) -> None:
    balanced = client.post(
        "/api/v1/arena/run",
        json={
            "intent": HERO,
            "buyer_profile": "URGENT_TRAVELLER",
            "seed": 2026,
            "merchant_objective_mode": "BALANCED",
        },
    )
    growth = client.post(
        "/api/v1/arena/run",
        json={
            "intent": HERO,
            "buyer_profile": "URGENT_TRAVELLER",
            "seed": 2026,
            "merchant_objective_mode": "GROWTH",
        },
    )
    assert balanced.status_code == 200
    assert growth.status_code == 200
    b = {
        item["name"]: item["response"].get("sku")
        for item in balanced.json()["strategies"]
    }
    g = {
        item["name"]: item["response"].get("sku")
        for item in growth.json()["strategies"]
    }
    assert b["DEFAULT"] == g["DEFAULT"]
    assert b["ALWAYS_DISCOUNT"] == g["ALWAYS_DISCOUNT"]
    assert b["SEMANTIC_ONLY"] == g["SEMANTIC_ONLY"]
    # AstraOS may stay on the same efficient offer; that is valid.
    assert "ASTRAOS" in b and "ASTRAOS" in g

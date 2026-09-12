"""Learning HTTP surface stays labelled synthetic."""

from fastapi.testclient import TestClient


def test_generate_train_list_and_detail(client: TestClient) -> None:
    created = client.post(
        "/api/v1/learning/datasets/generate",
        json={"interaction_count_target": 40, "seed": 2026},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["interaction_count"] <= 40
    assert body["positive_count"] >= 0
    assert "simulated" in body["disclaimer"].lower()
    assert "real-world conversion" in body["disclaimer"].lower()
    assert "FUTURE_REAL_COMMERCE" not in str(body["source_types"])
    trained = client.post(
        "/api/v1/learning/train",
        json={"dataset_id": body["dataset_id"], "seed": 2026},
    )
    assert trained.status_code == 200, trained.text
    report = trained.json()
    blob = str(report).lower()
    assert "conversion" not in blob or "not" in report["disclaimer"].lower()
    assert "LOGISTIC_REGRESSION" in report["reports"]
    assert "GRADIENT_BOOSTING" in report["reports"]
    assert "COLD_START_UTILITY" in report["reports"]
    models = client.get("/api/v1/learning/models")
    assert models.status_code == 200
    listed = models.json()
    assert listed
    detail = client.get(f"/api/v1/learning/models/{listed[0]['model_id']}")
    assert detail.status_code == 200
    assert "simulated" in detail.json()["disclaimer"].lower()
    overview = client.get("/api/v1/learning/overview")
    assert overview.status_code == 200
    assert overview.json()["maturity"][-1]["state"] == "FUTURE"
    decision = client.post(
        "/api/v1/decision/run",
        json={
            "intent": (
                "I'm flying from Sydney to Singapore tomorrow and need wireless "
                "noise-cancelling headphones under A$350. I need them delivered today."
            ),
            "parser_mode": "rule_based",
        },
    )
    assert decision.status_code == 200
    opt = decision.json()["optimisation"]
    assert opt["buyer_model"]["type"] == "SIMULATED_UTILITY"
    scored = client.post(
        f"/api/v1/learning/models/{listed[0]['model_id']}/score",
        json={"optimisation_run_id": opt["optimisation_run_id"]},
    )
    assert scored.status_code == 200
    payload = scored.json()
    assert "simulated" in payload["disclaimer"].lower()
    assert payload["score_label"] == "Synthetic Response Score"
    assert "conversion" not in payload["score_label"].lower()


def test_default_mode_is_cold_start() -> None:
    from app.config import settings

    assert settings.response_model_mode == "COLD_START"

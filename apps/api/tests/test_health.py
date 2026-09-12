"""Health endpoint contract."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    """GET /health returns the Stage 0 liveness payload."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "astraos-api"}

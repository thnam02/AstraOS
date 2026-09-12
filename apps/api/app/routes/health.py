"""Liveness endpoint."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return process liveness. No domain logic."""
    return HealthResponse(status="ok", service="astraos-api")

"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.schemas import ReadyResponse
from app.db.dependencies import get_db
from app.schemas.health import HealthResponse
from app.services.readiness import evaluate_readiness

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return process liveness. No domain logic."""
    return HealthResponse(status="ok", service="astraos-api")


@router.get("/ready", response_model=ReadyResponse)
async def get_ready(db: AsyncSession = Depends(get_db)) -> ReadyResponse:
    return await evaluate_readiness(db)

"""End-to-end decision route. Orchestrates existing services."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.optimisation import DecisionRequest
from app.services.decision import DecisionResponse, DecisionService

router = APIRouter(prefix="/decision", tags=["decision"])


def _service(db: AsyncSession = Depends(get_db)) -> DecisionService:
    return DecisionService(db)


@router.post("/run", response_model=DecisionResponse)
async def run_decision(
    payload: DecisionRequest,
    service: DecisionService = Depends(_service),
) -> DecisionResponse:
    return await service.run(payload)

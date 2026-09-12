"""Synthetic Agent Arena HTTP surface."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.decision.arena.config import ArenaBenchmarkConfig, ArenaDuelRequest
from app.schemas.arena import (
    ArenaBenchmarkCreated,
    ArenaBenchmarkRequest,
    ArenaBenchmarkResponse,
    ArenaRunRequest,
    ArenaRunResponse,
)
from app.services.arena import ArenaService

router = APIRouter(prefix="/arena", tags=["arena"])


def _service(db: AsyncSession = Depends(get_db)) -> ArenaService:
    return ArenaService(db)


@router.post("/run", response_model=ArenaRunResponse)
async def run_arena(
    payload: ArenaRunRequest,
    service: ArenaService = Depends(_service),
) -> ArenaRunResponse:
    return await service.duel(
        ArenaDuelRequest(
            intent=payload.intent,
            buyer_profile=payload.buyer_profile,
            strategies=payload.strategies,
            outside_option_utility=payload.outside_option_utility,
            seed=payload.seed,
        )
    )


@router.post("/benchmarks", response_model=ArenaBenchmarkCreated)
async def create_benchmark(
    payload: ArenaBenchmarkRequest,
    service: ArenaService = Depends(_service),
) -> ArenaBenchmarkCreated:
    return await service.benchmark(
        ArenaBenchmarkConfig(
            mission_count=payload.mission_count,
            seed=payload.seed,
            strategies=payload.strategies,
            buyer_profile=payload.buyer_profile,
            outside_option_utility=payload.outside_option_utility,
            persist_missions=payload.persist_missions,
        )
    )


@router.get("/benchmarks/latest", response_model=ArenaBenchmarkResponse)
async def get_latest_benchmark(
    service: ArenaService = Depends(_service),
) -> ArenaBenchmarkResponse:
    row = await service.get_latest_benchmark()
    if row is None:
        raise HTTPException(status_code=404, detail="No completed benchmark.")
    return row


@router.get("/benchmarks/{benchmark_id}", response_model=ArenaBenchmarkResponse)
async def get_benchmark(
    benchmark_id: UUID,
    service: ArenaService = Depends(_service),
) -> ArenaBenchmarkResponse:
    row = await service.get_benchmark(benchmark_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Benchmark not found.")
    return row


@router.get("/benchmarks/{benchmark_id}/export")
async def export_benchmark(
    benchmark_id: UUID,
    format: str = "json",
    service: ArenaService = Depends(_service),
) -> Response:
    fmt = "csv" if format.lower() == "csv" else "json"
    exported = await service.export_benchmark(benchmark_id, fmt)
    if exported is None:
        raise HTTPException(status_code=404, detail="Benchmark not found.")
    body, media = exported
    filename = f"astraos-arena-{benchmark_id}.{fmt}"
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

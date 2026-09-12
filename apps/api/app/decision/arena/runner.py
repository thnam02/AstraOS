"""Run one mission or a full synthetic benchmark with isolated state."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena import (
    ARENA_DISCLAIMER,
    ARENA_VERSION,
    BUYER_MODEL_VERSION,
    STRATEGY_SET_VERSION,
)
from app.decision.arena.config import ArenaBenchmarkConfig, ArenaDuelRequest
from app.decision.arena.context import ArenaCatalogueCache, ArenaContextBuilder
from app.decision.arena.explanation import explain_selection
from app.decision.arena.metrics import summarize
from app.decision.arena.missions import HERO_MISSION, generate_missions
from app.decision.arena.models import (
    ArenaBenchmarkSummary,
    ArenaMissionResult,
    BuyerMission,
)
from app.decision.arena.selection import choose_response
from app.decision.arena.strategies import strategy_set
from app.decision.utility.models import UTILITY_VERSION


def _events() -> list[dict[str, Any]]:
    return []


def _event(bucket: list[dict[str, Any]], name: str, **payload: Any) -> None:
    bucket.append(
        {
            "name": name,
            "at": datetime.now(UTC).isoformat(),
            **payload,
        }
    )


async def run_mission(
    session: AsyncSession,
    mission: BuyerMission,
    *,
    strategies: list[str],
    outside_option_utility: float,
    max_products: int,
    cache: ArenaCatalogueCache | None = None,
    events: list[dict[str, Any]] | None = None,
) -> tuple[ArenaMissionResult, dict[str, Any]]:
    started = time.perf_counter()
    log = events if events is not None else _events()
    _event(log, "ARENA_MISSION_CREATED", mission_id=mission.id)
    builder = ArenaContextBuilder(session, cache=cache)
    context = await builder.build(mission, max_products=max_products)
    responses = []
    for strategy in strategy_set(strategies):
        item_started = time.perf_counter()
        response = strategy.generate_response(context)
        response.runtime_ms = round((time.perf_counter() - item_started) * 1000, 3)
        responses.append(response)
        _event(
            log,
            "STRATEGY_RESPONSE_GENERATED",
            strategy=response.strategy_name,
            offer_id=str(response.offer_id) if response.offer_id else None,
        )
    selection = choose_response(
        responses, outside_option_utility=outside_option_utility
    )
    if selection.no_purchase:
        _event(log, "NO_PURCHASE", reason=selection.reason)
    else:
        _event(
            log,
            "BUYER_SELECTION_MADE",
            selected_strategy=selection.selected_strategy,
        )
    result = ArenaMissionResult(
        mission=mission,
        responses=responses,
        selection=selection,
        runtime_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    explanation = explain_selection(context, responses, selection)
    return result, {
        "context": context,
        "explanation": explanation,
        "events": log,
    }


async def run_duel(
    session: AsyncSession,
    request: ArenaDuelRequest,
    cache: ArenaCatalogueCache | None = None,
) -> dict[str, Any]:
    mission = BuyerMission(
        id=f"duel-{uuid4().hex[:8]}",
        raw_intent=request.intent,
        buyer_profile=request.buyer_profile,
        scenario_tags=["live_duel"],
        seed=request.seed,
        created_at=datetime.now(UTC),
    )
    events = _events()
    result, extra = await run_mission(
        session,
        mission,
        strategies=list(request.strategies),
        outside_option_utility=request.outside_option_utility,
        max_products=8,
        cache=cache,
        events=events,
    )
    return {
        "result": result,
        "explanation": extra["explanation"],
        "context": extra["context"],
        "events": events,
        "disclaimer": ARENA_DISCLAIMER,
    }


async def run_benchmark(
    session: AsyncSession,
    config: ArenaBenchmarkConfig,
) -> tuple[ArenaBenchmarkSummary, list[ArenaMissionResult], list[dict[str, Any]]]:
    events = _events()
    _event(
        events,
        "BENCHMARK_STARTED",
        seed=config.seed,
        mission_count=config.mission_count,
    )
    started = time.perf_counter()
    missions = generate_missions(
        config.mission_count,
        seed=config.seed,
        shares=config.segment_shares,
        profile_override=config.buyer_profile,
    )
    cache = ArenaCatalogueCache()
    await cache.load(session)
    results: list[ArenaMissionResult] = []
    per_strategy: dict[str, list[float]] = {name: [] for name in config.strategies}
    for mission in missions:
        item_started = time.perf_counter()
        result, _extra = await run_mission(
            session,
            mission,
            strategies=list(config.strategies),
            outside_option_utility=config.outside_option_utility,
            max_products=config.max_products,
            cache=cache,
        )
        results.append(result)
        elapsed = (time.perf_counter() - item_started) * 1000
        for response in result.responses:
            per_strategy.setdefault(response.strategy_name, []).append(
                response.runtime_ms
            )
        result.runtime_ms = round(elapsed, 2)
    total_ms = (time.perf_counter() - started) * 1000
    timing: dict[str, float] = {
        "total_ms": round(total_ms, 2),
        "average_mission_ms": round(total_ms / max(len(results), 1), 2),
    }
    for name, values in per_strategy.items():
        timing[f"strategy_{name}_avg_ms"] = (
            round(sum(values) / len(values), 3) if values else 0.0
        )
    summary = summarize(
        results,
        strategies=list(config.strategies),
        seed=config.seed,
        config={
            **config.model_dump(),
            "arena_version": ARENA_VERSION,
            "buyer_model_version": BUYER_MODEL_VERSION,
            "utility_version": UTILITY_VERSION,
            "strategy_set_version": STRATEGY_SET_VERSION,
            "transaction_simulation": (
                "disabled_for_bulk; offer-selection only. "
                "Merchant inventory is snapshotted and never consumed."
            ),
        },
        timing=timing,
    )
    _event(
        events,
        "BENCHMARK_COMPLETED",
        mission_count=len(results),
        total_ms=timing["total_ms"],
    )
    return summary, results, events


def hero_mission() -> BuyerMission:
    return HERO_MISSION.model_copy(deep=True)

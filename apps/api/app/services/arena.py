"""Arena orchestration. Benchmarks do not mutate merchant inventory."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena import (
    ARENA_DISCLAIMER,
    ARENA_VERSION,
    BUYER_MODEL_VERSION,
    STRATEGY_SET_VERSION,
)
from app.decision.arena.config import ArenaBenchmarkConfig, ArenaDuelRequest
from app.decision.arena.models import SegmentMetrics, StrategyMetrics
from app.decision.arena.runner import run_benchmark, run_duel
from app.models import (
    ArenaBenchmarkRun,
    ArenaRun,
    ArenaSegmentMetrics,
    ArenaStrategyMetrics,
)
from app.repositories.arena import ArenaRepository
from app.schemas.arena import (
    ArenaBenchmarkCreated,
    ArenaBenchmarkResponse,
    ArenaRunResponse,
    ArenaStrategyBlock,
    selection_to_api,
)


class ArenaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = ArenaRepository(session)

    async def duel(self, request: ArenaDuelRequest) -> ArenaRunResponse:
        payload = await run_duel(self.session, request)
        result = payload["result"]
        row = ArenaRun(
            mission_id=result.mission.id,
            buyer_profile=result.mission.buyer_profile,
            seed=result.mission.seed,
            buyer_selected_strategy=result.selection.selected_strategy,
            buyer_selected_offer_id=result.selection.selected_offer_id,
            no_purchase=result.selection.no_purchase,
            mission=result.mission.model_dump(mode="json"),
            strategy_responses=[
                item.model_dump(mode="json") for item in result.responses
            ],
            selection=result.selection.model_dump(mode="json"),
            explanation=payload["explanation"],
            events=payload["events"],
            run_metadata={
                "arena_version": ARENA_VERSION,
                "buyer_model_version": BUYER_MODEL_VERSION,
                "strategy_set_version": STRATEGY_SET_VERSION,
                "runtime_ms": result.runtime_ms,
                "merchant_objective": payload.get("merchant_objective"),
            },
        )
        await self.runs.add_run(row)
        await self.session.commit()
        await self.session.refresh(row)
        return ArenaRunResponse(
            arena_run_id=row.id,
            mission_id=row.mission_id,
            buyer_profile=row.buyer_profile,
            strategies=[
                ArenaStrategyBlock(name=item.strategy_name, response=item)
                for item in result.responses
            ],
            buyer_selection=selection_to_api(result.selection),
            explanation=payload["explanation"],
            disclaimer=ARENA_DISCLAIMER,
            created_at=row.created_at,
        )

    async def benchmark(
        self, config: ArenaBenchmarkConfig
    ) -> ArenaBenchmarkCreated:
        started = datetime.now(UTC)
        row = ArenaBenchmarkRun(
            seed=config.seed,
            mission_count=config.mission_count,
            strategy_names=list(config.strategies),
            buyer_model_version=BUYER_MODEL_VERSION,
            merchant_policy_version="policy.v1",
            started_at=started,
            completed_at=None,
            status="RUNNING",
            config={
                **config.model_dump(),
                "merchant_objective": config.merchant_objective().snapshot(),
            },
            summary={},
            events=[],
            run_metadata={"arena_version": ARENA_VERSION},
        )
        await self.runs.add_benchmark(row)
        await self.session.flush()
        summary, results, events = await run_benchmark(self.session, config)
        row.status = "COMPLETED"
        row.completed_at = datetime.now(UTC)
        row.summary = summary.model_dump(mode="json")
        row.events = events
        row.run_metadata = {
            "arena_version": ARENA_VERSION,
            "strategy_set_version": STRATEGY_SET_VERSION,
            "transaction_simulation": False,
            "state_isolation": (
                "shared catalogue snapshot; strategies never consume inventory"
            ),
        }
        for metric in summary.strategy_metrics:
            item = _strategy_row(metric)
            item.benchmark_run_id = row.id
            self.session.add(item)
        for segment in summary.segment_metrics:
            self.session.add(
                ArenaSegmentMetrics(
                    benchmark_run_id=row.id,
                    scenario_tag=segment.scenario_tag,
                    buyer_profile=segment.buyer_profile,
                    strategy_name=segment.strategy_name,
                    missions=segment.missions,
                    wins=segment.wins,
                    selection_rate=str(segment.selection_rate),
                    payload=segment.model_dump(mode="json"),
                )
            )
        if config.persist_missions:
            for result in results:
                self.session.add(
                    ArenaRun(
                        mission_id=result.mission.id,
                        buyer_profile=result.mission.buyer_profile,
                        seed=result.mission.seed,
                        buyer_selected_strategy=result.selection.selected_strategy,
                        buyer_selected_offer_id=result.selection.selected_offer_id,
                        no_purchase=result.selection.no_purchase,
                        mission=result.mission.model_dump(mode="json"),
                        strategy_responses=[
                            item.model_dump(mode="json") for item in result.responses
                        ],
                        selection=result.selection.model_dump(mode="json"),
                        explanation={},
                        events=[],
                        run_metadata={"source": "benchmark"},
                        benchmark_run_id=row.id,
                    )
                )
        await self.session.commit()
        await self.session.refresh(row)
        return ArenaBenchmarkCreated(
            benchmark_id=row.id,
            status=row.status,
            mission_count=row.mission_count,
            seed=row.seed,
            disclaimer=ARENA_DISCLAIMER,
        )

    async def get_latest_benchmark(self) -> ArenaBenchmarkResponse | None:
        row = await self.runs.latest_benchmark()
        if row is None:
            return None
        return await self.get_benchmark(row.id)

    async def get_benchmark(self, run_id: UUID) -> ArenaBenchmarkResponse | None:
        row = await self.runs.get_benchmark(run_id)
        if row is None:
            return None
        summary = row.summary or {}
        return ArenaBenchmarkResponse(
            benchmark_id=row.id,
            status=row.status,
            seed=row.seed,
            mission_count=row.mission_count,
            strategies=list(row.strategy_names),
            buyer_model_version=row.buyer_model_version,
            merchant_policy_version=row.merchant_policy_version,
            started_at=row.started_at,
            completed_at=row.completed_at,
            summary=summary,
            strategy_metrics=[
                StrategyMetrics.model_validate(item.payload)
                for item in row.strategy_metrics
            ],
            segment_metrics=[
                _segment(item.payload) for item in row.segment_metrics
            ],
            pairwise=list(summary.get("pairwise") or []),
            timing=dict(summary.get("timing") or {}),
            config=row.config,
            disclaimer=ARENA_DISCLAIMER,
        )

    async def export_benchmark(
        self, run_id: UUID, fmt: str
    ) -> tuple[str, str] | None:
        detail = await self.get_benchmark(run_id)
        if detail is None:
            return None
        if fmt == "csv":
            buffer = io.StringIO()
            writer = csv.DictWriter(
                buffer,
                fieldnames=[
                    "strategy_name",
                    "missions",
                    "wins",
                    "selection_rate",
                    "contribution_per_opportunity_cents",
                    "avg_contribution_when_selected",
                    "avg_buyer_utility",
                    "avg_intervention_cost_cents",
                    "no_offer_rate",
                    "policy_violation_rate",
                    "hard_constraint_violation_rate",
                ],
            )
            writer.writeheader()
            for row in detail.strategy_metrics:
                data = row.model_dump()
                writer.writerow({key: data.get(key) for key in writer.fieldnames})
            return buffer.getvalue(), "text/csv"
        payload = detail.model_dump(mode="json")
        payload["disclaimer"] = ARENA_DISCLAIMER
        import json

        return json.dumps(payload, indent=2), "application/json"


def _strategy_row(metric: StrategyMetrics) -> ArenaStrategyMetrics:
    return ArenaStrategyMetrics(
        strategy_name=metric.strategy_name,
        missions=metric.missions,
        wins=metric.wins,
        selection_rate=str(metric.selection_rate),
        avg_buyer_utility=(
            None if metric.avg_buyer_utility is None else str(metric.avg_buyer_utility)
        ),
        avg_contribution_when_selected=(
            None
            if metric.avg_contribution_when_selected is None
            else str(metric.avg_contribution_when_selected)
        ),
        contribution_per_opportunity=str(metric.contribution_per_opportunity_cents),
        avg_intervention_cost=(
            None
            if metric.avg_intervention_cost_cents is None
            else str(metric.avg_intervention_cost_cents)
        ),
        hard_constraint_violation_rate=str(metric.hard_constraint_violation_rate),
        policy_violation_rate=str(metric.policy_violation_rate),
        no_offer_rate=str(metric.no_offer_rate),
        transaction_completion_rate=str(metric.transaction_completion_rate),
        payload=metric.model_dump(mode="json"),
    )


def _segment(payload: dict[str, Any]) -> SegmentMetrics:
    return SegmentMetrics.model_validate(payload)

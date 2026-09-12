"""Capture Stage 8 hero duel + synthetic benchmarks for the report."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "astraos")
os.environ.setdefault("POSTGRES_PASSWORD", "astraos")
os.environ["POSTGRES_DB"] = "astraos_test"

from app.decision.arena.config import ArenaBenchmarkConfig, ArenaDuelRequest
from app.decision.arena.missions import HERO_MISSION
from app.decision.arena.runner import run_benchmark, run_duel
from app.db.session import AsyncSessionLocal


def _print_duel(payload: dict) -> None:
    result = payload["result"]
    print("=== HERO DUEL ===")
    print(f"intent: {result.mission.raw_intent}")
    print(f"profile: {result.mission.buyer_profile}")
    for item in result.responses:
        print(
            f"{item.strategy_name}: sku={item.sku} price={item.total_customer_price_cents} "
            f"delivery={item.delivery} warranty={item.warranty} util={item.buyer_utility} "
            f"contrib={item.merchant_contribution_cents} cost={item.intervention_cost_cents} "
            f"safe={item.policy_safe} hard={item.hard_constraints_satisfied} "
            f"fail={item.failure_reason}"
        )
    sel = result.selection
    print(
        f"selected={sel.selected_strategy} no_purchase={sel.no_purchase} "
        f"util={sel.simulated_utility} reason={sel.reason}"
    )
    print("explanation:", payload["explanation"]["reasons"])
    print(f"runtime_ms={result.runtime_ms}")


def _print_summary(label: str, summary) -> None:
    print(f"=== {label} ===")
    print(f"missions={summary.mission_count} seed={summary.seed}")
    print(f"no_purchase_rate={summary.no_purchase_rate}")
    print("timing", summary.timing)
    for row in summary.strategy_metrics:
        print(
            f"{row.strategy_name}: select={row.selection_rate} "
            f"wins={row.wins} util={row.avg_buyer_utility} "
            f"contrib_when={row.avg_contribution_when_selected} "
            f"per_opp={row.contribution_per_opportunity_cents} "
            f"interv={row.avg_intervention_cost_cents} "
            f"no_offer={row.no_offer_rate} hard={row.hard_constraint_violation_rate} "
            f"policy={row.policy_violation_rate}"
        )
    print("pairwise:")
    for row in summary.pairwise:
        print(
            f"  {row.left} vs {row.right}: "
            f"{row.left_wins}/{row.right_wins}/{row.no_purchase_or_other}"
        )
    hero_tags = {"budget", "urgent", "assurance", "balanced"}
    print("segments:")
    for row in summary.segment_metrics:
        if row.scenario_tag in hero_tags:
            print(
                f"  {row.scenario_tag} {row.strategy_name}: "
                f"{row.selection_rate} n={row.missions}"
            )


async def main() -> None:
    out = Path("/tmp/astraos_arena_report.json")
    async with AsyncSessionLocal() as session:
        duel = await run_duel(
            session,
            ArenaDuelRequest(
                intent=HERO_MISSION.raw_intent,
                buyer_profile="URGENT_TRAVELLER",
            ),
        )
        _print_duel(duel)
        small, _, _ = await run_benchmark(
            session, ArenaBenchmarkConfig(mission_count=100, seed=2026)
        )
        _print_summary("100 MISSIONS", small)
        large, _, _ = await run_benchmark(
            session, ArenaBenchmarkConfig(mission_count=500, seed=2026)
        )
        _print_summary("500 MISSIONS", large)
        payload = {
            "disclaimer": duel["disclaimer"],
            "hero": {
                "selection": duel["result"].selection.model_dump(mode="json"),
                "responses": [
                    item.model_dump(mode="json") for item in duel["result"].responses
                ],
                "explanation": duel["explanation"],
                "runtime_ms": duel["result"].runtime_ms,
            },
            "benchmark_100": small.model_dump(mode="json"),
            "benchmark_500": large.model_dump(mode="json"),
        }
        out.write_text(json.dumps(payload, indent=2, default=str))
        print(f"wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())

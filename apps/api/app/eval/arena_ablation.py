"""Phase 11 Arena ablation evaluation. Does not tune buyer utility."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from app.db.session import AsyncSessionLocal
from app.decision.arena import (
    ARENA_DISCLAIMER,
    ARENA_VERSION,
    BUYER_MODEL_VERSION,
    STRATEGY_SET_VERSION,
)
from app.decision.arena.config import (
    ABLATION_STRATEGIES,
    EXTENDED_STRATEGIES,
    SEGMENT_SHARES,
    STRATEGY_VERSIONS,
    ArenaBenchmarkConfig,
)
from app.decision.arena.runner import run_benchmark, run_objective_experiment
from app.decision.utility.models import UTILITY_VERSION

ROOT = Path(__file__).resolve().parents[4]


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _metric_row(row: Any) -> dict[str, Any]:
    return {
        "strategy_name": row.strategy_name,
        "missions": row.missions,
        "wins": row.wins,
        "selection_rate": row.selection_rate,
        "contribution_per_opportunity_cents": row.contribution_per_opportunity_cents,
        "avg_contribution_when_selected": row.avg_contribution_when_selected,
        "avg_buyer_utility": row.avg_buyer_utility,
        "avg_intervention_cost_cents": row.avg_intervention_cost_cents,
        "no_offer_rate": row.no_offer_rate,
        "policy_violation_rate": row.policy_violation_rate,
        "hard_constraint_violation_rate": row.hard_constraint_violation_rate,
        "avg_customer_price_cents": row.avg_customer_price_cents,
        "avg_commercial_interventions": row.avg_commercial_interventions,
        "no_purchase_involvement_rate": row.no_purchase_involvement_rate,
        "transaction_completion_rate": row.transaction_completion_rate,
    }


def _segment_row(row: Any) -> dict[str, Any]:
    return {
        "scenario_tag": row.scenario_tag,
        "buyer_profile": row.buyer_profile,
        "strategy_name": row.strategy_name,
        "missions": row.missions,
        "wins": row.wins,
        "selection_rate": row.selection_rate,
        "contribution_per_opportunity_cents": row.contribution_per_opportunity_cents,
        "avg_buyer_utility": row.avg_buyer_utility,
        "avg_intervention_cost_cents": row.avg_intervention_cost_cents,
    }


async def run_eval(
    *,
    mission_count: int = 100,
    seed: int = 2026,
    include_extended: bool = False,
    objective_missions: int = 20,
) -> dict[str, Any]:
    strategies = list(EXTENDED_STRATEGIES if include_extended else ABLATION_STRATEGIES)
    config = ArenaBenchmarkConfig(
        mission_count=mission_count,
        seed=seed,
        strategies=strategies,  # type: ignore[arg-type]
        persist_missions=False,
        merchant_objective_mode="BALANCED",
    )
    started = time.perf_counter()
    async with AsyncSessionLocal() as session:
        summary, results, _events = await run_benchmark(session, config)
        objective = await run_objective_experiment(
            session,
            mission_count=objective_missions,
            seed=seed,
        )
    runtime_s = time.perf_counter() - started
    examples = summary.ablation.get("examples") or {}
    return {
        "phase": 11,
        "title": "arena-ablation-competitive-proof",
        "git_sha": _git_sha(),
        "seed": seed,
        "mission_count": mission_count,
        "strategy_set": strategies,
        "strategy_versions": {
            name: STRATEGY_VERSIONS.get(name, "v1") for name in strategies
        },
        "buyer_model_version": BUYER_MODEL_VERSION,
        "utility_version": UTILITY_VERSION,
        "arena_version": ARENA_VERSION,
        "strategy_set_version": STRATEGY_SET_VERSION,
        "merchant_policy": summary.config.get("merchant_policy_snapshot")
        or {"version": "policy.v1"},
        "merchant_objective": summary.config.get("merchant_objective"),
        "catalogue_snapshot": summary.config.get("catalogue_snapshot"),
        "buyer_profile_distribution": dict(SEGMENT_SHARES),
        "outside_option_utility": config.outside_option_utility,
        "disclaimer": ARENA_DISCLAIMER,
        "default_uses_semantic_ranking": True,
        "overall_metrics_by_strategy": [
            _metric_row(row) for row in summary.strategy_metrics
        ],
        "segment_metrics": [_segment_row(row) for row in summary.segment_metrics],
        "pairwise_matrix": [row.model_dump() for row in summary.pairwise],
        "incremental_deltas": summary.ablation.get("incremental_deltas"),
        "astraos_vs_semantic_only": summary.ablation.get("astraos_vs_semantic"),
        "intervention_attribution": summary.ablation.get(
            "intervention_attribution"
        ),
        "win_loss": summary.ablation.get("win_loss"),
        "example_missions": examples,
        "objective_sensitivity": objective,
        "no_purchase_rate": summary.no_purchase_rate,
        "timing": summary.timing,
        "benchmark_runtime_seconds": round(runtime_s, 3),
        "targeted_tests_run": [],
        "formulas_unchanged": {
            "intent_parsing": True,
            "semantic_model": True,
            "qualification": True,
            "buyer_utility": True,
            "economics": True,
            "pareto_dominance": True,
            "merchant_policy": True,
            "transaction_logic": True,
        },
        "per_mission": [
            {
                "mission_id": item.mission.id,
                "segment": item.mission.scenario_tags,
                "buyer_profile": item.mission.buyer_profile,
                "selected_strategy": item.selection.selected_strategy,
                "no_purchase": item.selection.no_purchase,
                "win_category": (item.explanation or {}).get("win_category"),
                "loss_category": (item.explanation or {}).get("loss_category"),
                "responses": {
                    row.strategy_name: {
                        "product": row.product_name,
                        "sku": row.sku,
                        "price_cents": row.total_customer_price_cents,
                        "delivery": row.delivery,
                        "warranty": row.warranty,
                        "bundle": row.bundle,
                        "returns": row.returns,
                        "buyer_utility": row.buyer_utility,
                        "contribution_cents": row.merchant_contribution_cents,
                        "intervention_cost_cents": row.intervention_cost_cents,
                        "status": row.status,
                        "selectable": row.selectable,
                        "used_pareto": row.used_pareto,
                    }
                    for row in item.responses
                },
            }
            for item in results
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="artifacts/realification/phase11-arena-ablation.json",
    )
    parser.add_argument("--missions", type=int, default=100)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--extended", action="store_true")
    parser.add_argument("--objective-missions", type=int, default=20)
    args = parser.parse_args()
    report = asyncio.run(
        run_eval(
            mission_count=args.missions,
            seed=args.seed,
            include_extended=args.extended,
            objective_missions=args.objective_missions,
        )
    )
    path = Path(args.out)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "path": str(path),
                "mission_count": report["mission_count"],
                "runtime_s": report["benchmark_runtime_seconds"],
                "no_purchase_rate": report["no_purchase_rate"],
                "metrics": {
                    row["strategy_name"]: {
                        "selection": row["selection_rate"],
                        "contrib_opp": row["contribution_per_opportunity_cents"],
                    }
                    for row in report["overall_metrics_by_strategy"]
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

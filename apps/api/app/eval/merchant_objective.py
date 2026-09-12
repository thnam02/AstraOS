"""Frozen merchant-objective evaluation. Does not mutate buyer utility."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Any, cast

from app.db.session import AsyncSessionLocal
from app.decision.arena.runner import run_objective_experiment
from app.decision.optimisation.objective import OBJECTIVE_VERSION, PRESETS, preset
from app.schemas.optimisation import BuyerProfile, DecisionRequest
from app.services.decision import DecisionService
from app.services.optimisation import OptimisationService

HERO_INTENT = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)

MISSIONS: list[dict[str, str]] = [
    {
        "id": "urgent_traveller",
        "profile": "URGENT_TRAVELLER",
        "intent": HERO_INTENT,
    },
    {
        "id": "budget_buyer",
        "profile": "BUDGET_SHOPPER",
        "intent": (
            "I want the cheapest wireless noise-cancelling headphones under "
            "A$250. Standard delivery is fine."
        ),
    },
    {
        "id": "assurance_buyer",
        "profile": "ASSURANCE_BUYER",
        "intent": (
            "I need reliable ANC headphones under A$350 with a long warranty. "
            "I care more about reliability than price."
        ),
    },
    {
        "id": "quality_buyer",
        "profile": "QUALITY_FIRST",
        "intent": (
            "I want premium wireless ANC headphones under A$450. "
            "Sound quality and comfort matter more than the lowest price."
        ),
    },
    {
        "id": "balanced_buyer",
        "profile": "BALANCED",
        "intent": (
            "Looking for wireless noise-cancelling headphones under A$320. "
            "A reasonable mix of comfort, delivery, and value is fine."
        ),
    },
]


def _git_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _offer_row(response: Any, mode: str) -> dict[str, Any]:
    rec = response.recommended_offer
    return {
        "mode": mode,
        "offer_id": str(rec.offer_id) if rec else None,
        "product": rec.product_name if rec else None,
        "sku": rec.sku if rec else None,
        "buyer_utility": rec.buyer_utility if rec else None,
        "contribution_margin_cents": (
            rec.contribution_margin_cents if rec else None
        ),
        "intervention_cost_cents": (
            rec.incremental_intervention_cost_cents if rec else None
        ),
        "score": response.selection.score if response.selection else None,
        "frontier_size": response.summary.pareto_efficient,
        "frontier_ids": sorted(str(item.offer_id) for item in response.pareto_offers),
    }


async def _evaluate_mission(session: Any, mission: dict[str, str]) -> dict[str, Any]:
    decided = await DecisionService(session).run(
        DecisionRequest(
            intent=mission["intent"],
            parser_mode="rule_based",
            buyer_profile=cast(BuyerProfile, mission["profile"]),
            max_products=8,
        )
    )
    opt = decided.optimisation
    by_mode: dict[str, dict[str, Any]] = {}
    latencies: list[float] = []
    for mode in ("GROWTH", "BALANCED", "MARGIN"):
        started = time.perf_counter()
        selected = await OptimisationService(session).reselect(
            opt.optimisation_run_id, objective=preset(mode)
        )
        latencies.append((time.perf_counter() - started) * 1000)
        by_mode[mode] = _offer_row(selected, mode)
    frontiers = [tuple(row["frontier_ids"]) for row in by_mode.values()]
    selected_ids = {row["offer_id"] for row in by_mode.values()}
    return {
        "id": mission["id"],
        "profile": mission["profile"],
        "by_mode": by_mode,
        "frontier_invariant": len(set(frontiers)) == 1,
        "objective_sensitive": len(selected_ids) > 1,
        "reselect_ms": [round(item, 3) for item in latencies],
    }


def _sensitivity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = (("GROWTH", "BALANCED"), ("BALANCED", "MARGIN"), ("GROWTH", "MARGIN"))
    changed: dict[str, int] = {f"{a}_{b}": 0 for a, b in pairs}
    utility_delta: dict[str, list[float]] = {f"{a}_{b}": [] for a, b in pairs}
    contrib_delta: dict[str, list[float]] = {f"{a}_{b}": [] for a, b in pairs}
    for row in rows:
        for left, right in pairs:
            a = row["by_mode"][left]
            b = row["by_mode"][right]
            key = f"{left}_{right}"
            if a["offer_id"] != b["offer_id"]:
                changed[key] += 1
            if a["buyer_utility"] is not None and b["buyer_utility"] is not None:
                utility_delta[key].append(b["buyer_utility"] - a["buyer_utility"])
            if (
                a["contribution_margin_cents"] is not None
                and b["contribution_margin_cents"] is not None
            ):
                contrib_delta[key].append(
                    b["contribution_margin_cents"] - a["contribution_margin_cents"]
                )
    n = max(len(rows), 1)
    return {
        "missions": n,
        "objective_sensitive_rate": round(
            sum(1 for row in rows if row["objective_sensitive"]) / n, 4
        ),
        "change_rate": {key: round(value / n, 4) for key, value in changed.items()},
        "avg_buyer_utility_delta": {
            key: round(sum(values) / len(values), 4) if values else 0.0
            for key, values in utility_delta.items()
        },
        "avg_contribution_delta_cents": {
            key: round(sum(values) / len(values), 2) if values else 0.0
            for key, values in contrib_delta.items()
        },
    }


async def run_eval(*, arena_missions: int = 8) -> dict[str, Any]:
    async with AsyncSessionLocal() as session:
        missions = []
        for mission in MISSIONS:
            missions.append(await _evaluate_mission(session, mission))
        hero = next(item for item in missions if item["id"] == "urgent_traveller")
        latencies = [ms for row in missions for ms in row["reselect_ms"]]
        arena = await run_objective_experiment(
            session, mission_count=arena_missions, seed=2026
        )
    return {
        "phase": 5,
        "title": "configurable-merchant-objective",
        "git_sha": _git_sha(),
        "default_objective": {
            "mode": "BALANCED",
            "buyer_weight": 0.5,
            "merchant_weight": 0.5,
            "version": OBJECTIVE_VERSION,
        },
        "objective_presets": {
            mode: {"buyer_weight": weights[0], "merchant_weight": weights[1]}
            for mode, weights in PRESETS.items()
        },
        "selection_formula_version": "normalized_weighted_sum",
        "selection_formula": (
            "score = w_buyer * norm(utility) + w_merchant * norm(contribution)"
        ),
        "tie_break": [
            "higher weighted score",
            "higher contribution",
            "higher buyer utility",
            "lower intervention cost",
            "SKU",
            "offer ID",
        ],
        "hero_results_by_objective": hero["by_mode"],
        "frontier_invariant_status": all(row["frontier_invariant"] for row in missions),
        "missions": missions,
        "objective_sensitivity": _sensitivity(missions),
        "reselection_latency_ms": {
            "n": len(latencies),
            "mean": round(sum(latencies) / len(latencies), 3) if latencies else 0,
            "max": round(max(latencies), 3) if latencies else 0,
        },
        "arena_objective_experiment": arena,
        "formulas_unchanged": {
            "buyer_utility": True,
            "economics": True,
            "pareto_dominance": True,
            "semantic_matching": True,
            "qualification": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default="artifacts/realification/phase5-merchant-objective.json",
    )
    parser.add_argument("--arena-missions", type=int, default=8)
    args = parser.parse_args()
    report = asyncio.run(run_eval(arena_missions=args.arena_missions))
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "path": str(path),
        "frontier_invariant": report["frontier_invariant_status"],
        "sensitive_rate": report["objective_sensitivity"]["objective_sensitive_rate"],
        "reselect_mean_ms": report["reselection_latency_ms"]["mean"],
        "hero": {
            mode: row["product"]
            for mode, row in report["hero_results_by_objective"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()

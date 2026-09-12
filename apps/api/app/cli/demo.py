"""Run a hero demo through the public agent interface only."""

from __future__ import annotations

import argparse
import asyncio
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.gateway import AgentGatewayService
from app.agent.schemas import AgentAcceptRequest, AgentCounterRequest, AgentOfferRequest
from app.db.session import AsyncSessionLocal
from app.demo.scenarios import HERO_TRAVEL, get_scenario


class DemoInvariantError(RuntimeError):
    """Hero demo failed a required invariant."""


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise DemoInvariantError(message)


async def _run_hero(session: AsyncSession, *, accept: bool) -> dict[str, Any]:
    gateway = AgentGatewayService(session)
    scenario = HERO_TRAVEL
    offered = await gateway.request_offer(
        AgentOfferRequest(
            natural_language_intent=scenario.buyer_intent,
            buyer_profile=scenario.buyer_profile,
        )
    )
    qual = offered.qualification_summary or {}
    semantic = offered.semantic_match_summary or {}
    _check(offered.understood_intent is not None, "Intent was not understood.")
    _check(int(qual.get("eligible") or 0) >= 1, "Need at least one eligible product.")
    _check(int(semantic.get("match_count") or 0) >= 1, "Need a semantic match.")
    _check(
        int(semantic.get("offer_configurations") or 0) >= 2,
        "Need at least two commercial alternatives.",
    )
    _check(
        int(semantic.get("policy_safe") or 0) >= 1,
        "Need at least one policy-safe offer.",
    )
    _check(
        int(semantic.get("pareto_efficient") or 0) >= 1,
        "Need at least one Pareto-efficient offer.",
    )
    _check(offered.proposal is not None, "Need a merchant proposal.")
    _check(
        offered.policy_status == "POLICY_SAFE",
        "Recommended proposal must be policy-safe.",
    )
    _check(
        offered.negotiation_session_id is not None
        and offered.proposal is not None,
        "Negotiation session missing.",
    )
    _check(
        "ACCEPT" in offered.allowed_actions or "COUNTER" in offered.allowed_actions,
        "Transaction path must be available.",
    )
    countered = await gateway.counter_offer(
        AgentCounterRequest(
            session_id=offered.negotiation_session_id,
            message=scenario.scripted_counter,
        )
    )
    report: dict[str, Any] = {
        "scenario": scenario.id,
        "request_id": str(offered.request_id),
        "session_id": str(offered.negotiation_session_id),
        "proposal_id": str(offered.proposal.proposal_id) if offered.proposal else None,
        "status": offered.status,
        "qualification": qual,
        "semantic_matches": (offered.semantic_match_summary or {}).get("match_count"),
        "counter_status": countered.status,
        "counter_outcome": countered.proposal.outcome if countered.proposal else None,
        "lineage": offered.lineage,
    }
    if accept and countered.proposal is not None and countered.negotiation_session_id:
        accepted = await gateway.accept_offer(
            AgentAcceptRequest(
                session_id=countered.negotiation_session_id,
                proposal_id=countered.proposal.proposal_id,
                idempotency_key=f"demo-{uuid.uuid4()}",
            )
        )
        report["transaction_status"] = accepted.status
        report["order"] = accepted.order
        _check(
            accepted.status == "CONFIRMED",
            f"Transaction was not confirmed: {accepted.failure_codes}",
        )
    return report


async def _async_main(scenario_id: str, accept: bool) -> dict[str, Any]:
    get_scenario(scenario_id)
    async with AsyncSessionLocal() as session:
        if scenario_id != "HERO_TRAVEL":
            raise DemoInvariantError("CLI currently runs HERO_TRAVEL only.")
        return await _run_hero(session, accept=accept)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AstraOS hero demo.")
    parser.add_argument("scenario", nargs="?", default="hero")
    parser.add_argument(
        "--stop-before-accept",
        action="store_true",
        help="Stop after the counter so the LIVE page can continue.",
    )
    args = parser.parse_args()
    name = args.scenario.lower()
    scenario_id = "HERO_TRAVEL" if name in {"hero", "hero_travel"} else args.scenario
    report = asyncio.run(_async_main(scenario_id, accept=not args.stop_before_accept))
    for key, value in report.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

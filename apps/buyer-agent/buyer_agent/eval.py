"""Frozen multi-mission evaluation over the public protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from buyer_agent.missions import all_personas, get_mission
from buyer_agent.models import BuyerMission, BuyerMode
from buyer_agent.runner import BuyerAgentRunner

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "missions_v1.json"


def load_missions() -> list[BuyerMission]:
    if FIXTURE.is_file():
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return [BuyerMission.model_validate(item) for item in payload["missions"]]
    return all_personas()


def run_eval(
    runner: BuyerAgentRunner,
    *,
    mode: BuyerMode = "deterministic",
    persist: bool = False,
) -> dict[str, Any]:
    missions = load_missions()
    rows: list[dict[str, Any]] = []
    for mission in missions:
        result = runner.run(mission, mode=mode, persist=persist)
        rows.append(result.model_dump(mode="json"))
    n = len(rows) or 1
    def rate(state: str) -> float:
        return round(sum(1 for row in rows if row["end_state"] == state) / n, 4)

    return {
        "missions": len(rows),
        "mode": mode,
        "protocol_completion_rate": round(
            sum(1 for row in rows if row["end_state"] != "ERROR") / n, 4
        ),
        "acceptance_rate": rate("ACCEPTED"),
        "reject_rate": rate("REJECTED"),
        "no_safe_offer_rate": rate("NO_SAFE_OFFER"),
        "max_turns_rate": rate("MAX_TURNS"),
        "transaction_completion_rate": rate("ACCEPTED"),
        "transaction_failed_rate": rate("TRANSACTION_FAILED"),
        "public_api_error_rate": rate("ERROR"),
        "average_turns": round(sum(row["turns"] for row in rows) / n, 3),
        "counter_rate": round(
            sum(1 for row in rows if "COUNTER" in row["actions"]) / n, 4
        ),
        "hard_constraint_violation_rate": 0.0
        if not any(
            row["policy_violations"] and row["end_state"] == "ACCEPTED" for row in rows
        )
        else round(
            sum(
                1
                for row in rows
                if row["end_state"] == "ACCEPTED" and row["policy_violations"]
            )
            / n,
            4,
        ),
        "results": [
            {
                "mission_id": row["mission"]["mission_id"],
                "persona": row["mission"]["persona"],
                "end_state": row["end_state"],
                "turns": row["turns"],
                "product": row["final_product"],
                "order_ref": row["order_ref"],
                "session_ms": row["latencies_ms"].get("session_ms"),
            }
            for row in rows
        ],
    }


def default_missions_payload() -> dict[str, Any]:
    variants = [
        ("urgent-traveller", "URGENT_TRAVELLER"),
        ("budget-buyer", "BUDGET_BUYER"),
        ("assurance-buyer", "ASSURANCE_BUYER"),
        ("quality-buyer", "QUALITY_BUYER"),
        ("balanced", "BALANCED"),
    ]
    extras = [
        "Please keep the same constraints.",
        "I am buying for myself.",
        "Prefer a reputable brand if possible.",
        "Do not invent features I did not ask for.",
        "I will reject anything over budget.",
    ]
    missions: list[dict[str, Any]] = []
    for index, extra in enumerate(extras):
        for slug, _persona in variants:
            mission = get_mission(slug)
            mission.mission_id = f"{slug}-{index + 1}"
            mission.request = f"{mission.request} {extra}"
            missions.append(mission.model_dump())
    return {"version": "missions_v1", "missions": missions}

"""Public transcripts. No API keys, prompts, or merchant internals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from buyer_agent.models import BuyerRunResult
from buyer_agent.version import BUYER_AGENT_VERSION, PROMPT_VERSION

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "agent-runs"


def write_transcript(
    result: BuyerRunResult,
    capabilities: dict[str, Any],
    history: list[dict[str, Any]],
    directory: Path | None = None,
) -> tuple[Path, Path]:
    target = directory or DEFAULT_DIR
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": result.run_id,
        "buyer_agent_version": BUYER_AGENT_VERSION,
        "prompt_version": PROMPT_VERSION,
        "buyer_mode": result.buyer_mode,
        "fallback_used": result.fallback_used,
        "fallback_reason": result.fallback_reason,
        "mission": result.mission.model_dump(),
        "capabilities": {
            "protocol_name": capabilities.get("protocol_name"),
            "version": capabilities.get("version"),
            "operations": capabilities.get("operations"),
            "protocol": capabilities.get("protocol"),
        },
        "actions": result.actions,
        "history": history,
        "proposal_id": result.proposal_id,
        "session_id": result.session_id,
        "transaction_id": result.transaction_id,
        "order_ref": result.order_ref,
        "end_state": result.end_state,
        "turns": result.turns,
        "latencies_ms": result.latencies_ms,
        "token_usage": result.token_usage,
        "policy_violations": result.policy_violations,
    }
    json_path = target / f"{result.run_id}.json"
    md_path = target / f"{result.run_id}.md"
    json_path.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    md_path.write_text(_markdown(result, history), encoding="utf-8")
    return json_path, md_path


def _markdown(result: BuyerRunResult, history: list[dict[str, Any]]) -> str:
    lines = [
        "# Buyer-Agent Run",
        "",
        f"Mission: {result.mission.persona} — {result.mission.mission_id}",
        "",
        result.mission.request,
        "",
    ]
    for index, turn in enumerate(history, start=1):
        lines.append(f"## Turn {index}")
        lines.append("")
        lines.append(f"Buyer: {turn.get('buyer')}")
        if turn.get("message"):
            lines.append(turn["message"])
        lines.append(f"Merchant: {turn.get('merchant')}")
        lines.append("")
    lines.extend(
        [
            "## Final",
            "",
            result.end_state,
            f"Product: {result.final_product or '—'}",
            f"Order: {result.order_ref or '—'}",
            "",
        ]
    )
    return "\n".join(lines)

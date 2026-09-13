"""LLM buyer. Structured actions only; hard requirements stay deterministic."""

from __future__ import annotations

import json
from typing import Any, Protocol

from buyer_agent.errors import BuyerAgentError
from buyer_agent.models import BuyerDecision, BuyerMission, PublicProposal
from buyer_agent.prompts import SYSTEM_PROMPT_V1, user_payload
from buyer_agent.validator import BuyerPolicyValidator


class StructuredBuyerLLM(Protocol):
    def complete_json(self, *, system: str, user: str) -> dict[str, Any]: ...


class LLMBuyer:
    def __init__(
        self,
        client: StructuredBuyerLLM,
        validator: BuyerPolicyValidator | None = None,
    ) -> None:
        self.client = client
        self.validator = validator or BuyerPolicyValidator()

    def decide(
        self,
        mission: BuyerMission,
        proposal: PublicProposal,
        *,
        capabilities: dict[str, Any],
        history: list[dict[str, Any]],
        turns_used: int,
    ) -> BuyerDecision:
        public_proposal = {
            "status": proposal.status,
            "product": proposal.product_name,
            "sku": proposal.sku,
            "brand": proposal.brand,
            "total_cents": proposal.total_cents,
            "delivery_days": proposal.delivery_days,
            "warranty_months": proposal.warranty_months,
            "bundle": proposal.bundle_name,
            "expiry": proposal.expiry,
            "allowed_actions": proposal.allowed_actions,
            "proof": proposal.proof,
        }
        raw = self.client.complete_json(
            system=SYSTEM_PROMPT_V1,
            user=user_payload(
                mission_json=mission.model_dump_json(),
                capabilities_json=json.dumps(capabilities, default=str),
                proposal_json=json.dumps(public_proposal, default=str),
                history_json=json.dumps(history, default=str),
                turns_used=turns_used,
                max_turns=mission.max_turns,
            ),
        )
        try:
            decision = BuyerDecision.model_validate(raw)
        except Exception as exc:
            raise BuyerAgentError(
                "LLM_INVALID_ACTION",
                "Buyer LLM returned an invalid action payload.",
            ) from exc
        gated, _notes = self.validator.gate(decision, mission, proposal)
        return gated

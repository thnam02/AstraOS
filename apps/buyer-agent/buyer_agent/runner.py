"""Bounded external negotiation loop over the public protocol."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from buyer_agent.client import AstraOSAgentClient
from buyer_agent.config import BuyerAgentSettings, load_settings
from buyer_agent.deterministic import DeterministicBuyer
from buyer_agent.errors import BuyerAgentError
from buyer_agent.llm_buyer import LLMBuyer
from buyer_agent.llm_client import BuyerLLMClient
from buyer_agent.models import (
    BuyerDecision,
    BuyerMission,
    BuyerMode,
    BuyerRunResult,
    EndState,
    PublicProposal,
)
from buyer_agent.proposal import contains_private_keys, parse_proposal
from buyer_agent.transcript import write_transcript
from buyer_agent.validator import BuyerPolicyValidator
from buyer_agent.version import BUYER_AGENT_VERSION


class BuyerAgentRunner:
    def __init__(
        self,
        settings: BuyerAgentSettings | None = None,
        *,
        client: AstraOSAgentClient | None = None,
        llm: LLMBuyer | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self.client = client or AstraOSAgentClient(self.settings)
        self.validator = BuyerPolicyValidator()
        self.deterministic = DeterministicBuyer(self.validator)
        self.llm = llm
        self.owns_client = client is None

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def run(
        self,
        mission: BuyerMission,
        *,
        mode: BuyerMode | None = None,
        persist: bool = True,
    ) -> BuyerRunResult:
        mode = mode or _mode(self.settings.buyer_agent_mode)
        mission.max_turns = min(mission.max_turns, self.settings.buyer_agent_max_turns)
        run_id = str(uuid4())
        started = time.perf_counter()
        fallback_used = False
        fallback_reason = None
        notes: list[str] = []
        actions: list[str] = []
        history: list[dict[str, Any]] = []
        latencies: dict[str, float] = {}
        tokens: dict[str, int] | None = None
        policy_violations: list[str] = []
        capabilities: dict[str, Any] = {}
        proposal: PublicProposal | None = None
        end: EndState = "ERROR"
        order_ref = None
        transaction_id = None
        inspect_count = 0
        turns = 0
        try:
            cap_started = time.perf_counter()
            capabilities = self.client.capabilities()
            latencies["capabilities_ms"] = (time.perf_counter() - cap_started) * 1000
            req_started = time.perf_counter()
            offered = self.client.request_offer(
                mission.request,
                metadata={"buyer_run_id": run_id, "persona": mission.persona},
            )
            latencies["request_offer_ms"] = (time.perf_counter() - req_started) * 1000
            actions.append("REQUEST")
            history.append({"buyer": "REQUEST", "merchant": offered.get("status")})
            leak = contains_private_keys(offered)
            if leak:
                notes.append(f"public_payload_contained_private_keys:{','.join(leak)}")
            proposal = parse_proposal(offered)
            if proposal.status in {"NO_ELIGIBLE_PRODUCT", "NO_POLICY_SAFE_OFFER"}:
                end = "NO_SAFE_OFFER"
            else:
                end, turns, inspect_count, proposal, extra = self._negotiate(
                    mission,
                    proposal,
                    capabilities,
                    history,
                    actions,
                    latencies,
                    mode,
                )
                fallback_used = extra["fallback_used"]
                fallback_reason = extra["fallback_reason"]
                tokens = extra["tokens"]
                policy_violations.extend(extra["policy_violations"])
                if end == "ACCEPTED" and proposal.session_id and proposal.proposal_id:
                    acc_started = time.perf_counter()
                    accepted = self.client.accept_offer(
                        proposal.session_id,
                        proposal.proposal_id,
                        f"buyer-{run_id}",
                    )
                    latencies["accept_ms"] = (time.perf_counter() - acc_started) * 1000
                    actions.append("ACCEPT")
                    if accepted.get("status") == "CONFIRMED":
                        order = accepted.get("order") or {}
                        order_ref = order.get("order_number")
                        transaction_id = (
                            str(accepted["transaction_id"])
                            if accepted.get("transaction_id")
                            else None
                        )
                        if order_ref:
                            self.client.get_order(str(order_ref))
                        if transaction_id:
                            self.client.get_transaction(transaction_id)
                        leftover = self.validator.violations(mission, proposal)
                        policy_violations.extend(leftover)
                    else:
                        end = "TRANSACTION_FAILED"
                        notes.append(str(accepted.get("status")))
        except BuyerAgentError as exc:
            end = "ERROR"
            notes.append(f"{exc.code}:{exc.message}")
        latencies["session_ms"] = (time.perf_counter() - started) * 1000
        result = BuyerRunResult(
            run_id=run_id,
            buyer_agent_version=BUYER_AGENT_VERSION,
            buyer_mode="deterministic" if fallback_used else mode,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            mission=mission,
            end_state=end,
            turns=turns,
            inspect_count=inspect_count,
            order_ref=order_ref,
            transaction_id=transaction_id,
            proposal_id=proposal.proposal_id if proposal else None,
            session_id=proposal.session_id if proposal else None,
            final_total_cents=proposal.total_cents if proposal else None,
            final_product=proposal.product_name if proposal else None,
            latencies_ms={key: round(value, 2) for key, value in latencies.items()},
            token_usage=tokens,
            actions=actions,
            policy_violations=policy_violations,
            notes=notes,
        )
        if persist:
            write_transcript(result, capabilities, history)
        return result

    def _negotiate(
        self,
        mission: BuyerMission,
        proposal: PublicProposal,
        capabilities: dict[str, Any],
        history: list[dict[str, Any]],
        actions: list[str],
        latencies: dict[str, float],
        mode: BuyerMode,
    ) -> tuple[EndState, int, int, PublicProposal, dict[str, Any]]:
        turns = 0
        inspect_count = 0
        fallback_used = False
        fallback_reason = None
        tokens = None
        policy_violations: list[str] = []
        extra = {
            "fallback_used": False,
            "fallback_reason": None,
            "tokens": None,
            "policy_violations": policy_violations,
        }
        while True:
            decision = self._decide(
                mission,
                proposal,
                capabilities,
                history,
                turns,
                mode,
                inspected=inspect_count > 0,
            )
            if decision.get("fallback_used"):
                fallback_used = True
                fallback_reason = decision.get("fallback_reason")
                mode = "deterministic"
            tokens = decision.get("tokens") or tokens
            if decision.get("decision_ms") is not None:
                latencies["buyer_decision_ms"] = float(decision["decision_ms"])
            chosen: BuyerDecision = decision["decision"]
            gated, notes = self.validator.gate(chosen, mission, proposal)
            if chosen.action == "ACCEPT" and gated.action != "ACCEPT":
                policy_violations.extend(notes)
            if gated.action == "INSPECT":
                if proposal.proposal_id and inspect_count < 2:
                    inspect_count += 1
                    actions.append("INSPECT")
                    inspected = self.client.inspect_offer(proposal.proposal_id)
                    proposal = parse_proposal(inspected)
                    history.append({"buyer": "INSPECT", "merchant": proposal.status})
                    continue
                gated = self.deterministic.decide(
                    mission, proposal, turns_used=turns, inspected=True
                )
            if gated.action == "ACCEPT":
                extra.update(
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    tokens=tokens,
                )
                return "ACCEPTED", turns, inspect_count, proposal, extra
            if gated.action == "REJECT":
                extra.update(
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    tokens=tokens,
                )
                if proposal_expired_status(proposal):
                    return "EXPIRED", turns, inspect_count, proposal, extra
                return "REJECTED", turns, inspect_count, proposal, extra
            if turns >= mission.max_turns:
                extra.update(
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    tokens=tokens,
                )
                return "MAX_TURNS", turns, inspect_count, proposal, extra
            if not proposal.session_id:
                extra.update(
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    tokens=tokens,
                )
                return "ERROR", turns, inspect_count, proposal, extra
            counter = gated.counter
            payload = (
                counter.model_dump(exclude_none=True, exclude={"message"})
                if counter
                else None
            )
            message = counter.message if counter else gated.reason_summary
            ctr_started = time.perf_counter()
            countered = self.client.counter_offer(
                proposal.session_id, message=message, constraints=payload
            )
            latencies["counter_ms"] = (time.perf_counter() - ctr_started) * 1000
            turns += 1
            actions.append("COUNTER")
            history.append(
                {
                    "buyer": "COUNTER",
                    "message": message,
                    "merchant": countered.get("status"),
                }
            )
            proposal = parse_proposal(countered)
            if proposal.status in {"NO_ELIGIBLE_PRODUCT", "NO_POLICY_SAFE_OFFER"}:
                extra.update(
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason,
                    tokens=tokens,
                )
                return "NO_SAFE_OFFER", turns, inspect_count, proposal, extra
        raise RuntimeError("negotiation loop exited")

    def _decide(
        self,
        mission: BuyerMission,
        proposal: PublicProposal,
        capabilities: dict[str, Any],
        history: list[dict[str, Any]],
        turns: int,
        mode: BuyerMode,
        inspected: bool = True,
    ) -> dict[str, Any]:
        if mode == "llm":
            buyer = self.llm or self._live_llm()
            if buyer is None:
                return {
                    "decision": self.deterministic.decide(
                        mission,
                        proposal,
                        turns_used=turns,
                        inspected=inspected,
                    ),
                    "fallback_used": True,
                    "fallback_reason": "model_unavailable",
                }
            try:
                started = time.perf_counter()
                decision = buyer.decide(
                    mission,
                    proposal,
                    capabilities=capabilities,
                    history=history,
                    turns_used=turns,
                )
                decision_ms = (time.perf_counter() - started) * 1000
                usage = getattr(getattr(buyer, "client", None), "last_usage", None)
                return {
                    "decision": decision,
                    "tokens": usage,
                    "decision_ms": decision_ms,
                }
            except BuyerAgentError as exc:
                return {
                    "decision": self.deterministic.decide(
                        mission,
                        proposal,
                        turns_used=turns,
                        inspected=inspected,
                    ),
                    "fallback_used": True,
                    "fallback_reason": exc.code.lower(),
                }
        return {
            "decision": self.deterministic.decide(
                mission,
                proposal,
                turns_used=turns,
                inspected=inspected,
            )
        }

    def _live_llm(self) -> LLMBuyer | None:
        if not self.settings.api_key:
            return None
        return LLMBuyer(
            BuyerLLMClient(
                api_key=self.settings.api_key,
                model=self.settings.buyer_agent_model,
                base_url=self.settings.buyer_agent_llm_base_url,
                timeout_seconds=self.settings.buyer_agent_timeout,
            ),
            self.validator,
        )


def proposal_expired_status(proposal: PublicProposal) -> bool:
    from buyer_agent.proposal import proposal_expired

    return proposal_expired(proposal) or proposal.status == "EXPIRED"


def _mode(value: str) -> BuyerMode:
    return "llm" if value.strip().lower() == "llm" else "deterministic"

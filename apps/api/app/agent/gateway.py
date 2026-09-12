"""Canonical agent gateway. Calls existing services; no commercial logic."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.errors import AgentErrorCode, AgentProtocolError
from app.agent.proof import (
    claims_from_bundle,
    claims_from_match,
    claims_from_offer,
    merge_claims,
)
from app.agent.schemas import (
    AgentAcceptRequest,
    AgentCapabilities,
    AgentCounterRequest,
    AgentErrorBody,
    AgentOfferRequest,
    AgentOfferResponse,
    AgentProposalView,
    AgentTransactionResponse,
    StructuredConstraints,
)
from app.decision.intent.models import ConstraintField, ShoppingIntent
from app.decision.intent.rule_based_parser import RuleBasedIntentParser
from app.decision.negotiation.models import BuyerAction, CounterConstraints
from app.schemas.negotiation import (
    BuyerTurnRequest,
    CreateNegotiationRequest,
    NegotiationResponse,
)
from app.schemas.optimisation import PublicScoredOffer
from app.schemas.transaction import AcceptProposalRequest
from app.services.negotiation import NegotiationError, NegotiationService
from app.services.transaction import TransactionError, TransactionService

logger = logging.getLogger("astraos.agent")

CAPABILITIES = AgentCapabilities(
    operations=[
        "capabilities",
        "request_offer",
        "inspect_offer",
        "counter_offer",
        "accept_offer",
        "get_transaction",
        "get_order",
    ],
    supported=[
        "intent interpretation",
        "semantic product matching",
        "dynamic offer construction",
        "policy-safe optimisation",
        "offer negotiation",
        "transaction acceptance",
    ],
    not_supported=[
        "real payment execution",
        "physical fulfilment",
        "production conversion prediction",
    ],
    protocol=["REST", "MCP"],
    disclaimer=(
        "The agent adapter translates protocol messages onto AstraOS "
        "canonical services. It does not price, qualify, or optimise offers."
    ),
)


def _budget_cents(intent: ShoppingIntent) -> int | None:
    for item in intent.hard_constraints:
        if item.field != ConstraintField.PRICE:
            continue
        value = (
            item.normalized_value
            if item.normalized_value is not None
            else item.value
        )
        if isinstance(value, int):
            return value
    return None


def _same_day(intent: ShoppingIntent) -> bool:
    return any(
        item.field in {ConstraintField.SAME_DAY_DELIVERY, ConstraintField.DELIVERY_DAYS}
        and (
            item.normalized_value in (True, 0)
            or item.value in (True, 0)
        )
        for item in intent.hard_constraints
    )


async def _discrepancies(
    intent_text: str, structured: StructuredConstraints | None
) -> list[str]:
    if structured is None:
        return []
    parsed = await RuleBasedIntentParser().parse(intent_text)
    notes: list[str] = []
    budget = _budget_cents(parsed)
    if (
        structured.max_total_price_cents is not None
        and budget is not None
        and structured.max_total_price_cents != budget
    ):
        notes.append(
            "Structured max_total_price_cents disagrees with the natural-language "
            f"budget ({structured.max_total_price_cents} vs {budget}). "
            "Natural-language constraints are used."
        )
    if structured.same_day_required is True and not _same_day(parsed):
        notes.append(
            "Structured same_day_required is true but the natural-language "
            "intent did not require same-day delivery. Natural language is used."
        )
    return notes


def _proposal_view(session: NegotiationResponse) -> AgentProposalView | None:
    proposal = session.proposal
    if proposal is None:
        return None
    offer = proposal.offer or {}
    pricing = offer.get("pricing") or {}
    return AgentProposalView(
        proposal_id=proposal.proposal_id,
        product={
            "name": offer.get("product_name"),
            "sku": offer.get("sku"),
            "brand": offer.get("brand"),
        }
        if offer
        else None,
        pricing=_public_pricing(pricing) or None,
        delivery=offer.get("delivery"),
        warranty=offer.get("warranty"),
        bundle=offer.get("bundle"),
        returns=offer.get("returns"),
        total={
            "amount_cents": pricing.get("total_price_cents"),
            "currency": pricing.get("currency") or "AUD",
        }
        if pricing
        else None,
        expiry=proposal.expires_at,
        outcome=proposal.outcome,
    )


def _status_from_session(session: NegotiationResponse) -> str:
    if session.proposal is None:
        if session.match and session.match.qualification.eligible == 0:
            return "NO_ELIGIBLE_PRODUCT"
        return "NO_POLICY_SAFE_OFFER"
    outcome = session.proposal.outcome
    if outcome == "DECLINE":
        return "DECLINED"
    if outcome == "CLARIFICATION_REQUIRED":
        return "CLARIFICATION_REQUIRED"
    if outcome in {"COUNTEROFFER", "ALTERNATIVE_PRODUCT", "ACCEPT_BUYER_COUNTER"}:
        if session.turns and session.turns[-1].structured_action == "COUNTER":
            return "COUNTERED"
        return "PROPOSED"
    return "PROPOSED"


def _from_session(
    session: NegotiationResponse,
    *,
    request_id: UUID,
    discrepancies: list[str] | None = None,
    started: float,
) -> AgentOfferResponse:
    rec: PublicScoredOffer | None = (
        session.optimisation.recommended_offer if session.optimisation else None
    )
    offer_payload = session.proposal.offer if session.proposal else None
    status = _status_from_session(session)
    error = None
    if status == "NO_ELIGIBLE_PRODUCT":
        error = AgentErrorBody(
            error_code=AgentErrorCode.NO_ELIGIBLE_PRODUCT.value,
            machine_message="No catalogue product satisfies the hard constraints.",
            allowed_next_actions=["REQUEST"],
        )
    elif status == "NO_POLICY_SAFE_OFFER":
        error = AgentErrorBody(
            error_code=AgentErrorCode.NO_POLICY_SAFE_OFFER.value,
            machine_message="No constructed offer clears current merchant policy.",
            allowed_next_actions=["REQUEST"],
        )
    match = session.match
    construction = session.construction
    optimisation = session.optimisation
    understood = (
        match.intent.model_dump(mode="json")
        if match
        else session.original_intent
    )
    timing = {
        "total_ms": round((time.perf_counter() - started) * 1000, 2),
        "intent_ms": match.timing.intent_parse_ms if match else 0,
        "qualification_ms": match.timing.qualification_ms if match else 0,
        "semantic_match_ms": (
            match.timing.embedding_ms + match.timing.rerank_ms if match else 0
        ),
        "offer_construction_ms": construction.timing.total_ms if construction else 0,
        "optimisation_ms": (
            optimisation.timing.total_optimisation_ms if optimisation else 0
        ),
        "negotiation_ms": session.timing.total_turn_ms if session.timing else 0,
    }
    return AgentOfferResponse(
        request_id=request_id,
        decision_id=optimisation.optimisation_run_id if optimisation else None,
        negotiation_session_id=session.session_id,
        status=status,
        understood_intent=understood,
        qualification_summary=match.qualification.model_dump() if match else None,
        semantic_match_summary=(
            {
                "match_count": len(match.semantic_matching.matches),
                "top_sku": (
                    match.semantic_matching.matches[0].sku
                    if match.semantic_matching.matches
                    else None
                ),
                "variants_checked": match.qualification.variants_checked,
                "eligible": match.qualification.eligible,
                "offer_configurations": (
                    construction.summary.generated_candidates if construction else 0
                ),
                "policy_safe": optimisation.summary.policy_safe if optimisation else 0,
                "pareto_efficient": (
                    optimisation.summary.pareto_efficient if optimisation else 0
                ),
            }
            if match
            else None
        ),
        proposal=_proposal_view(session),
        merchant_reasoning=_public_reasoning(
            list(session.proposal.explanation) if session.proposal else []
        ),
        proof=merge_claims(
            claims_from_bundle(
                (offer_payload or {}).get("proof_bundle") if offer_payload else None
            ),
            claims_from_match(match),
            claims_from_offer(rec or offer_payload),
        ),
        policy_status="POLICY_SAFE" if session.proposal and offer_payload else status,
        allowed_actions=list(session.proposal.next_allowed_actions)
        if session.proposal
        else ["REQUEST"],
        constraint_discrepancies=discrepancies or [],
        lineage={
            "match_run_id": str(match.run_id) if match else None,
            "offer_run_id": str(construction.offer_run_id) if construction else None,
            "optimisation_run_id": (
                str(optimisation.optimisation_run_id) if optimisation else None
            ),
            "negotiation_session_id": str(session.session_id),
            "proposal_id": str(session.proposal.proposal_id)
            if session.proposal
            else None,
        },
        timing=timing,
        error=error,
    )


def _public_pricing(pricing: dict[str, Any] | None) -> dict[str, Any]:
    """Customer-facing money only. Never COGS or margin."""
    if not pricing:
        return {}
    return {
        "product_price_cents": pricing.get("product_price_cents"),
        "total_price_cents": pricing.get("total_price_cents"),
        "currency": pricing.get("currency") or "AUD",
    }


_PRIVATE_REASON_MARKERS = (
    "margin floor",
    "contribution rate",
    "contribution than",
    "merchant contribution",
    "cogs",
    "pareto",
    "merchant's",
    "merchant objective",
    "merchant strategy",
    "commercial objective",
    "buyer fit /",
    "contribution preservation",
    "buyer_weight",
    "merchant_weight",
)


def _public_reasoning(lines: list[str]) -> list[str]:
    """Buyer-visible reasons. Merchant economics stay private."""
    kept: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(marker in lowered for marker in _PRIVATE_REASON_MARKERS):
            continue
        kept.append(line)
    return kept


async def _public_session(
    db: AsyncSession,
    session: NegotiationResponse,
    *,
    request_id: UUID,
    started: float,
    discrepancies: list[str] | None = None,
) -> AgentOfferResponse:
    return _from_session(
        session,
        request_id=request_id,
        discrepancies=discrepancies,
        started=started,
    )


class AgentGatewayService:
    """External Buyer Agent entry. Delegates to Stage 2–7 services."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.negotiations = NegotiationService(session)
        self.transactions = TransactionService(session)

    def capabilities(self) -> AgentCapabilities:
        return CAPABILITIES

    async def request_offer(self, payload: AgentOfferRequest) -> AgentOfferResponse:
        started = time.perf_counter()
        request_id = payload.request_id or uuid4()
        text = payload.natural_language_intent.strip()
        if len(text) < 8:
            raise AgentProtocolError(
                AgentErrorCode.INVALID_INTENT,
                "Intent text is too short to interpret.",
                allowed_next_actions=["REQUEST"],
            )
        discrepancies = await _discrepancies(text, payload.structured_constraints)
        logger.info(
            "agent_request_offer request_id=%s buyer_agent=%s",
            request_id,
            payload.buyer_agent_id,
        )
        session = await self.negotiations.create(
            CreateNegotiationRequest(
                intent=text,
                buyer_profile=payload.buyer_profile,
                buyer_agent_type="MANUAL",
            )
        )
        return await _public_session(
            self.session,
            session,
            request_id=request_id,
            discrepancies=discrepancies,
            started=started,
        )

    async def inspect_offer(
        self, proposal_id: UUID, *, request_id: UUID | None = None
    ) -> AgentOfferResponse:
        started = time.perf_counter()
        rid = request_id or uuid4()
        session = await self._session_for_proposal(proposal_id)
        return await _public_session(
            self.session, session, request_id=rid, started=started
        )

    async def counter_offer(self, payload: AgentCounterRequest) -> AgentOfferResponse:
        started = time.perf_counter()
        request_id = uuid4()
        if not payload.message and payload.constraints is None:
            raise AgentProtocolError(
                AgentErrorCode.INVALID_INTENT,
                "Counter requires a message or structured constraints.",
            )
        try:
            session = await self.negotiations.turn(
                payload.session_id,
                BuyerTurnRequest(
                    message=payload.message,
                    action=BuyerAction.COUNTER if payload.constraints else None,
                    constraints=payload.constraints or CounterConstraints(),
                ),
            )
        except NegotiationError as exc:
            raise AgentProtocolError(
                AgentErrorCode.INVALID_SESSION_STATE,
                str(exc),
                http_status=409,
                allowed_next_actions=["INSPECT", "REQUEST"],
            ) from exc
        return await _public_session(
            self.session, session, request_id=request_id, started=started
        )

    async def accept_offer(
        self, payload: AgentAcceptRequest
    ) -> AgentTransactionResponse:
        request_id = uuid4()
        try:
            result = await self.transactions.accept(
                payload.session_id,
                AcceptProposalRequest(
                    proposal_id=payload.proposal_id,
                    idempotency_key=payload.idempotency_key,
                    quantity=payload.quantity,
                ),
            )
        except TransactionError as exc:
            code = AgentErrorCode.TRANSACTION_REVALIDATION_FAILED
            if exc.code.value.endswith("NOT_FOUND"):
                code = AgentErrorCode.PROPOSAL_NOT_FOUND
            raise AgentProtocolError(
                code,
                exc.code.value,
                http_status=409,
                allowed_next_actions=["REQUEST", "INSPECT"],
            ) from exc
        status = (
            "CONFIRMED" if result.state == "CONFIRMED" else "REVALIDATION_FAILED"
        )
        error = None
        if result.state != "CONFIRMED":
            error = AgentErrorBody(
                error_code=AgentErrorCode.TRANSACTION_REVALIDATION_FAILED.value,
                machine_message="Live merchant state rejected the accepted proposal.",
                human_debug_message=",".join(result.failure_codes) or result.state,
                allowed_next_actions=result.next_actions or ["REQUEST"],
            )
        return AgentTransactionResponse(
            request_id=request_id,
            status=status,
            transaction_id=result.transaction_id,
            order=result.order.model_dump(mode="json") if result.order else None,
            revalidation=result.revalidation.model_dump(mode="json")
            if result.revalidation
            else None,
            failure_codes=result.failure_codes,
            next_actions=result.next_actions,
            lineage=result.lineage,
            timing=result.timing.model_dump() if result.timing else {},
            error=error,
        )

    async def get_order(self, ref: str) -> dict[str, Any]:
        if ref.startswith("AST-"):
            order = await self.transactions.get_order_by_number(ref)
        else:
            try:
                order = await self.transactions.get_order(UUID(ref))
            except ValueError as exc:
                raise AgentProtocolError(
                    AgentErrorCode.ORDER_NOT_FOUND,
                    "Order reference is not a valid id or order number.",
                    http_status=404,
                    allowed_next_actions=["REQUEST"],
                ) from exc
        if order is None:
            raise AgentProtocolError(
                AgentErrorCode.ORDER_NOT_FOUND,
                "Order not found.",
                http_status=404,
                allowed_next_actions=["REQUEST"],
            )
        return order.model_dump(mode="json")

    async def get_transaction(self, transaction_id: UUID) -> dict[str, Any]:
        detail = await self.transactions.get(transaction_id)
        if detail is None:
            raise AgentProtocolError(
                AgentErrorCode.PROPOSAL_NOT_FOUND,
                "Transaction not found.",
                http_status=404,
            )
        return detail.model_dump(mode="json")

    async def _session_for_proposal(self, proposal_id: UUID) -> NegotiationResponse:
        from sqlalchemy import select

        from app.models.negotiation import MerchantProposal

        result = await self.session.execute(
            select(MerchantProposal).where(MerchantProposal.id == proposal_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AgentProtocolError(
                AgentErrorCode.PROPOSAL_NOT_FOUND,
                "Proposal not found.",
                http_status=404,
                allowed_next_actions=["REQUEST"],
            )
        session = await self.negotiations.get(row.session_id)
        if session is None:
            raise AgentProtocolError(
                AgentErrorCode.INVALID_SESSION_STATE,
                "Negotiation session not found for proposal.",
                http_status=404,
            )
        return session

"""Merchant-side negotiation. Reuses Stages 2–5. Never invents a deal."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.decision.intent.models import ConstraintField, ShoppingIntent
from app.decision.intent.price import max_customer_total_cents
from app.decision.negotiation.delta import (
    apply_working_intent,
    delta_from_turn,
    merged_constraints,
)
from app.decision.negotiation.explanation import explain, next_actions
from app.decision.negotiation.interpreter import RuleBasedNegotiationInterpreter
from app.decision.negotiation.llm_interpreter import LLMNegotiationInterpreter
from app.decision.negotiation.models import (
    Actor,
    BuyerAction,
    BuyerTurnInput,
    CounterConstraints,
    MerchantAction,
    MerchantOutcome,
    MerchantProposalDTO,
    NegotiationDelta,
    ProposalType,
    ReasonCode,
)
from app.decision.negotiation.search import search_counter
from app.decision.negotiation.simulator import simulate_buyer
from app.decision.negotiation.state_machine import NegotiationState as State
from app.decision.negotiation.state_machine import buyer_may_act, transition
from app.decision.optimisation.models import EngineResult, ScoredOffer
from app.decision.optimisation.objective import (
    MerchantObjectiveConfig,
    from_snapshot,
)
from app.decision.proof.compiler import attach_proof_bundle
from app.models.negotiation import (
    MerchantProposal,
    NegotiationSession,
    NegotiationTurn,
)
from app.repositories.negotiation import NegotiationRepository
from app.repositories.policy import MerchantPolicyRepository
from app.repositories.product import ProductRepository
from app.schemas.negotiation import (
    BuyerTurnRequest,
    CommercialState,
    CreateNegotiationRequest,
    NegotiationResponse,
    NegotiationTiming,
    NegotiationTurnView,
    SimulateBuyerRequest,
)
from app.schemas.optimisation import (
    DecisionRequest,
    to_public_scored,
)
from app.services.decision import DecisionService
from app.services.matching import SemanticMatchingService
from app.services.objective import MerchantObjectiveService
from app.services.offers import OfferConstructionService
from app.services.optimisation import OptimisationService

logger = logging.getLogger("astraos.negotiation")


class NegotiationError(ValueError):
    """Invalid session or disallowed turn."""


class NegotiationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rows = NegotiationRepository(session)
        self.policy = MerchantPolicyRepository(session)
        self.products = ProductRepository(session)
        self.decision = DecisionService(session)
        self.matching = SemanticMatchingService(session)
        self.offers = OfferConstructionService(session)
        self.optimisation = OptimisationService(session)
        self.rule_interpreter = RuleBasedNegotiationInterpreter()
        self.llm_interpreter = LLMNegotiationInterpreter()

    async def create(
        self, payload: CreateNegotiationRequest
    ) -> NegotiationResponse:
        decided = await self.decision.run(
            DecisionRequest(
                intent=payload.intent,
                parser_mode=payload.parser_mode,
                buyer_profile=payload.buyer_profile,
                max_products=payload.max_products,
            )
        )
        policy = await self.policy.get_active()
        if policy is None:
            raise RuntimeError("No active merchant policy.")
        intent = decided.match.intent
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=settings.negotiation_ttl_seconds)
        rec = decided.optimisation.recommended_offer
        objective = await MerchantObjectiveService(self.session).active_config()
        opening_state = (
            State.MERCHANT_PROPOSAL_CREATED
            if rec is not None
            else State.NO_POLICY_SAFE_COUNTER
        )
        row = NegotiationSession(
            initial_intent_run_id=decided.match.run_id,
            match_run_id=decided.match.run_id,
            offer_run_id=decided.construction.offer_run_id,
            optimisation_run_id=decided.optimisation.optimisation_run_id,
            current_offer_id=rec.offer_id if rec else None,
            current_state=State.CREATED.value,
            buyer_agent_type=payload.buyer_agent_type,
            buyer_profile=payload.buyer_profile,
            merchant_policy_version=str(policy.id),
            original_intent=intent.model_dump(mode="json"),
            working_intent=intent.model_dump(mode="json"),
            delta_history=[],
            events=[],
            raw_intent=payload.intent,
            turn_count=0,
            max_turns=settings.max_negotiation_turns,
            expires_at=expires,
            session_metadata={
                "policy_snapshot": {
                    "minimum_margin_rate": str(policy.minimum_margin_rate),
                    "maximum_discount_rate": str(policy.maximum_discount_rate),
                    "policy_id": str(policy.id),
                },
                "merchant_objective": objective.snapshot(),
                "objective_binding": "snapshot_at_session_creation",
            },
        )
        row.turns = []
        row.proposals = []
        await self.rows.add_session(row)
        row.current_state = State.BUYER_REQUEST_RECEIVED.value
        self._event(row, "NEGOTIATION_CREATED")
        self._event(row, "BUYER_REQUEST_RECEIVED")
        buyer_turn = self._turn(
            row,
            actor=Actor.BUYER_AGENT,
            action=BuyerAction.REQUEST.value,
            message=payload.intent,
            payload={"buyer_profile": payload.buyer_profile},
        )
        self.session.add(buyer_turn)
        proposal = self._proposal_row(
            row,
            version=1,
            proposal_type=ProposalType.INITIAL,
            outcome=(
                MerchantOutcome.COUNTEROFFER
                if rec is None
                else MerchantOutcome.ACCEPT_BUYER_COUNTER
            ),
            offer_id=rec.offer_id if rec else None,
            snapshot=_snapshot_with_proof(rec, decided.match),
            codes=(
                [ReasonCode.ORIGINAL_CONSTRAINTS_RETAINED.value]
                if rec
                else [
                    (
                        decided.optimisation.failure.code
                        if decided.optimisation.failure
                        else ReasonCode.NO_COMPLIANT_OFFER.value
                    )
                ]
            ),
            explanation=(
                decided.optimisation.explanation
                if rec
                else [
                    decided.optimisation.failure.message
                    if decided.optimisation.failure
                    else (
                        "No complete offer satisfies the buyer's "
                        "mandatory constraints."
                    )
                ]
            ),
            next_acts=["ACCEPT", "REJECT", "COUNTER"] if rec else ["COUNTER", "REJECT"],
            expires=expires,
        )
        # Fix outcome for initial: use a dedicated initial outcome via type INITIAL
        proposal.outcome = (
            MerchantOutcome.ACCEPT_BUYER_COUNTER.value
            if rec
            else MerchantOutcome.DECLINE.value
        )
        if rec is None:
            proposal.outcome = MerchantOutcome.DECLINE.value
        else:
            proposal.outcome = "INITIAL"
        self.session.add(proposal)
        await self.session.flush()
        row.current_proposal_id = proposal.id
        row.current_state = opening_state.value
        self._event(row, "PROPOSAL_GENERATED")
        merchant_turn = self._turn(
            row,
            actor=Actor.MERCHANT_AGENT,
            action=MerchantAction.PROPOSE.value,
            message=None,
            payload={"proposal_id": str(proposal.id)},
            offer_id=rec.offer_id if rec else None,
            proposal_id=proposal.id,
        )
        self.session.add(merchant_turn)
        await self.session.commit()
        await self.session.refresh(row)
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        return await self._response(
            loaded,
            match=decided.match,
            construction=decided.construction,
            optimisation=decided.optimisation,
        )

    async def get(self, session_id: uuid.UUID) -> NegotiationResponse | None:
        row = await self.rows.get(session_id)
        if row is None:
            return None
        return await self._response(row)

    async def recover_after_failure(
        self,
        session_id: uuid.UUID,
        *,
        failure_codes: list[str],
    ) -> MerchantProposalDTO | None:
        """Create a NEW proposal after a failed execution. Never mutates the old one."""
        row = await self.rows.get(session_id)
        if row is None:
            return None
        if State(row.current_state) != State.READY_FOR_CHECKOUT:
            current = self._current_proposal(row)
            return self._to_dto(row, current) if current else None

        working = ShoppingIntent.model_validate(row.working_intent)
        matched = await self.matching.match_from_intent(working, limit=8)
        row.match_run_id = matched.run_id
        construction = await self.offers.generate(
            intent_text=None,
            match_run_id=matched.run_id,
            max_products=8,
            preview_status="FEASIBLE",
            preview_limit=40,
            intent_override=working,
        )
        objective = self._session_objective(row)
        response, engine = await self.optimisation.evaluate(
            construction.offer_run_id,
            buyer_profile=row.buyer_profile,
            objective=objective,
        )
        assert isinstance(engine, EngineResult)
        row.offer_run_id = construction.offer_run_id
        row.optimisation_run_id = response.optimisation_run_id
        current = self._current_proposal(row)
        current_variant = None
        if current and current.offer_snapshot:
            current_variant = uuid.UUID(current.offer_snapshot["variant_id"])
        found = search_counter(
            engine.scored,
            request=CounterConstraints(alternative_product_allowed=True),
            current_variant_id=current_variant,
            objective=objective,
        )
        if found.offer is None:
            return None
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=settings.negotiation_ttl_seconds)
        version = max((item.version for item in row.proposals), default=0) + 1
        snapshot = attach_proof_bundle(
            to_public_scored(found.offer).model_dump(mode="json")
        )
        codes = [item.value for item in found.reason_codes]
        codes.insert(0, "RECOVERY_AFTER_REVALIDATION_FAILURE")
        explanation = [
            "The accepted proposal could not be executed against live merchant state.",
            f"Failure: {', '.join(failure_codes) or 'REVALIDATION_FAILED'}.",
            "A new policy-safe proposal was generated. "
            "The original offer was not changed.",
            f"Recovery offer: {found.offer.product_name}.",
        ]
        proposal = self._proposal_row(
            row,
            version=version,
            proposal_type=found.proposal_type,
            outcome=found.outcome,
            offer_id=found.offer.offer_id,
            snapshot=snapshot,
            codes=codes,
            explanation=explanation,
            next_acts=["ACCEPT", "REJECT", "COUNTER"],
            expires=expires,
            compromise=(found.compromise.model_dump() if found.compromise else None),
            optimisation_run_id=response.optimisation_run_id,
        )
        self.session.add(proposal)
        await self.session.flush()
        row.current_proposal_id = proposal.id
        row.current_offer_id = found.offer.offer_id
        row.expires_at = expires
        row.current_state = transition(
            State.READY_FOR_CHECKOUT, State.MERCHANT_PROPOSAL_CREATED
        ).value
        self._event(row, "RECOVERY_PROPOSAL_GENERATED")
        self.session.add(
            self._turn(
                row,
                actor=Actor.MERCHANT_AGENT,
                action=MerchantAction.PROPOSE.value,
                message=None,
                payload={
                    "recovery": True,
                    "failure_codes": failure_codes,
                    "proposal_id": str(proposal.id),
                },
                offer_id=found.offer.offer_id,
                proposal_id=proposal.id,
            )
        )
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        created = next(item for item in loaded.proposals if item.id == proposal.id)
        return self._to_dto(loaded, created)

    async def turn(
        self,
        session_id: uuid.UUID,
        payload: BuyerTurnRequest,
    ) -> NegotiationResponse:
        started = time.perf_counter()
        row = await self.rows.get(session_id)
        if row is None:
            raise NegotiationError("Negotiation session not found")
        state = State(row.current_state)
        if not buyer_may_act(state):
            raise NegotiationError(f"Session is {state.value}")
        if row.turn_count >= row.max_turns:
            return await self._close_limit(row, started)

        now = datetime.now(UTC)
        expired = row.expires_at is not None and now > row.expires_at
        interpret_started = time.perf_counter()
        interpreter = (
            self.llm_interpreter
            if payload.interpreter == "llm"
            else self.rule_interpreter
        )
        interpreted = interpreter.interpret(
            BuyerTurnInput(
                action=payload.action,
                constraints=payload.constraints,
                message=payload.message,
            )
        )
        interpret_ms = (time.perf_counter() - interpret_started) * 1000

        if expired and interpreted.action == BuyerAction.ACCEPT:
            return await self._expired_refresh(row, interpreted, started, interpret_ms)

        row.turn_count += 1
        buyer_turn = self._turn(
            row,
            actor=Actor.BUYER_AGENT,
            action=interpreted.action.value,
            message=interpreted.raw_message,
            payload=interpreted.model_dump(mode="json"),
        )
        self.session.add(buyer_turn)

        if interpreted.action == BuyerAction.ACCEPT:
            return await self._accept(row, started, interpret_ms)
        if interpreted.action == BuyerAction.REJECT:
            return await self._reject(row, started, interpret_ms)
        if interpreted.action == BuyerAction.ASK_CLARIFICATION:
            return await self._clarify(
                row, interpreted, started, interpret_ms
            )
        return await self._counter(
            row, interpreted, started, interpret_ms, expired=expired
        )

    async def simulate(
        self,
        session_id: uuid.UUID,
        payload: SimulateBuyerRequest,
    ) -> NegotiationResponse:
        row = await self.rows.get(session_id)
        if row is None:
            raise NegotiationError("Negotiation session not found")
        current = self._current_proposal(row)
        offer = current.offer_snapshot if current else None
        if not offer:
            raise NegotiationError("No proposal to evaluate")
        budget = _intent_budget(ShoppingIntent.model_validate(row.original_intent))
        decision = simulate_buyer(
            mode=payload.mode,
            budget_cents=budget,
            offer_price_cents=int(offer["pricing"]["total_price_cents"]),
            delivery_days=int(offer["delivery"]["days"]),
            warranty_months=int(offer["warranty"]["months"]),
            buyer_utility=float(offer["buyer_utility"]),
        )
        return await self.turn(
            session_id,
            BuyerTurnRequest(
                message=decision.message,
                action=decision.action,
                constraints=decision.constraints,
            ),
        )

    async def _counter(
        self,
        row: NegotiationSession,
        interpreted: Any,
        started: float,
        interpret_ms: float,
        *,
        expired: bool,
    ) -> NegotiationResponse:
        row.current_state = transition(
            State(row.current_state), State.BUYER_COUNTERED
        ).value
        self._event(row, "BUYER_COUNTERED")
        delta_started = time.perf_counter()
        delta = delta_from_turn(interpreted)
        history = list(row.delta_history)
        history.append(delta.model_dump(mode="json"))
        row.delta_history = history
        original = ShoppingIntent.model_validate(row.original_intent)
        deltas = [NegotiationDelta.model_validate(item) for item in history]
        working = apply_working_intent(original, deltas)
        row.working_intent = working.model_dump(mode="json")
        request = merged_constraints(deltas)
        if request.max_total_price_cents is None:
            request.max_total_price_cents = max_customer_total_cents(working)
        delta_ms = (time.perf_counter() - delta_started) * 1000

        reopt_started = time.perf_counter()
        match_run_id = row.match_run_id
        if delta.rematch_required:
            matched = await self.matching.match_from_intent(working, limit=8)
            match_run_id = matched.run_id
            row.match_run_id = match_run_id
        construction = await self.offers.generate(
            intent_text=None,
            match_run_id=match_run_id,
            max_products=8,
            preview_status="FEASIBLE",
            preview_limit=40,
            intent_override=working,
        )
        objective = self._session_objective(row)
        response, engine = await self.optimisation.evaluate(
            construction.offer_run_id,
            buyer_profile=row.buyer_profile,
            objective=objective,
        )
        assert isinstance(engine, EngineResult)
        row.offer_run_id = construction.offer_run_id
        row.optimisation_run_id = response.optimisation_run_id
        reopt_ms = (time.perf_counter() - reopt_started) * 1000

        current = self._current_proposal(row)
        current_variant = None
        previous_scored = None
        if current and current.offer_snapshot:
            current_variant = uuid.UUID(current.offer_snapshot["variant_id"])
            previous_scored = _scored_from_public(current.offer_snapshot, engine)

        found = search_counter(
            engine.scored,
            request=request,
            current_variant_id=current_variant,
            objective=objective,
        )
        policy = await self.policy.get_active()
        margin = policy.minimum_margin_rate if policy else Decimal("0.15")
        codes = list(found.reason_codes)
        if interpreted.prompt_injection:
            codes.insert(0, ReasonCode.PROMPT_INJECTION_IGNORED)
        if expired:
            codes.insert(0, ReasonCode.PROPOSAL_EXPIRED)
        explanation = explain(
            outcome=found.outcome,
            codes=codes,
            request=request,
            offer=found.offer,
            previous=previous_scored,
            margin_floor=Decimal(str(margin)),
            prompt_injection=interpreted.prompt_injection,
        )
        prop_started = time.perf_counter()
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=settings.negotiation_ttl_seconds)
        version = max((item.version for item in row.proposals), default=0) + 1
        snapshot = (
            attach_proof_bundle(to_public_scored(found.offer).model_dump(mode="json"))
            if found.offer
            else None
        )
        proposal = self._proposal_row(
            row,
            version=version,
            proposal_type=found.proposal_type,
            outcome=found.outcome,
            offer_id=found.offer.offer_id if found.offer else None,
            snapshot=snapshot,
            codes=[item.value for item in codes],
            explanation=explanation,
            next_acts=next_actions(found.outcome),
            expires=expires,
            compromise=(
                found.compromise.model_dump() if found.compromise else None
            ),
            optimisation_run_id=response.optimisation_run_id,
        )
        self.session.add(proposal)
        await self.session.flush()
        row.current_proposal_id = proposal.id
        row.current_offer_id = found.offer.offer_id if found.offer else None
        row.expires_at = expires
        next_state = (
            State.NO_POLICY_SAFE_COUNTER
            if found.outcome == MerchantOutcome.DECLINE
            else State.MERCHANT_COUNTER_CREATED
        )
        row.current_state = transition(State.BUYER_COUNTERED, next_state).value
        event = (
            "NO_POLICY_SAFE_RESPONSE"
            if found.outcome == MerchantOutcome.DECLINE
            else "MERCHANT_COUNTERED"
        )
        self._event(row, event)
        self.session.add(
            self._turn(
                row,
                actor=Actor.MERCHANT_AGENT,
                action=(
                    MerchantAction.DECLINE.value
                    if found.outcome == MerchantOutcome.DECLINE
                    else MerchantAction.COUNTER.value
                ),
                message=None,
                payload={
                    "outcome": found.outcome.value,
                    "reason_codes": [item.value for item in codes],
                },
                offer_id=found.offer.offer_id if found.offer else None,
                proposal_id=proposal.id,
            )
        )
        prop_ms = (time.perf_counter() - prop_started) * 1000
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        timing = NegotiationTiming(
            message_interpretation_ms=round(interpret_ms, 2),
            delta_application_ms=round(delta_ms, 2),
            reoptimisation_ms=round(reopt_ms, 2),
            proposal_generation_ms=round(prop_ms, 2),
            total_turn_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return await self._response(loaded, timing=timing)

    async def _accept(
        self, row: NegotiationSession, started: float, interpret_ms: float
    ) -> NegotiationResponse:
        row.current_state = transition(
            State(row.current_state), State.BUYER_ACCEPTED
        ).value
        self._event(row, "BUYER_ACCEPTED")
        row.current_state = transition(
            State.BUYER_ACCEPTED, State.READY_FOR_CHECKOUT
        ).value
        self.session.add(
            self._turn(
                row,
                actor=Actor.MERCHANT_AGENT,
                action=MerchantAction.READY_FOR_CHECKOUT.value,
                message=None,
                payload={"reason_codes": [ReasonCode.BUYER_ACCEPTED.value]},
                offer_id=row.current_offer_id,
                proposal_id=row.current_proposal_id,
            )
        )
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        return await self._response(
            loaded,
            timing=NegotiationTiming(
                message_interpretation_ms=round(interpret_ms, 2),
                total_turn_ms=round((time.perf_counter() - started) * 1000, 2),
            ),
        )

    async def _reject(
        self, row: NegotiationSession, started: float, interpret_ms: float
    ) -> NegotiationResponse:
        row.current_state = transition(
            State(row.current_state), State.BUYER_REJECTED
        ).value
        self._event(row, "BUYER_REJECTED")
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        return await self._response(
            loaded,
            timing=NegotiationTiming(
                message_interpretation_ms=round(interpret_ms, 2),
                total_turn_ms=round((time.perf_counter() - started) * 1000, 2),
            ),
        )

    async def _clarify(
        self,
        row: NegotiationSession,
        interpreted: Any,
        started: float,
        interpret_ms: float,
    ) -> NegotiationResponse:
        codes = [ReasonCode.AMBIGUOUS_REQUEST]
        if interpreted.prompt_injection:
            codes.insert(0, ReasonCode.PROMPT_INJECTION_IGNORED)
            codes.append(ReasonCode.UNSUPPORTED_INSTRUCTION)
        self.session.add(
            self._turn(
                row,
                actor=Actor.MERCHANT_AGENT,
                action=MerchantAction.CLARIFY.value,
                message=None,
                payload={
                    "outcome": MerchantOutcome.CLARIFICATION_REQUIRED.value,
                    "reason_codes": [item.value for item in codes],
                    "explanation": explain(
                        outcome=MerchantOutcome.CLARIFICATION_REQUIRED,
                        codes=codes,
                        request=interpreted.constraints,
                        offer=None,
                        previous=None,
                        margin_floor=Decimal("0.15"),
                        prompt_injection=interpreted.prompt_injection,
                    ),
                },
            )
        )
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        return await self._response(
            loaded,
            timing=NegotiationTiming(
                message_interpretation_ms=round(interpret_ms, 2),
                total_turn_ms=round((time.perf_counter() - started) * 1000, 2),
            ),
        )

    async def _close_limit(
        self, row: NegotiationSession, started: float
    ) -> NegotiationResponse:
        row.current_state = transition(
            State(row.current_state), State.NEGOTIATION_LIMIT_REACHED
        ).value
        self._event(row, "NEGOTIATION_LIMIT_REACHED")
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        return await self._response(
            loaded,
            timing=NegotiationTiming(
                total_turn_ms=round((time.perf_counter() - started) * 1000, 2)
            ),
        )

    async def _expired_refresh(
        self,
        row: NegotiationSession,
        interpreted: Any,
        started: float,
        interpret_ms: float,
    ) -> NegotiationResponse:
        self._event(row, "PROPOSAL_EXPIRED")
        self.session.add(
            self._turn(
                row,
                actor=Actor.SYSTEM,
                action="PROPOSAL_EXPIRED",
                message=interpreted.raw_message,
                payload={"reason_codes": [ReasonCode.PROPOSAL_EXPIRED.value]},
            )
        )
        await self.session.commit()
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        return await self._response(
            loaded,
            timing=NegotiationTiming(
                message_interpretation_ms=round(interpret_ms, 2),
                total_turn_ms=round((time.perf_counter() - started) * 1000, 2),
            ),
        )

    def _session_objective(
        self, row: NegotiationSession
    ) -> MerchantObjectiveConfig:
        """Use the objective snapshotted at session creation, not the live config."""
        meta = row.session_metadata or {}
        return from_snapshot(meta.get("merchant_objective"))

    async def _response(
        self,
        row: NegotiationSession,
        *,
        match: Any = None,
        construction: Any = None,
        optimisation: Any = None,
        timing: NegotiationTiming | None = None,
    ) -> NegotiationResponse:
        proposals = [self._to_dto(row, item) for item in row.proposals]
        current = proposals[-1] if proposals else None
        previous = proposals[-2] if len(proposals) >= 2 else None
        policy = await self.policy.get_active()
        inventory = None
        sku = None
        if current and current.offer:
            sku = current.offer.get("sku")
            variant_id = current.offer.get("variant_id")
            if variant_id:
                variants = await self.products.list_variants_by_ids(
                    [uuid.UUID(str(variant_id))]
                )
                if variants:
                    record = getattr(variants[0], "inventory", None)
                    if record is not None:
                        inventory = getattr(record, "units_available", None)
        commercial = None
        if policy is not None:
            commercial = CommercialState(
                minimum_margin_rate=float(policy.minimum_margin_rate),
                maximum_discount_rate=float(policy.maximum_discount_rate),
                inventory_units=inventory,
                expires_at=row.expires_at,
                current_sku=sku,
            )
        return NegotiationResponse(
            session_id=row.id,
            state=row.current_state,
            proposal=current,
            previous_proposal=previous,
            turns=[
                NegotiationTurnView(
                    turn_id=item.id,
                    turn_number=item.turn_number,
                    actor=item.actor,
                    raw_message=item.raw_message,
                    structured_action=item.structured_action,
                    structured_payload=item.structured_payload,
                    related_offer_id=item.related_offer_id,
                    created_at=item.created_at,
                )
                for item in row.turns
            ],
            proposals=proposals,
            commercial=commercial,
            timing=timing,
            events=list(row.events),
            original_intent=row.original_intent,
            merchant_policy_version=row.merchant_policy_version,
            match=match,
            construction=construction,
            optimisation=optimisation,
        )

    def _current_proposal(
        self, row: NegotiationSession
    ) -> MerchantProposal | None:
        if not row.proposals:
            return None
        return max(row.proposals, key=lambda item: item.version)

    def _proposal_row(
        self,
        row: NegotiationSession,
        *,
        version: int,
        proposal_type: ProposalType,
        outcome: MerchantOutcome | str,
        offer_id: uuid.UUID | None,
        snapshot: dict[str, Any] | None,
        codes: list[str],
        explanation: list[str],
        next_acts: list[str],
        expires: datetime,
        compromise: dict[str, Any] | None = None,
        optimisation_run_id: uuid.UUID | None = None,
    ) -> MerchantProposal:
        proposal = MerchantProposal(
            session_id=row.id,
            version=version,
            proposal_type=proposal_type.value,
            outcome=outcome if isinstance(outcome, str) else outcome.value,
            offer_id=offer_id,
            optimisation_run_id=optimisation_run_id,
            offer_snapshot=snapshot,
            reason_codes=codes,
            explanation=explanation,
            next_allowed_actions=next_acts,
            compromise=compromise,
            expires_at=expires,
            created_at=datetime.now(UTC),
        )
        row.proposals.append(proposal)
        return proposal

    def _turn(
        self,
        row: NegotiationSession,
        *,
        actor: Actor | str,
        action: str,
        message: str | None,
        payload: dict[str, Any],
        offer_id: uuid.UUID | None = None,
        proposal_id: uuid.UUID | None = None,
    ) -> NegotiationTurn:
        number = max((item.turn_number for item in row.turns), default=0) + 1
        turn = NegotiationTurn(
            session_id=row.id,
            turn_number=number,
            actor=actor if isinstance(actor, str) else actor.value,
            raw_message=message,
            structured_action=action,
            structured_payload=payload,
            related_offer_id=offer_id,
            related_proposal_id=proposal_id,
            created_at=datetime.now(UTC),
        )
        row.turns.append(turn)
        return turn

    def _event(self, row: NegotiationSession, name: str) -> None:
        events = list(row.events)
        events.append(
            {
                "type": name,
                "at": datetime.now(UTC).isoformat(),
                "state": row.current_state,
            }
        )
        row.events = events

    def _to_dto(
        self, row: NegotiationSession, item: MerchantProposal
    ) -> MerchantProposalDTO:
        return MerchantProposalDTO(
            proposal_id=item.id,
            negotiation_session_id=row.id,
            version=item.version,
            proposal_type=item.proposal_type,
            outcome=item.outcome,
            offer_id=item.offer_id,
            offer=item.offer_snapshot,
            reason_codes=list(item.reason_codes),
            explanation=list(item.explanation),
            next_allowed_actions=list(item.next_allowed_actions),
            compromise=item.compromise,
            expires_at=item.expires_at,
            created_at=item.created_at,
        )


def _snapshot_with_proof(rec: Any, match: Any = None) -> dict[str, Any] | None:
    if rec is None:
        return None
    payload = rec.model_dump(mode="json")
    proof: list[dict[str, Any]] = []
    block = getattr(match, "semantic_matching", None)
    if block is not None and block.matches:
        proof = list(block.matches[0].proof or [])
    return attach_proof_bundle(payload, proof)


def _intent_budget(intent: ShoppingIntent) -> int | None:
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


def _scored_from_public(
    snapshot: dict[str, Any], engine: EngineResult
) -> ScoredOffer | None:
    offer_id = snapshot.get("offer_id")
    if not offer_id:
        return None
    target = uuid.UUID(str(offer_id))
    return next((item for item in engine.scored if item.offer_id == target), None)

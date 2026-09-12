"""Accept a proposal, revalidate live state, reserve, and create an order."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.negotiation.models import MerchantProposalDTO
from app.decision.negotiation.state_machine import NegotiationState as NState
from app.decision.negotiation.state_machine import transition as nego_transition
from app.decision.offers.models import OfferCandidate
from app.decision.transaction.models import (
    TransactionFailureCode,
    TransactionState,
    TransactionTiming,
)
from app.decision.transaction.providers import (
    LocalInventoryReservationProvider,
    LocalOrderProvider,
    ReservationError,
    reservation_view,
)
from app.decision.transaction.revalidation import TransactionRevalidationService
from app.decision.transaction.state_machine import (
    InvalidTransactionTransition,
    transition,
)
from app.models.commerce import CommerceTransaction, InventoryReservation, Order
from app.models.negotiation import MerchantProposal, NegotiationSession
from app.repositories.offer import OfferRepository
from app.repositories.policy import MerchantPolicyRepository
from app.repositories.product import ProductRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import (
    AcceptProposalRequest,
    AcceptProposalResponse,
    OrderView,
    ReservationView,
    RevalidationView,
    TransactionDetailResponse,
)
from app.services.negotiation import NegotiationService

logger = logging.getLogger("astraos.transaction")

ACCEPTABLE = frozenset(
    {
        NState.MERCHANT_PROPOSAL_CREATED,
        NState.MERCHANT_COUNTER_CREATED,
        NState.BUYER_ACCEPTED,
        NState.READY_FOR_CHECKOUT,
    }
)


class TransactionError(ValueError):
    def __init__(
        self,
        message: str,
        code: TransactionFailureCode = TransactionFailureCode.SESSION_NOT_FOUND,
    ) -> None:
        super().__init__(message)
        self.code = code


class TransactionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rows = TransactionRepository(session)
        self.offers = OfferRepository(session)
        self.products = ProductRepository(session)
        self.policy = MerchantPolicyRepository(session)
        self.negotiation = NegotiationService(session)
        self.revalidator = TransactionRevalidationService()
        self.inventory = LocalInventoryReservationProvider(session)
        self.orders = LocalOrderProvider(session)

    async def accept(
        self,
        session_id: UUID,
        payload: AcceptProposalRequest,
    ) -> AcceptProposalResponse:
        existing = await self.rows.get_by_idempotency_key(payload.idempotency_key)
        if existing is not None:
            return await self._to_accept(existing)

        confirmed = await self.rows.get_confirmed_for_proposal(payload.proposal_id)
        if confirmed is not None:
            return await self._to_accept(confirmed)

        row, proposal, created = await self._start(session_id, payload)
        if not created:
            return await self._to_accept(row)
        return await self._execute(row, proposal, payload)

    async def get(self, transaction_id: UUID) -> TransactionDetailResponse | None:
        row = await self.rows.get(transaction_id)
        if row is None:
            return None
        return await self._to_detail(row)

    async def get_order(self, order_id: UUID) -> OrderView | None:
        order = await self.rows.get_order(order_id)
        return _order_view(order) if order else None

    async def get_order_by_number(self, order_number: str) -> OrderView | None:
        order = await self.rows.get_order_by_number(order_number)
        return _order_view(order) if order else None

    async def _start(
        self,
        session_id: UUID,
        payload: AcceptProposalRequest,
    ) -> tuple[CommerceTransaction, MerchantProposal, bool]:
        nego = await self.negotiation.rows.get(session_id)
        if nego is None:
            raise TransactionError(
                "Negotiation session not found",
                TransactionFailureCode.SESSION_NOT_FOUND,
            )
        proposal = next(
            (item for item in nego.proposals if item.id == payload.proposal_id),
            None,
        )
        if proposal is None:
            raise TransactionError(
                "Proposal does not belong to this session",
                TransactionFailureCode.PROPOSAL_NOT_FOUND,
            )
        state = NState(nego.current_state)
        if state not in ACCEPTABLE:
            raise TransactionError(
                f"Session is {state.value}",
                TransactionFailureCode.SESSION_NOT_ACCEPTABLE,
            )
        now = datetime.now(UTC)
        row = CommerceTransaction(
            negotiation_session_id=nego.id,
            proposal_id=proposal.id,
            offer_id=proposal.offer_id,
            transaction_state=TransactionState.PENDING.value,
            idempotency_key=payload.idempotency_key,
            quantity=payload.quantity,
            started_at=now,
            events=[],
            transaction_metadata=_lineage(nego, proposal),
        )
        row.reservations = []
        row.orders = []
        try:
            await self.rows.add(row)
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            loaded = await self.rows.get_by_idempotency_key(payload.idempotency_key)
            if loaded is not None:
                return loaded, proposal, False
            raise TransactionError(
                "Duplicate acceptance conflict",
                TransactionFailureCode.ALREADY_TRANSACTED,
            ) from exc
        await self._mark_accepted(nego)
        self._event(row, "PROPOSAL_ACCEPTED")
        self._event(row, "TRANSACTION_STARTED")
        self.negotiation._event(nego, "PROPOSAL_ACCEPTED")
        await self.session.flush()
        return row, proposal, True

    async def _mark_accepted(self, nego: NegotiationSession) -> None:
        state = NState(nego.current_state)
        if state in {
            NState.MERCHANT_PROPOSAL_CREATED,
            NState.MERCHANT_COUNTER_CREATED,
        }:
            nego.current_state = nego_transition(state, NState.BUYER_ACCEPTED).value
            self.negotiation._event(nego, "BUYER_ACCEPTED")
            state = NState.BUYER_ACCEPTED
        if state == NState.BUYER_ACCEPTED:
            nego.current_state = nego_transition(
                NState.BUYER_ACCEPTED, NState.READY_FOR_CHECKOUT
            ).value
            self.negotiation._event(nego, "READY_FOR_CHECKOUT")

    async def _execute(
        self,
        row: CommerceTransaction,
        proposal: MerchantProposal,
        payload: AcceptProposalRequest,
    ) -> AcceptProposalResponse:
        started = time.perf_counter()
        timing = TransactionTiming()
        nego = await self.negotiation.rows.get(row.negotiation_session_id)
        assert nego is not None
        try:
            self._move(row, TransactionState.REVALIDATING)
            self._event(row, "REVALIDATION_STARTED")
            reval_started = time.perf_counter()
            offer = await self._load_offer(proposal.offer_id)
            variant = None
            if offer is not None:
                variants = await self.products.list_variants_by_ids([offer.variant_id])
                variant = variants[0] if variants else None
            policy = await self.policy.get_active()
            result = self.revalidator.validate(
                session=nego,
                proposal=proposal,
                variant=variant,
                policy=policy,
                offer=offer,
                quantity=payload.quantity,
            )
            timing.revalidation_ms = round(
                (time.perf_counter() - reval_started) * 1000, 2
            )
            row.revalidation = result.model_dump(mode="json")
            if not result.valid:
                self._fail(
                    row,
                    TransactionState.REVALIDATION_FAILED,
                    result.failure_codes[0]
                    if result.failure_codes
                    else TransactionFailureCode.PROPOSAL_NOT_FOUND,
                    [item.value for item in result.failure_codes],
                )
                self._event(row, "REVALIDATION_FAILED")
                await self.session.commit()
                recovery = None
                if payload.generate_recovery:
                    recovery = await self.negotiation.recover_after_failure(
                        nego.id,
                        failure_codes=[item.value for item in result.failure_codes],
                    )
                timing.total_transaction_ms = round(
                    (time.perf_counter() - started) * 1000, 2
                )
                return await self._to_accept(row, recovery=recovery, timing=timing)

            self._event(row, "REVALIDATION_PASSED")
            self._move(row, TransactionState.READY_TO_RESERVE)
            assert offer is not None
            self._move(row, TransactionState.RESERVING)
            reserve_started = time.perf_counter()
            try:
                reservation = await self.inventory.reserve(
                    row, offer.variant_id, payload.quantity
                )
            except ReservationError as exc:
                timing.reservation_ms = round(
                    (time.perf_counter() - reserve_started) * 1000, 2
                )
                self._fail(
                    row,
                    TransactionState.RESERVATION_FAILED,
                    exc.code,
                    [exc.code.value],
                )
                self._event(row, "RESERVATION_FAILED")
                await self.session.commit()
                timing.total_transaction_ms = round(
                    (time.perf_counter() - started) * 1000, 2
                )
                return await self._to_accept(row, timing=timing)
            row.reservation_id = reservation.id
            row.reservations.append(reservation)
            self._move(row, TransactionState.RESERVED)
            self._event(row, "INVENTORY_RESERVED")
            timing.reservation_ms = round(
                (time.perf_counter() - reserve_started) * 1000, 2
            )

            self._move(row, TransactionState.CREATING_ORDER)
            order_started = time.perf_counter()
            try:
                order = await self.orders.create(
                    transaction=row,
                    session=nego,
                    proposal=proposal,
                    offer=offer,
                    quantity=payload.quantity,
                )
            except Exception:  # noqa: BLE001 - convert to typed failure
                timing.order_creation_ms = round(
                    (time.perf_counter() - order_started) * 1000, 2
                )
                await self.inventory.release(reservation)
                self._fail(
                    row,
                    TransactionState.ORDER_FAILED,
                    TransactionFailureCode.ORDER_CREATION_FAILED,
                    [TransactionFailureCode.ORDER_CREATION_FAILED.value],
                )
                self._event(row, "TRANSACTION_FAILED")
                await self.session.commit()
                logger.exception("Order creation failed after reservation")
                timing.total_transaction_ms = round(
                    (time.perf_counter() - started) * 1000, 2
                )
                return await self._to_accept(row, timing=timing)
            await self.inventory.consume(reservation)
            row.order_id = order.id
            row.orders.append(order)
            self._move(row, TransactionState.CONFIRMED)
            row.completed_at = datetime.now(UTC)
            self._event(row, "ORDER_CREATED")
            self._event(row, "ORDER_CONFIRMED")
            nego.current_state = nego_transition(
                NState(nego.current_state), NState.TRANSACTION_CONFIRMED
            ).value
            self.negotiation._event(nego, "TRANSACTION_CONFIRMED")
            timing.order_creation_ms = round(
                (time.perf_counter() - order_started) * 1000, 2
            )
            timing.total_transaction_ms = round(
                (time.perf_counter() - started) * 1000, 2
            )
            meta = dict(row.transaction_metadata)
            meta["timing"] = timing.model_dump()
            row.transaction_metadata = meta
            try:
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()
                winner = await self.rows.get_confirmed_for_proposal(proposal.id)
                if winner is not None:
                    return await self._to_accept(winner, timing=timing)
                raise
            return await self._to_accept(row, timing=timing)
        except InvalidTransactionTransition as exc:
            await self.session.rollback()
            raise TransactionError(
                str(exc), TransactionFailureCode.INVALID_TRANSITION
            ) from exc

    async def _load_offer(self, offer_id: UUID | None) -> OfferCandidate | None:
        if offer_id is None:
            return None
        row = await self.offers.get_offer(offer_id)
        if row is None:
            return None
        return OfferCandidate.model_validate(row.payload)

    def _move(self, row: CommerceTransaction, target: TransactionState) -> None:
        row.transaction_state = transition(
            TransactionState(row.transaction_state), target
        ).value

    def _fail(
        self,
        row: CommerceTransaction,
        target: TransactionState,
        code: TransactionFailureCode,
        codes: list[str],
    ) -> None:
        self._move(row, target)
        row.failure_code = code.value
        row.failure_details = {"failure_codes": codes}
        row.completed_at = datetime.now(UTC)
        self._event(row, "TRANSACTION_FAILED")

    def _event(self, row: CommerceTransaction, name: str) -> None:
        events = list(row.events)
        events.append(
            {
                "type": name,
                "at": datetime.now(UTC).isoformat(),
                "state": row.transaction_state,
            }
        )
        row.events = events

    async def _to_accept(
        self,
        row: CommerceTransaction,
        *,
        recovery: MerchantProposalDTO | None = None,
        timing: TransactionTiming | None = None,
    ) -> AcceptProposalResponse:
        loaded = await self.rows.get(row.id)
        assert loaded is not None
        nego = await self.negotiation.rows.get(loaded.negotiation_session_id)
        reservation = _latest_reservation(loaded)
        order = loaded.orders[0] if loaded.orders else None
        reval = loaded.revalidation or {}
        failure_codes = list((loaded.failure_details or {}).get("failure_codes") or [])
        if loaded.failure_code and loaded.failure_code not in failure_codes:
            failure_codes.append(loaded.failure_code)
        next_actions: list[str] = []
        if loaded.transaction_state == TransactionState.CONFIRMED.value:
            next_actions = ["NONE"]
        elif loaded.transaction_state == TransactionState.REVALIDATION_FAILED.value:
            next_actions = ["REQUEST_NEW_PROPOSAL"]
        stored_timing = (loaded.transaction_metadata or {}).get("timing")
        return AcceptProposalResponse(
            transaction_id=loaded.id,
            state=loaded.transaction_state,
            negotiation_state=nego.current_state if nego else None,
            proposal_id=loaded.proposal_id,
            offer_id=loaded.offer_id,
            revalidation=_revalidation_view(reval),
            reservation=_reservation_view(reservation),
            order=_order_view(order),
            failure_codes=failure_codes,
            next_actions=next_actions,
            recovery_proposal=recovery,
            timing=timing
            or (TransactionTiming(**stored_timing) if stored_timing else None),
            events=list(loaded.events),
            lineage=dict(loaded.transaction_metadata or {}),
        )

    async def _to_detail(self, row: CommerceTransaction) -> TransactionDetailResponse:
        base = await self._to_accept(row)
        nego = await self.negotiation.rows.get(row.negotiation_session_id)
        proposal = None
        if nego is not None:
            match = next(
                (item for item in nego.proposals if item.id == row.proposal_id),
                None,
            )
            if match is not None:
                proposal = self.negotiation._to_dto(nego, match)
        return TransactionDetailResponse(
            **base.model_dump(),
            session_id=row.negotiation_session_id,
            proposal=proposal,
        )


def _lineage(
    nego: NegotiationSession, proposal: MerchantProposal
) -> dict[str, Any]:
    return {
        "match_run_id": str(nego.match_run_id) if nego.match_run_id else None,
        "offer_run_id": str(nego.offer_run_id) if nego.offer_run_id else None,
        "optimisation_run_id": (
            str(nego.optimisation_run_id) if nego.optimisation_run_id else None
        ),
        "negotiation_session_id": str(nego.id),
        "proposal_id": str(proposal.id),
        "offer_id": str(proposal.offer_id) if proposal.offer_id else None,
        "intent_run_id": (
            str(nego.initial_intent_run_id) if nego.initial_intent_run_id else None
        ),
    }


def _latest_reservation(
    row: CommerceTransaction,
) -> InventoryReservation | None:
    if not row.reservations:
        return None
    return max(row.reservations, key=lambda item: item.id.hex)


def _revalidation_view(payload: dict[str, Any]) -> RevalidationView | None:
    if not payload:
        return None
    valid = bool(payload.get("valid"))
    return RevalidationView(
        status="PASSED" if valid else "FAILED",
        checks=list(payload.get("checks") or []),
        failure_codes=list(payload.get("failure_codes") or []),
        current_state_snapshot=dict(payload.get("current_state_snapshot") or {}),
        validated_at=payload.get("validated_at"),
    )


def _reservation_view(row: InventoryReservation | None) -> ReservationView | None:
    if row is None:
        return None
    view = reservation_view(row)
    return ReservationView(
        reservation_id=view.reservation_id,
        status=view.status.value,
        variant_id=view.variant_id,
        quantity=view.quantity,
    )


def _order_view(row: Order | None) -> OrderView | None:
    if row is None:
        return None
    return OrderView(
        order_id=row.id,
        order_number=row.order_number,
        status=row.status,
        sku=row.sku,
        product_name=row.product_name,
        quantity=row.quantity,
        product_price_cents=row.product_price_cents,
        delivery_charge_cents=row.delivery_charge_cents,
        warranty_price_cents=row.warranty_price_cents,
        bundle_price_cents=row.bundle_price_cents,
        total_amount_cents=row.total_amount_cents,
        currency=row.currency,
        delivery_code=row.delivery_code,
        warranty_code=row.warranty_code,
        bundle_code=row.bundle_code,
        return_policy_code=row.return_policy_code,
        warranty_months=row.warranty_months,
        payment_mode=row.payment_mode,
        payment_status=row.payment_status,
        confirmation=dict(row.confirmation),
        created_at=row.created_at,
        confirmed_at=row.confirmed_at,
    )

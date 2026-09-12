"""Atomic local inventory reservation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.decision.transaction.models import ReservationStatus, TransactionState
from app.decision.transaction.providers import (
    LocalInventoryReservationProvider,
    ReservationError,
)
from app.models.commerce import CommerceTransaction
from app.models.inventory import InventoryRecord
from app.models.negotiation import MerchantProposal, NegotiationSession
from app.schemas.negotiation import CreateNegotiationRequest
from app.schemas.transaction import AcceptProposalRequest
from app.services.negotiation import NegotiationService
from app.services.transaction import TransactionService
from tests.factories import make_inventory, make_product, make_variant

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)

_INTENT = {
    "raw_text": "x",
    "category": "headphones",
    "hard_constraints": [],
    "soft_preferences": [],
    "context_tags": [],
    "context_items": [],
    "desired_outcomes": [],
    "values": [],
    "tradeoffs": [],
    "unsupported_semantic_needs": [],
    "ambiguities": [],
    "parser_type": "rule_based",
    "parser_version": "1",
    "status": "READY",
}


async def _stub_txn(db_session: AsyncSession) -> CommerceTransaction:
    now = datetime.now(UTC)
    session = NegotiationSession(
        current_state="READY_FOR_CHECKOUT",
        buyer_agent_type="MANUAL",
        buyer_profile="INTENT_ADAPTED",
        merchant_policy_version="v1",
        original_intent=_INTENT,
        working_intent=_INTENT,
        delta_history=[],
        events=[],
        raw_intent="x",
        turn_count=0,
        max_turns=5,
        session_metadata={},
    )
    session.turns = []
    session.proposals = []
    db_session.add(session)
    await db_session.flush()
    proposal = MerchantProposal(
        session_id=session.id,
        version=1,
        proposal_type="INITIAL",
        outcome="INITIAL",
        reason_codes=[],
        explanation=[],
        next_allowed_actions=[],
        created_at=now,
    )
    db_session.add(proposal)
    await db_session.flush()
    row = CommerceTransaction(
        negotiation_session_id=session.id,
        proposal_id=proposal.id,
        transaction_state=TransactionState.RESERVING.value,
        idempotency_key=f"res-{uuid.uuid4()}",
        quantity=1,
        started_at=now,
        events=[],
        transaction_metadata={},
    )
    row.reservations = []
    row.orders = []
    db_session.add(row)
    await db_session.flush()
    return row


@pytest.mark.asyncio
async def test_successful_reservation(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_available=4, units_reserved=1)
    db_session.add_all([product, variant, inventory])
    await db_session.flush()
    txn = await _stub_txn(db_session)
    provider = LocalInventoryReservationProvider(db_session)
    reserved = await provider.reserve(txn, variant.id, 1)
    assert reserved.status == ReservationStatus.ACTIVE.value
    await db_session.refresh(inventory)
    assert inventory.units_reserved == 2
    await provider.consume(reserved)
    await db_session.refresh(inventory)
    assert inventory.units_available == 3
    assert inventory.units_reserved == 1
    assert reserved.status == ReservationStatus.CONSUMED.value


@pytest.mark.asyncio
async def test_insufficient_inventory(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_available=1, units_reserved=1)
    db_session.add_all([product, variant, inventory])
    await db_session.flush()
    txn = await _stub_txn(db_session)
    provider = LocalInventoryReservationProvider(db_session)
    with pytest.raises(ReservationError):
        await provider.reserve(txn, variant.id, 1)


@pytest.mark.asyncio
async def test_release_restores_reserved(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_available=3, units_reserved=0)
    db_session.add_all([product, variant, inventory])
    await db_session.flush()
    txn = await _stub_txn(db_session)
    provider = LocalInventoryReservationProvider(db_session)
    reserved = await provider.reserve(txn, variant.id, 2)
    await provider.release(reserved)
    await db_session.refresh(inventory)
    assert inventory.units_reserved == 0
    assert inventory.units_available == 3
    assert reserved.status == ReservationStatus.RELEASED.value


@pytest.mark.asyncio
async def test_no_negative_stock(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    inventory = make_inventory(variant.id, units_available=1, units_reserved=0)
    db_session.add_all([product, variant, inventory])
    await db_session.flush()
    txn = await _stub_txn(db_session)
    provider = LocalInventoryReservationProvider(db_session)
    with pytest.raises(ReservationError):
        await provider.reserve(txn, variant.id, 2)
    await db_session.refresh(inventory)
    assert inventory.units_reserved == 0
    assert inventory.units_available == 1


@pytest.mark.asyncio
async def test_concurrent_last_unit() -> None:
    async with AsyncSessionLocal() as session:
        opened = await NegotiationService(session).create(
            CreateNegotiationRequest(intent=HERO)
        )
    assert opened.proposal and opened.proposal.offer
    variant_id = uuid.UUID(str(opened.proposal.offer["variant_id"]))
    async with AsyncSessionLocal() as session:
        inventory = (
            await session.scalars(
                select(InventoryRecord).where(
                    InventoryRecord.variant_id == variant_id
                )
            )
        ).one()
        inventory.units_available = 1
        inventory.units_reserved = 0
        await session.commit()

    async def _one(key: str) -> str:
        async with AsyncSessionLocal() as session:
            service = TransactionService(session)
            response = await service.accept(
                opened.session_id,
                AcceptProposalRequest(
                    proposal_id=opened.proposal.proposal_id,
                    idempotency_key=key,
                    generate_recovery=False,
                ),
            )
            return response.state

    first, second = await asyncio.gather(
        _one(f"c1-{uuid.uuid4()}"),
        _one(f"c2-{uuid.uuid4()}"),
    )
    states = {first, second}
    assert "CONFIRMED" in states
    assert "RESERVATION_FAILED" in states or "REVALIDATION_FAILED" in states
    assert [item for item in (first, second) if item == "CONFIRMED"] == [
        "CONFIRMED"
    ]

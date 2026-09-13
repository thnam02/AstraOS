"""Persistence for commerce transactions, reservations, and orders."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commerce import CommerceTransaction, InventoryReservation, Order


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: CommerceTransaction) -> CommerceTransaction:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, transaction_id: UUID) -> CommerceTransaction | None:
        result = await self.session.execute(
            select(CommerceTransaction)
            .where(CommerceTransaction.id == transaction_id)
            .options(
                selectinload(CommerceTransaction.reservations),
                selectinload(CommerceTransaction.orders),
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(
        self, key: str
    ) -> CommerceTransaction | None:
        result = await self.session.execute(
            select(CommerceTransaction)
            .where(CommerceTransaction.idempotency_key == key)
            .options(
                selectinload(CommerceTransaction.reservations),
                selectinload(CommerceTransaction.orders),
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_latest_for_negotiation(
        self, negotiation_session_id: UUID
    ) -> CommerceTransaction | None:
        result = await self.session.execute(
            select(CommerceTransaction)
            .where(
                CommerceTransaction.negotiation_session_id == negotiation_session_id
            )
            .options(
                selectinload(CommerceTransaction.reservations),
                selectinload(CommerceTransaction.orders),
            )
            .order_by(CommerceTransaction.created_at.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_confirmed_for_proposal(
        self, proposal_id: UUID
    ) -> CommerceTransaction | None:
        result = await self.session.execute(
            select(CommerceTransaction)
            .where(
                CommerceTransaction.proposal_id == proposal_id,
                CommerceTransaction.transaction_state == "CONFIRMED",
            )
            .options(
                selectinload(CommerceTransaction.reservations),
                selectinload(CommerceTransaction.orders),
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_order(self, order_id: UUID) -> Order | None:
        result = await self.session.scalars(select(Order).where(Order.id == order_id))
        return result.one_or_none()

    async def get_order_by_number(self, order_number: str) -> Order | None:
        result = await self.session.scalars(
            select(Order).where(Order.order_number == order_number)
        )
        return result.one_or_none()

    async def get_reservation(
        self, reservation_id: UUID
    ) -> InventoryReservation | None:
        result = await self.session.scalars(
            select(InventoryReservation).where(
                InventoryReservation.id == reservation_id
            )
        )
        return result.one_or_none()

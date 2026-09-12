"""Commerce execution adapters. Local implementations are demo-only."""

from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.decision.offers.models import OfferCandidate
from app.decision.transaction.models import (
    OrderStatus,
    ReservationResult,
    ReservationStatus,
    TransactionFailureCode,
)
from app.models.commerce import (
    CommerceTransaction,
    InventoryReservation,
    Order,
    OrderNumberSequence,
)
from app.models.inventory import InventoryRecord
from app.models.negotiation import MerchantProposal, NegotiationSession


class ReservationError(Exception):
    def __init__(self, code: TransactionFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class OrderCreationError(Exception):
    def __init__(self, code: TransactionFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class InventoryReservationProvider(Protocol):
    async def reserve(
        self,
        transaction: CommerceTransaction,
        variant_id: UUID,
        quantity: int,
    ) -> InventoryReservation: ...

    async def consume(self, reservation: InventoryReservation) -> None: ...

    async def release(self, reservation: InventoryReservation) -> None: ...


class OrderProvider(Protocol):
    async def create(
        self,
        *,
        transaction: CommerceTransaction,
        session: NegotiationSession,
        proposal: MerchantProposal,
        offer: OfferCandidate,
        quantity: int,
    ) -> Order: ...


class LocalInventoryReservationProvider:
    """Atomic local reservation using SELECT ... FOR UPDATE."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def reserve(
        self,
        transaction: CommerceTransaction,
        variant_id: UUID,
        quantity: int,
    ) -> InventoryReservation:
        now = datetime.now(UTC)
        ttl = timedelta(minutes=settings.reservation_ttl_minutes)
        row = InventoryReservation(
            transaction_id=transaction.id,
            variant_id=variant_id,
            quantity=quantity,
            status=ReservationStatus.PENDING.value,
        )
        self.db.add(row)
        await self.db.flush()

        inventory = await self._lock_inventory(variant_id)
        if inventory is None:
            row.status = ReservationStatus.FAILED.value
            await self.db.flush()
            raise ReservationError(
                TransactionFailureCode.RESERVATION_FAILED,
                "Inventory record is missing.",
            )
        available = int(inventory.units_available) - int(inventory.units_reserved)
        if available < quantity:
            row.status = ReservationStatus.FAILED.value
            await self.db.flush()
            code = (
                TransactionFailureCode.OUT_OF_STOCK
                if available <= 0
                else TransactionFailureCode.INSUFFICIENT_STOCK
            )
            raise ReservationError(code, f"Only {available} sellable units.")
        inventory.units_reserved = int(inventory.units_reserved) + quantity
        row.status = ReservationStatus.ACTIVE.value
        row.reserved_at = now
        row.expires_at = now + ttl
        await self.db.flush()
        return row

    async def consume(self, reservation: InventoryReservation) -> None:
        inventory = await self._lock_inventory(reservation.variant_id)
        if inventory is None:
            raise ReservationError(
                TransactionFailureCode.RESERVATION_FAILED,
                "Inventory record is missing.",
            )
        if reservation.status != ReservationStatus.ACTIVE.value:
            raise ReservationError(
                TransactionFailureCode.RESERVATION_FAILED,
                f"Reservation is {reservation.status}.",
            )
        qty = int(reservation.quantity)
        if int(inventory.units_reserved) < qty:
            raise ReservationError(
                TransactionFailureCode.RESERVATION_FAILED,
                "Reserved count is inconsistent.",
            )
        if int(inventory.units_available) < qty:
            raise ReservationError(
                TransactionFailureCode.RESERVATION_FAILED,
                "On-hand stock is inconsistent.",
            )
        inventory.units_reserved = int(inventory.units_reserved) - qty
        inventory.units_available = int(inventory.units_available) - qty
        reservation.status = ReservationStatus.CONSUMED.value
        reservation.released_at = datetime.now(UTC)
        await self.db.flush()

    async def release(self, reservation: InventoryReservation) -> None:
        if reservation.status != ReservationStatus.ACTIVE.value:
            return
        inventory = await self._lock_inventory(reservation.variant_id)
        if inventory is not None:
            qty = int(reservation.quantity)
            reserved = max(0, int(inventory.units_reserved) - qty)
            inventory.units_reserved = reserved
        reservation.status = ReservationStatus.RELEASED.value
        reservation.released_at = datetime.now(UTC)
        await self.db.flush()

    async def _lock_inventory(self, variant_id: UUID) -> InventoryRecord | None:
        result = await self.db.scalars(
            select(InventoryRecord)
            .where(InventoryRecord.variant_id == variant_id)
            .with_for_update()
        )
        return result.one_or_none()


class LocalOrderProvider:
    """Persist an immutable local order snapshot. No payment movement."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        transaction: CommerceTransaction,
        session: NegotiationSession,
        proposal: MerchantProposal,
        offer: OfferCandidate,
        quantity: int,
    ) -> Order:
        now = datetime.now(UTC)
        number = await self._next_order_number(now.year)
        confirmation = {
            "order_number": number,
            "status": OrderStatus.CONFIRMED.value,
            "items": [{"sku": offer.sku, "quantity": quantity}],
            "commercial_terms": {
                "total_cents": offer.total_customer_price_cents * quantity,
                "currency": offer.currency,
                "delivery": offer.delivery_code,
                "warranty_months": offer.warranty_months,
                "product_price_cents": offer.final_product_price_cents,
                "delivery_charge_cents": offer.delivery_customer_charge_cents,
                "warranty_price_cents": offer.warranty_customer_price_cents,
                "bundle_price_cents": offer.bundle_customer_price_cents,
            },
            "proposal_id": str(proposal.id),
            "transaction_id": str(transaction.id),
            "payment_mode": "SIMULATED",
            "payment_status": "NOT_REQUIRED_FOR_DEMO",
            "proof": [item.model_dump(mode="json") for item in offer.proof],
        }
        row = Order(
            order_number=number,
            transaction_id=transaction.id,
            negotiation_session_id=session.id,
            proposal_id=proposal.id,
            offer_id=offer.id,
            variant_id=offer.variant_id,
            quantity=quantity,
            product_price_cents=offer.final_product_price_cents,
            delivery_charge_cents=offer.delivery_customer_charge_cents,
            warranty_price_cents=offer.warranty_customer_price_cents,
            bundle_price_cents=offer.bundle_customer_price_cents,
            total_amount_cents=offer.total_customer_price_cents * quantity,
            currency=offer.currency,
            delivery_option_id=offer.delivery_option_id,
            warranty_option_id=offer.warranty_option_id,
            bundle_option_id=offer.bundle_option_id,
            return_policy_id=offer.return_policy_id,
            delivery_code=offer.delivery_code,
            warranty_code=offer.warranty_code,
            bundle_code=offer.bundle_code,
            return_policy_code=offer.return_policy_code,
            sku=offer.sku,
            product_name=offer.product_name,
            warranty_months=offer.warranty_months,
            status=OrderStatus.CONFIRMED.value,
            payment_mode="SIMULATED",
            payment_status="NOT_REQUIRED_FOR_DEMO",
            confirmation=confirmation,
            created_at=now,
            confirmed_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def _next_order_number(self, year: int) -> str:
        result = await self.db.scalars(
            select(OrderNumberSequence)
            .where(OrderNumberSequence.year == year)
            .with_for_update()
        )
        counter = result.one_or_none()
        if counter is None:
            try:
                async with self.db.begin_nested():
                    counter = OrderNumberSequence(year=year, last_value=0)
                    self.db.add(counter)
                    await self.db.flush()
            except IntegrityError:
                result = await self.db.scalars(
                    select(OrderNumberSequence)
                    .where(OrderNumberSequence.year == year)
                    .with_for_update()
                )
                counter = result.one()
        assert counter is not None
        counter.last_value = int(counter.last_value) + 1
        await self.db.flush()
        return f"AST-{year}-{counter.last_value:06d}"


def reservation_view(row: InventoryReservation) -> ReservationResult:
    return ReservationResult(
        reservation_id=row.id,
        status=ReservationStatus(row.status),
        variant_id=row.variant_id,
        quantity=row.quantity,
        reserved_at=row.reserved_at,
        expires_at=row.expires_at,
    )

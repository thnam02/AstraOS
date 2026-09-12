"""Merchant-side transaction, reservation, and order snapshots.

AstraOS is not a payment processor, OMS, or ERP. These tables persist
the integration-boundary execution of an accepted proposal.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CommerceTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commerce_transactions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_commerce_transactions_idemp"),
    )

    negotiation_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchant_proposals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    transaction_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    failure_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revalidation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    events: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    transaction_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )

    reservations: Mapped[list["InventoryReservation"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class InventoryReservation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_reservations"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commerce_transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transaction: Mapped[CommerceTransaction] = relationship(
        back_populates="reservations"
    )


class Order(UUIDPrimaryKeyMixin, Base):
    """Immutable commercial snapshot of an executed proposal."""

    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("order_number", name="uq_orders_order_number"),)

    order_number: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commerce_transactions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    negotiation_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("negotiation_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchant_proposals.id", ondelete="RESTRICT"),
        nullable=False,
    )
    offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    product_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_charge_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    warranty_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")
    delivery_option_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    warranty_option_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    bundle_option_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    return_policy_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    delivery_code: Mapped[str | None] = mapped_column(String(32))
    warranty_code: Mapped[str | None] = mapped_column(String(32))
    bundle_code: Mapped[str | None] = mapped_column(String(32))
    return_policy_code: Mapped[str | None] = mapped_column(String(32))
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    warranty_months: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False)
    confirmation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transaction: Mapped[CommerceTransaction] = relationship(back_populates="orders")


class OrderNumberSequence(Base):
    """Year-scoped counter for human-readable AST-YYYY-NNNNNN ids."""

    __tablename__ = "order_number_sequences"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

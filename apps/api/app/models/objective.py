"""Persisted merchant commercial objective. Separate from policy guardrails."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.merchant import Merchant
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MerchantObjective(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """What the merchant prefers among policy-safe Pareto offers."""

    __tablename__ = "merchant_objectives"
    __table_args__ = (
        CheckConstraint(
            "buyer_weight >= 0 AND buyer_weight <= 1",
            name="ck_objective_buyer_weight",
        ),
        CheckConstraint(
            "merchant_weight >= 0 AND merchant_weight <= 1",
            name="ck_objective_merchant_weight",
        ),
    )

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="BALANCED")
    buyer_weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    merchant_weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    merchant: Mapped[Merchant] = relationship(back_populates="objectives")

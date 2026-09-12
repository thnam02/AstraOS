"""Merchant commercial policy. Stored only — not evaluated in Stage 1."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.merchant import Merchant
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MerchantPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Guardrails for later offer construction. No evaluation happens here."""

    __tablename__ = "merchant_policies"
    __table_args__ = (
        CheckConstraint(
            "minimum_margin_rate >= 0 AND minimum_margin_rate < 1",
            name="ck_policy_minimum_margin_rate",
        ),
        CheckConstraint(
            "maximum_discount_rate >= 0 AND maximum_discount_rate <= 1",
            name="ck_policy_maximum_discount_rate",
        ),
        CheckConstraint(
            "maximum_delivery_subsidy_cents IS NULL"
            " OR maximum_delivery_subsidy_cents >= 0",
            name="ck_policy_max_delivery_subsidy",
        ),
        CheckConstraint(
            "maximum_warranty_subsidy_cents IS NULL"
            " OR maximum_warranty_subsidy_cents >= 0",
            name="ck_policy_max_warranty_subsidy",
        ),
        CheckConstraint(
            "maximum_bundle_subsidy_cents IS NULL"
            " OR maximum_bundle_subsidy_cents >= 0",
            name="ck_policy_max_bundle_subsidy",
        ),
    )

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    minimum_margin_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    maximum_discount_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False
    )
    delivery_subsidy_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    warranty_upgrade_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    bundle_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    flexible_returns_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    loyalty_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    maximum_delivery_subsidy_cents: Mapped[int | None] = mapped_column(Integer)
    maximum_warranty_subsidy_cents: Mapped[int | None] = mapped_column(Integer)
    maximum_bundle_subsidy_cents: Mapped[int | None] = mapped_column(Integer)

    merchant: Mapped[Merchant] = relationship(back_populates="policies")

"""Return policies and per-variant mappings."""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.product import ProductVariant


class ReturnPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Return window the merchant can attach to a SKU."""

    __tablename__ = "return_policies"
    __table_args__ = (
        CheckConstraint("return_window_days > 0", name="ck_return_window_positive"),
        CheckConstraint(
            "restocking_fee_rate IS NULL OR "
            "(restocking_fee_rate >= 0 AND restocking_fee_rate <= 1)",
            name="ck_return_restocking_fee_rate",
        ),
        CheckConstraint(
            "merchant_expected_cost_cents IS NULL OR merchant_expected_cost_cents >= 0",
            name="ck_return_expected_cost_nonnegative",
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    return_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    restocking_fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    conditions: Mapped[str | None] = mapped_column(Text)
    merchant_expected_cost_cents: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant_links: Mapped[list["VariantReturnPolicy"]] = relationship(
        back_populates="return_policy",
        cascade="all, delete-orphan",
    )


class VariantReturnPolicy(UUIDPrimaryKeyMixin, Base):
    """Whether a SKU may use a return policy."""

    __tablename__ = "variant_return_policies"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "return_policy_id",
            name="uq_variant_return_policy",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    return_policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("return_policies.id", ondelete="CASCADE"),
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant: Mapped[ProductVariant] = relationship(back_populates="return_policies")
    return_policy: Mapped[ReturnPolicy] = relationship(back_populates="variant_links")

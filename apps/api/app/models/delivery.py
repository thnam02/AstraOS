"""Fulfilment options and per-variant availability."""

import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.product import ProductVariant


class DeliveryOption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Merchant fulfilment method, independent of any offer."""

    __tablename__ = "delivery_options"
    __table_args__ = (
        CheckConstraint("delivery_days >= 0", name="ck_delivery_days_nonnegative"),
        CheckConstraint(
            "merchant_cost_cents >= 0", name="ck_delivery_merchant_cost_nonnegative"
        ),
        CheckConstraint(
            "customer_charge_cents >= 0", name="ck_delivery_customer_charge_nonnegative"
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    merchant_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_charge_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant_links: Mapped[list["VariantDeliveryOption"]] = relationship(
        back_populates="delivery_option",
        cascade="all, delete-orphan",
    )


class VariantDeliveryOption(UUIDPrimaryKeyMixin, Base):
    """Whether a SKU can use a delivery method, with optional cost overrides."""

    __tablename__ = "variant_delivery_options"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "delivery_option_id",
            name="uq_variant_delivery_option",
        ),
        CheckConstraint(
            "merchant_cost_override_cents IS NULL"
            " OR merchant_cost_override_cents >= 0",
            name="ck_variant_delivery_merchant_override_nonnegative",
        ),
        CheckConstraint(
            "customer_charge_override_cents IS NULL"
            " OR customer_charge_override_cents >= 0",
            name="ck_variant_delivery_customer_override_nonnegative",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("delivery_options.id", ondelete="CASCADE"),
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    merchant_cost_override_cents: Mapped[int | None] = mapped_column(Integer)
    customer_charge_override_cents: Mapped[int | None] = mapped_column(Integer)
    cutoff_time: Mapped[time | None] = mapped_column(Time)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    variant: Mapped[ProductVariant] = relationship(back_populates="delivery_options")
    delivery_option: Mapped[DeliveryOption] = relationship(
        back_populates="variant_links"
    )

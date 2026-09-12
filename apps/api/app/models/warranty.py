"""Warranty catalogue and per-variant mappings."""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.product import ProductVariant


class WarrantyOption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Warranty term the merchant can attach to a SKU."""

    __tablename__ = "warranty_options"
    __table_args__ = (
        CheckConstraint("months > 0", name="ck_warranty_months_positive"),
        CheckConstraint(
            "merchant_cost_cents >= 0", name="ck_warranty_merchant_cost_nonnegative"
        ),
        CheckConstraint(
            "customer_price_cents >= 0", name="ck_warranty_customer_price_nonnegative"
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    merchant_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant_links: Mapped[list["VariantWarrantyOption"]] = relationship(
        back_populates="warranty_option",
        cascade="all, delete-orphan",
    )


class VariantWarrantyOption(UUIDPrimaryKeyMixin, Base):
    """Whether a SKU may use a warranty option."""

    __tablename__ = "variant_warranty_options"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "warranty_option_id",
            name="uq_variant_warranty_option",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warranty_option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranty_options.id", ondelete="CASCADE"),
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant: Mapped[ProductVariant] = relationship(back_populates="warranty_options")
    warranty_option: Mapped[WarrantyOption] = relationship(
        back_populates="variant_links"
    )

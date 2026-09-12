"""Bundle catalogue and per-variant mappings."""

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.product import ProductVariant


class BundleOption(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Optional accessory bundle. Absence of a row is not a bundle."""

    __tablename__ = "bundle_options"
    __table_args__ = (
        CheckConstraint(
            "merchant_cost_cents >= 0", name="ck_bundle_merchant_cost_nonnegative"
        ),
        CheckConstraint(
            "customer_price_cents >= 0", name="ck_bundle_customer_price_nonnegative"
        ),
    )

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    merchant_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    variant_links: Mapped[list["VariantBundleOption"]] = relationship(
        back_populates="bundle_option",
        cascade="all, delete-orphan",
    )


class VariantBundleOption(UUIDPrimaryKeyMixin, Base):
    """Whether a SKU may be sold with a bundle."""

    __tablename__ = "variant_bundle_options"
    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "bundle_option_id",
            name="uq_variant_bundle_option",
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bundle_option_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bundle_options.id", ondelete="CASCADE"),
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    variant: Mapped[ProductVariant] = relationship(back_populates="bundle_options")
    bundle_option: Mapped[BundleOption] = relationship(back_populates="variant_links")

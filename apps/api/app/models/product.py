"""Product and SKU models. Product ≠ ProductVariant ≠ Offer."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from app.models.bundle import VariantBundleOption
    from app.models.delivery import VariantDeliveryOption
    from app.models.inventory import InventoryRecord
    from app.models.provenance import AttributeEvidence
    from app.models.returns import VariantReturnPolicy
    from app.models.warranty import VariantWarrantyOption


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Conceptual catalogue item, e.g. Aurora A9."""

    __tablename__ = "products"
    __table_args__ = (
        {"comment": "Conceptual products. Commercial offers are not stored here."},
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    model_number: Mapped[str | None] = mapped_column(String(80))
    manufacturer: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Exact merchant SKU. Money is stored as integer cents."""

    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("base_price_cents > 0", name="ck_variant_base_price_positive"),
        CheckConstraint("cogs_cents >= 0", name="ck_variant_cogs_nonnegative"),
        UniqueConstraint("sku", name="uq_product_variants_sku"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="AUD")
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    cogs_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")
    inventory: Mapped[InventoryRecord | None] = relationship(
        back_populates="variant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    delivery_options: Mapped[list[VariantDeliveryOption]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )
    warranty_options: Mapped[list[VariantWarrantyOption]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )
    bundle_options: Mapped[list[VariantBundleOption]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )
    return_policies: Mapped[list[VariantReturnPolicy]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[list[AttributeEvidence]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )

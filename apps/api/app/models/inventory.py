"""Inventory state for a single SKU."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin
from app.models.product import ProductVariant


class InventoryRecord(UUIDPrimaryKeyMixin, Base):
    """Warehouse on-hand and reserved units for one variant."""

    __tablename__ = "inventory_records"
    __table_args__ = (
        CheckConstraint(
            "units_available >= 0", name="ck_inventory_available_nonnegative"
        ),
        CheckConstraint(
            "units_reserved >= 0", name="ck_inventory_reserved_nonnegative"
        ),
    )

    variant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    units_available: Mapped[int] = mapped_column(Integer, nullable=False)
    units_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warehouse_code: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    variant: Mapped[ProductVariant] = relationship(back_populates="inventory")

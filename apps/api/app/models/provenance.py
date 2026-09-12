"""Provenance metadata. Cryptographic proof is not part of Stage 1."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.product import ProductVariant


class DataSource(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Origin of a merchant or product fact."""

    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reference: Mapped[str | None] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text)

    evidence: Mapped[list["AttributeEvidence"]] = relationship(
        back_populates="source",
    )


class AttributeEvidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A single observed attribute value and its source."""

    __tablename__ = "attribute_evidence"

    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        index=True,
    )
    attribute_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_reference: Mapped[str | None] = mapped_column(String(240))
    confidence: Mapped[float | None] = mapped_column(Float)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    variant: Mapped[ProductVariant | None] = relationship(back_populates="evidence")
    source: Mapped[DataSource] = relationship(back_populates="evidence")

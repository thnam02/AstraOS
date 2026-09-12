"""Persisted qualification runs. Offer candidates are not stored here."""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class QualificationRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One parsed intent plus the catalogue scan that followed."""

    __tablename__ = "qualification_runs"
    __table_args__ = (
        {"comment": "Intent qualification traces. Not offer or outcome records."},
    )

    raw_intent: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parser_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    variant_results: Mapped[list["QualificationVariantResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class QualificationVariantResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Per-SKU condition trace for a qualification run."""

    __tablename__ = "qualification_variant_results"
    __table_args__ = (
        UniqueConstraint("run_id", "variant_id", name="uq_qualification_run_variant"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("qualification_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    variant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(120))
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    violated_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unknown_count: Mapped[int] = mapped_column(Integer, nullable=False)
    satisfied_count: Mapped[int] = mapped_column(Integer, nullable=False)
    exclusion_reasons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    evaluations: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)

    run: Mapped[QualificationRun] = relationship(back_populates="variant_results")

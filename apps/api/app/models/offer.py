"""Persisted offer construction runs. No optimisation fields."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class OfferConstructionRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One intent's constructed offer space."""

    __tablename__ = "offer_construction_runs"

    match_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL")
    )
    raw_intent: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    construction_version: Mapped[str] = mapped_column(String(32), nullable=False)
    top_product_count: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_candidates: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_offer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    feasible_offer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_offer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pruning_reason: Mapped[str | None] = mapped_column(String(80))
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rejection_distribution: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    timing: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    construction_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    offers: Mapped[list["OfferCandidateRow"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class OfferCandidateRow(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One constructed commercial configuration."""

    __tablename__ = "offer_candidates"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_construction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    variant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    construction_status: Mapped[str] = mapped_column(String(24), nullable=False)
    feasibility_status: Mapped[str] = mapped_column(
        String(24), nullable=False, index=True
    )
    delivery_code: Mapped[str] = mapped_column(String(32), nullable=False)
    warranty_code: Mapped[str] = mapped_column(String(32), nullable=False)
    bundle_code: Mapped[str | None] = mapped_column(String(32))
    return_policy_code: Mapped[str | None] = mapped_column(String(32))
    final_product_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_customer_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    direct_intervention_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reasons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    run: Mapped[OfferConstructionRun] = relationship(back_populates="offers")

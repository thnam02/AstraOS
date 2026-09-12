"""Persisted optimisation runs. No negotiation or checkout."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class OptimisationRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One merchant-economics / Pareto pass over an offer space."""

    __tablename__ = "optimisation_runs"

    offer_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offer_construction_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL")
    )
    buyer_profile: Mapped[str] = mapped_column(String(40), nullable=False)
    weight_configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    merchant_policy_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    merchant_policy_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    total_offers: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_safe_offers: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_rejected_offers: Mapped[int] = mapped_column(Integer, nullable=False)
    pareto_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    selection_rule: Mapped[str] = mapped_column(String(40), nullable=False)
    selection_alpha: Mapped[str] = mapped_column(String(16), nullable=False)
    merchant_objective: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw_intent: Mapped[str] = mapped_column(Text, nullable=False)
    timing: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    buyer_model: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    recommended: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    pareto_offers: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    plot_points: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    counterfactuals: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    comparisons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    failure: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

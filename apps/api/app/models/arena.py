"""Persisted Arena duels and synthetic benchmarks. Not training data yet."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ArenaRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "arena_runs"

    mission_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    buyer_profile: Mapped[str] = mapped_column(String(40), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    buyer_selected_strategy: Mapped[str | None] = mapped_column(String(40))
    buyer_selected_offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    no_purchase: Mapped[bool] = mapped_column(nullable=False)
    mission: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    strategy_responses: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    selection: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    events: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    benchmark_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("arena_benchmark_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


class ArenaBenchmarkRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "arena_benchmark_runs"

    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    mission_count: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy_names: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    buyer_model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    merchant_policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    events: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    strategy_metrics: Mapped[list["ArenaStrategyMetrics"]] = relationship(
        back_populates="benchmark",
        cascade="all, delete-orphan",
    )
    segment_metrics: Mapped[list["ArenaSegmentMetrics"]] = relationship(
        back_populates="benchmark",
        cascade="all, delete-orphan",
    )


class ArenaStrategyMetrics(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "arena_strategy_metrics"

    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("arena_benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy_name: Mapped[str] = mapped_column(String(40), nullable=False)
    missions: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_rate: Mapped[str] = mapped_column(String(24), nullable=False)
    avg_buyer_utility: Mapped[str | None] = mapped_column(String(24))
    avg_contribution_when_selected: Mapped[str | None] = mapped_column(String(24))
    contribution_per_opportunity: Mapped[str] = mapped_column(
        String(24), nullable=False
    )
    avg_intervention_cost: Mapped[str | None] = mapped_column(String(24))
    hard_constraint_violation_rate: Mapped[str] = mapped_column(
        String(24), nullable=False
    )
    policy_violation_rate: Mapped[str] = mapped_column(String(24), nullable=False)
    no_offer_rate: Mapped[str] = mapped_column(String(24), nullable=False)
    transaction_completion_rate: Mapped[str] = mapped_column(
        String(24), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    benchmark: Mapped[ArenaBenchmarkRun] = relationship(
        back_populates="strategy_metrics"
    )


class ArenaSegmentMetrics(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "arena_segment_metrics"

    benchmark_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("arena_benchmark_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_tag: Mapped[str] = mapped_column(String(40), nullable=False)
    buyer_profile: Mapped[str] = mapped_column(String(40), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(40), nullable=False)
    missions: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    selection_rate: Mapped[str] = mapped_column(String(24), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    benchmark: Mapped[ArenaBenchmarkRun] = relationship(
        back_populates="segment_metrics"
    )

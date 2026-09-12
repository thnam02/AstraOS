"""Learning registry. Artifacts live on disk; rows are metadata only."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class CommerceInteraction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "commerce_interactions"

    intent_request_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    qualification_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    match_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    offer_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    optimisation_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    negotiation_session_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    arena_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    group_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    buyer_profile: Mapped[str | None] = mapped_column(String(40))
    structured_intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    offer_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    product_fit: Mapped[str] = mapped_column(String(24), nullable=False)
    total_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery: Mapped[str | None] = mapped_column(String(40))
    warranty: Mapped[str | None] = mapped_column(String(40))
    bundle: Mapped[str | None] = mapped_column(String(40))
    returns: Mapped[str | None] = mapped_column(String(40))
    merchant_contribution_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    intervention_cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome_type: Mapped[str] = mapped_column(String(32), nullable=False)
    selected: Mapped[bool | None] = mapped_column(nullable=True)
    accepted: Mapped[bool | None] = mapped_column(nullable=True)
    transacted: Mapped[bool | None] = mapped_column(nullable=True)
    outcome_source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    policy_safe: Mapped[bool] = mapped_column(nullable=False)
    hard_constraints_satisfied: Mapped[bool] = mapped_column(nullable=False)
    buyer_utility: Mapped[str | None] = mapped_column(String(24))
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    interaction_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )


class LearningDatasetVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "learning_dataset_versions"

    source_types: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    positive_count: Mapped[int] = mapped_column(Integer, nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ModelTrainingRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "model_training_runs"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    algorithms: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    results: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ResponseModelVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "response_model_versions"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    training_data_source: Mapped[str] = mapped_column(String(64), nullable=False)
    training_dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    train_size: Mapped[int] = mapped_column(Integer, nullable=False)
    validation_size: Mapped[int] = mapped_column(Integer, nullable=False)
    test_size: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    training_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_training_runs.id", ondelete="SET NULL")
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("learning_dataset_versions.id", ondelete="SET NULL")
    )
    model_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

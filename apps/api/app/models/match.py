"""Persisted semantic match runs. Offers are not stored here."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class MatchRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One deep-intent parse plus ranked eligible matches."""

    __tablename__ = "match_runs"

    raw_intent: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parser_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(80), nullable=False)
    semantic_document_version: Mapped[str] = mapped_column(String(64), nullable=False)
    qualification_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    timing: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    eligible_variant_ids: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)

    matches: Mapped[list["MatchResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class MatchResult(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One ranked eligible variant for a match run."""

    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("run_id", "variant_id", name="uq_match_run_variant"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("match_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    variant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    run: Mapped[MatchRun] = relationship(back_populates="matches")

"""Persisted B2A negotiation sessions. No checkout or payment."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class NegotiationSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "negotiation_sessions"

    initial_intent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL")
    )
    match_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL")
    )
    offer_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offer_construction_runs.id", ondelete="SET NULL")
    )
    optimisation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("optimisation_runs.id", ondelete="SET NULL")
    )
    current_offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    current_proposal_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    current_state: Mapped[str] = mapped_column(String(40), nullable=False)
    buyer_agent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    buyer_profile: Mapped[str] = mapped_column(String(40), nullable=False)
    merchant_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    original_intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    working_intent: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    delta_history: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    events: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    raw_intent: Mapped[str] = mapped_column(Text, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    turns: Mapped[list["NegotiationTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="NegotiationTurn.turn_number",
    )
    proposals: Mapped[list["MerchantProposal"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MerchantProposal.version",
    )


class NegotiationTurn(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "negotiation_turns"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(24), nullable=False)
    raw_message: Mapped[str | None] = mapped_column(Text)
    structured_action: Mapped[str] = mapped_column(String(40), nullable=False)
    structured_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    related_offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    related_proposal_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    session: Mapped[NegotiationSession] = relationship(back_populates="turns")


class MerchantProposal(UUIDPrimaryKeyMixin, Base):
    """Immutable merchant proposal. Never updated in place."""

    __tablename__ = "merchant_proposals"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("negotiation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    offer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    optimisation_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    offer_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason_codes: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    next_allowed_actions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    compromise: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    session: Mapped[NegotiationSession] = relationship(back_populates="proposals")

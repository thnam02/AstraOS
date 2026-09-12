"""Negotiation persistence. No commercial decisions here."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.negotiation import (
    NegotiationSession,
)


class NegotiationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_session(self, row: NegotiationSession) -> NegotiationSession:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get(self, session_id: UUID) -> NegotiationSession | None:
        result = await self.session.execute(
            select(NegotiationSession)
            .where(NegotiationSession.id == session_id)
            .options(
                selectinload(NegotiationSession.turns),
                selectinload(NegotiationSession.proposals),
            )
        )
        return result.scalar_one_or_none()

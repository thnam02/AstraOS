"""Persistence for offer construction runs."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.offer import OfferCandidateRow, OfferConstructionRun


class OfferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_run(self, run: OfferConstructionRun) -> OfferConstructionRun:
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_run(self, run_id: uuid.UUID) -> OfferConstructionRun | None:
        stmt = (
            select(OfferConstructionRun)
            .options(selectinload(OfferConstructionRun.offers))
            .where(OfferConstructionRun.id == run_id)
        )
        result = await self.session.scalars(stmt)
        return result.unique().one_or_none()

    async def get_offer(self, offer_id: uuid.UUID) -> OfferCandidateRow | None:
        result = await self.session.scalars(
            select(OfferCandidateRow).where(OfferCandidateRow.id == offer_id)
        )
        return result.one_or_none()

    def _filtered(
        self,
        run_id: uuid.UUID,
        *,
        product_id: uuid.UUID | None = None,
        delivery_code: str | None = None,
        warranty_code: str | None = None,
        bundle_code: str | None = None,
        return_policy_code: str | None = None,
        max_price_cents: int | None = None,
        status: str | None = None,
    ) -> Select[tuple[OfferCandidateRow]]:
        stmt = select(OfferCandidateRow).where(OfferCandidateRow.run_id == run_id)
        if product_id:
            stmt = stmt.where(OfferCandidateRow.product_id == product_id)
        if delivery_code:
            stmt = stmt.where(OfferCandidateRow.delivery_code == delivery_code)
        if warranty_code:
            stmt = stmt.where(OfferCandidateRow.warranty_code == warranty_code)
        if bundle_code == "NONE":
            stmt = stmt.where(OfferCandidateRow.bundle_code.is_(None))
        elif bundle_code:
            stmt = stmt.where(OfferCandidateRow.bundle_code == bundle_code)
        if return_policy_code:
            stmt = stmt.where(
                OfferCandidateRow.return_policy_code == return_policy_code
            )
        if max_price_cents is not None:
            stmt = stmt.where(
                OfferCandidateRow.total_customer_price_cents <= max_price_cents
            )
        if status and status != "ALL":
            stmt = stmt.where(OfferCandidateRow.feasibility_status == status)
        return stmt

    async def list_offers(
        self,
        run_id: uuid.UUID,
        *,
        product_id: uuid.UUID | None = None,
        delivery_code: str | None = None,
        warranty_code: str | None = None,
        bundle_code: str | None = None,
        return_policy_code: str | None = None,
        max_price_cents: int | None = None,
        status: str | None = "FEASIBLE",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[OfferCandidateRow], int]:
        filters: dict[str, Any] = {
            "product_id": product_id,
            "delivery_code": delivery_code,
            "warranty_code": warranty_code,
            "bundle_code": bundle_code,
            "return_policy_code": return_policy_code,
            "max_price_cents": max_price_cents,
            "status": status,
        }
        base = self._filtered(run_id, **filters)
        total = int(
            await self.session.scalar(select(func.count()).select_from(base.subquery()))
            or 0
        )
        rows = await self.session.scalars(
            base.order_by(
                OfferCandidateRow.sku,
                OfferCandidateRow.total_customer_price_cents,
                OfferCandidateRow.delivery_code,
                OfferCandidateRow.warranty_code,
                OfferCandidateRow.bundle_code,
            )
            .limit(limit)
            .offset(offset)
        )
        return rows.all(), total

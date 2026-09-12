"""Merchant objective configuration. Does not score offers."""

from __future__ import annotations

from decimal import Decimal
from typing import cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.optimisation.objective import (
    MODE_BLURBS,
    MerchantObjectiveConfig,
    ObjectiveMode,
    default_objective,
    resolve_objective,
)
from app.models import Merchant, MerchantObjective
from app.repositories.objective import MerchantObjectiveRepository
from app.schemas.objective import (
    MerchantObjectiveResponse,
    MerchantObjectiveUpdate,
    preset_catalog,
)


class ObjectiveValidationError(ValueError):
    """Invalid merchant objective update."""


class MerchantObjectiveService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = MerchantObjectiveRepository(session)

    async def get_active(self) -> MerchantObjectiveResponse:
        row = await self.repository.get_active()
        if row is None:
            config = default_objective()
            row = await self._create_default(config)
        return self._to_response(row)

    async def active_config(self) -> MerchantObjectiveConfig:
        row = await self.repository.get_active()
        if row is None:
            return default_objective()
        return MerchantObjectiveConfig(
            mode=cast(ObjectiveMode, row.mode),
            buyer_weight=float(row.buyer_weight),
            merchant_weight=float(row.merchant_weight),
            version=row.version,
        )

    async def update(
        self, payload: MerchantObjectiveUpdate
    ) -> MerchantObjectiveResponse:
        try:
            config = resolve_objective(
                mode=payload.mode,
                buyer_weight=payload.buyer_weight,
                merchant_weight=payload.merchant_weight,
            )
        except ValueError as exc:
            raise ObjectiveValidationError(str(exc)) from exc
        row = await self.repository.get_active()
        if row is None:
            row = await self._create_default(config)
        else:
            row.mode = config.mode
            row.buyer_weight = Decimal(str(config.buyer_weight))
            row.merchant_weight = Decimal(str(config.merchant_weight))
            row.version = config.version
            await self.repository.update_active(row)
        return self._to_response(row)

    async def _create_default(
        self, config: MerchantObjectiveConfig
    ) -> MerchantObjective:
        merchant = (
            await self.session.execute(select(Merchant).limit(1))
        ).scalars().first()
        if merchant is None:
            raise RuntimeError("No merchant exists.")
        row = MerchantObjective(
            id=uuid4(),
            merchant_id=merchant.id,
            mode=config.mode,
            buyer_weight=Decimal(str(config.buyer_weight)),
            merchant_weight=Decimal(str(config.merchant_weight)),
            version=config.version,
            is_active=True,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    def _to_response(self, row: MerchantObjective) -> MerchantObjectiveResponse:
        return MerchantObjectiveResponse(
            id=row.id,
            merchant_id=row.merchant_id,
            mode=cast(ObjectiveMode, row.mode),
            buyer_weight=float(row.buyer_weight),
            merchant_weight=float(row.merchant_weight),
            version=row.version,
            label=MerchantObjectiveConfig(
                mode=cast(ObjectiveMode, row.mode),
                buyer_weight=float(row.buyer_weight),
                merchant_weight=float(row.merchant_weight),
            ).label(),
            blurb=MODE_BLURBS.get(row.mode, MODE_BLURBS["BALANCED"]),
            presets=preset_catalog(),
            is_active=row.is_active,
            updated_at=row.updated_at,
        )

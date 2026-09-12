"""End-to-end decision orchestration. Reuses existing services."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.optimisation.models import DEFAULT_ALPHA
from app.schemas.match import MatchResponse
from app.schemas.offer import GenerateOffersResponse
from app.schemas.optimisation import DecisionRequest, OptimisationResponse
from app.services.matching import SemanticMatchingService
from app.services.offers import OfferConstructionService
from app.services.optimisation import OptimisationService


class DecisionResponse(BaseModel):
    match: MatchResponse
    construction: GenerateOffersResponse
    optimisation: OptimisationResponse


class DecisionService:
    def __init__(self, session: AsyncSession) -> None:
        self.matching = SemanticMatchingService(session)
        self.offers = OfferConstructionService(session)
        self.optimisation = OptimisationService(session)

    async def run(self, payload: DecisionRequest) -> DecisionResponse:
        matched = await self.matching.match(
            payload.intent, payload.parser_mode, limit=payload.max_products
        )
        construction = await self.offers.generate(
            intent_text=None,
            match_run_id=matched.run_id,
            parser_mode=payload.parser_mode,
            max_products=payload.max_products,
            preview_status="FEASIBLE",
            preview_limit=40,
        )
        optimisation = await self.optimisation.run(
            construction.offer_run_id,
            buyer_profile=payload.buyer_profile,
            alpha=payload.alpha if payload.alpha is not None else DEFAULT_ALPHA,
        )
        return DecisionResponse(
            match=matched,
            construction=construction,
            optimisation=optimisation,
        )

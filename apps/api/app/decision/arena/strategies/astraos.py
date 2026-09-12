"""Reuse the live Stage 5 Pareto selection. Do not reimplement AstraOS."""

from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.arena.strategies.common import (
    cheapest_safe_id,
    empty_response,
    offer_by_id,
    scored_by_id,
    to_response,
)


class AstraOSStrategy:
    name = "ASTRAOS"

    def generate_response(self, context: ArenaContext) -> StrategyResponse:
        if context.recommended_offer_id is None:
            return empty_response(
                self.name,
                context.optimisation_failure or "NO_POLICY_SAFE_OFFER",
            )
        key = str(context.recommended_offer_id)
        scored = scored_by_id(context)[key]
        offer = offer_by_id(context)[key]
        cheapest = cheapest_safe_id(context)
        return to_response(
            self.name,
            scored,
            offer,
            used_pareto=True,
            used_max_discount=False,
            is_cheapest_in_space=cheapest == key,
        )

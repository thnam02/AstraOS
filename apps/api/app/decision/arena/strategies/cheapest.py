"""Lowest customer-price policy-safe configuration. No utility search."""

from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.arena.strategies.common import (
    cheapest_safe_id,
    empty_response,
    offer_by_id,
    scored_by_id,
    to_response,
)


class CheapestEligibleStrategy:
    name = "CHEAPEST_ELIGIBLE"

    def generate_response(self, context: ArenaContext) -> StrategyResponse:
        offer_id = cheapest_safe_id(context)
        if offer_id is None:
            return empty_response(self.name, "NO_POLICY_SAFE_OFFER")
        scored = scored_by_id(context)[offer_id]
        offer = offer_by_id(context)[offer_id]
        return to_response(
            self.name,
            scored,
            offer,
            used_pareto=False,
            used_max_discount=False,
            is_cheapest_in_space=True,
        )

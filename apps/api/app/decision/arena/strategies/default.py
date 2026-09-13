"""Highest-ranked eligible product with the conceptual default offer.

DEFAULT already uses semantic ranking (`top_match_variant`). It does not
search commercial combinations and does not use Pareto. Because of that,
Default → Semantic Only does not isolate semantic search; it isolates
the same product plus the same default terms. Leave the definition
unchanged so the ablation reports what the code actually does.
"""

from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.arena.strategies.common import (
    baseline_pair,
    cheapest_safe_id,
    empty_response,
    to_response,
    top_match_variant,
)


class DefaultMerchantStrategy:
    name = "DEFAULT"

    def generate_response(self, context: ArenaContext) -> StrategyResponse:
        variant_id = top_match_variant(context)
        if variant_id is None:
            return empty_response(self.name, "NO_ELIGIBLE_PRODUCT")
        pair = baseline_pair(context, variant_id)
        if pair is None:
            return empty_response(self.name, "NO_BASELINE_CONFIGURATION")
        scored, offer = pair
        cheapest = cheapest_safe_id(context)
        return to_response(
            self.name,
            scored,
            offer,
            used_pareto=False,
            used_max_discount=False,
            is_cheapest_in_space=cheapest == str(scored.offer_id),
        )

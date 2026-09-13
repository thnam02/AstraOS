"""Top semantic product with that product's default commercial terms.

Does not search price / delivery / warranty / bundle / returns combinations
and does not use Pareto selection. Isolates product-matching value.
"""

from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.arena.strategies.common import (
    baseline_pair,
    cheapest_safe_id,
    empty_response,
    to_response,
    top_match_variant,
)


class SemanticOnlyStrategy:
    name = "SEMANTIC_ONLY"

    def generate_response(self, context: ArenaContext) -> StrategyResponse:
        # Must never reuse context.recommended_offer_id. That offer is the
        # AstraOS Pareto/objective selection. This strategy isolates matching.
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

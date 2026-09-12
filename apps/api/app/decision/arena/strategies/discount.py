"""Same default product, maximum policy-safe promotional discount."""

from decimal import Decimal

from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.arena.strategies.common import (
    cheapest_safe_id,
    default_dims,
    empty_response,
    scored_by_id,
    to_response,
    top_match_variant,
)


class AlwaysDiscountStrategy:
    name = "ALWAYS_DISCOUNT"

    def generate_response(self, context: ArenaContext) -> StrategyResponse:
        variant_id = top_match_variant(context)
        if variant_id is None:
            return empty_response(self.name, "NO_ELIGIBLE_PRODUCT")
        lookup = scored_by_id(context)
        candidates = []
        for offer in context.offers:
            if offer.variant_id != variant_id or not default_dims(offer):
                continue
            if offer.price_adjustment_type != "DISCOUNT":
                continue
            scored = lookup.get(str(offer.id))
            if scored is None:
                continue
            candidates.append((offer.price_adjustment_rate, scored, offer))
        if not candidates:
            return empty_response(self.name, "NO_DISCOUNT_CONFIGURATION")
        safe = [item for item in candidates if item[1].policy.policy_safe]
        pool = safe or candidates
        rate, scored, offer = max(pool, key=lambda item: item[0])
        cap = Decimal(str(context.policy_max_discount))
        used_max = bool(safe) and rate == max(item[0] for item in safe) and rate <= cap
        cheapest = cheapest_safe_id(context)
        return to_response(
            self.name,
            scored,
            offer,
            used_pareto=False,
            used_max_discount=used_max,
            is_cheapest_in_space=cheapest == str(scored.offer_id),
        )

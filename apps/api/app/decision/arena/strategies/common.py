"""Shared mapping from the scored space onto StrategyResponse."""

from uuid import UUID

from app.decision.arena.config import STRATEGY_VERSIONS
from app.decision.arena.models import ArenaContext, StrategyResponse
from app.decision.offers.models import FeasibilityStatus, OfferCandidate
from app.decision.optimisation.baseline import (
    STANDARD_DELIVERY,
    STANDARD_RETURNS,
    STANDARD_WARRANTY,
    is_conceptual_baseline,
)
from app.decision.optimisation.models import ScoredOffer


def scored_by_id(context: ArenaContext) -> dict[str, ScoredOffer]:
    return {str(item.offer_id): item for item in context.scored}


def offer_by_id(context: ArenaContext) -> dict[str, OfferCandidate]:
    return {str(item.id): item for item in context.offers}


_BUYER_PRICE_CODES = {
    "BUYER_MAX_TOTAL_EXCEEDED",
    "BUYER_MAX_PRODUCT_PRICE_EXCEEDED",
}


def hard_ok(scored: ScoredOffer, offer: OfferCandidate) -> bool:
    if not scored.all_mandatory_buyer_constraints_satisfied:
        return False
    codes = set(scored.policy.rejection_codes) | set(scored.buyer_constraint_codes)
    if codes & _BUYER_PRICE_CODES:
        return False
    if scored.policy.policy_safe:
        return True
    delivery_ok = "INTENT_DELIVERY_INCOMPATIBLE" not in codes
    return offer.feasibility_status == FeasibilityStatus.FEASIBLE and delivery_ok


_STATUS = {
    "NO_ELIGIBLE_PRODUCT": "NO_ELIGIBLE_PRODUCT",
    "NO_POLICY_SAFE_OFFER": "NO_POLICY_SAFE_OFFER",
    "NO_BASELINE_CONFIGURATION": "NO_VALID_DEFAULT_CONFIGURATION",
    "NO_DISCOUNT_CONFIGURATION": "NO_VALID_DEFAULT_CONFIGURATION",
    "HARD_CONSTRAINT_VIOLATION": "HARD_CONSTRAINT_VIOLATION",
}


def empty_response(name: str, reason: str) -> StrategyResponse:
    return StrategyResponse(
        strategy_name=name,
        hard_constraints_satisfied=False,
        policy_safe=False,
        transaction_possible=False,
        failure_reason=reason,
        status=_STATUS.get(reason, "ERROR"),
        selectable=False,
        strategy_version=STRATEGY_VERSIONS.get(name, "v1"),
    )


def to_response(
    name: str,
    scored: ScoredOffer,
    offer: OfferCandidate,
    *,
    used_pareto: bool = False,
    used_max_discount: bool = False,
    is_cheapest_in_space: bool = False,
) -> StrategyResponse:
    constraints = hard_ok(scored, offer)
    safe = scored.policy.policy_safe
    selectable = bool(
        constraints and safe and scored.all_mandatory_buyer_constraints_satisfied
    )
    if not constraints:
        status = "HARD_CONSTRAINT_VIOLATION"
    elif not safe:
        status = "NO_POLICY_SAFE_OFFER"
    else:
        status = "VALID"
    return StrategyResponse(
        strategy_name=name,
        product_id=offer.product_id,
        variant_id=offer.variant_id,
        offer_id=scored.offer_id,
        sku=scored.sku,
        product_name=scored.product_name,
        total_customer_price_cents=scored.total_customer_price_cents,
        currency=scored.currency,
        delivery=scored.delivery_code,
        delivery_days=scored.delivery_days,
        warranty=scored.warranty_code,
        warranty_months=scored.warranty_months,
        bundle=scored.bundle_code,
        returns=scored.return_policy_code,
        buyer_utility=scored.utility.score,
        merchant_contribution_cents=scored.economics.contribution_margin_cents,
        intervention_cost_cents=(
            scored.economics.incremental_intervention_cost_cents
        ),
        hard_constraints_satisfied=constraints,
        policy_safe=safe,
        transaction_possible=selectable,
        failure_reason=None
        if selectable
        else ",".join(scored.policy.rejection_codes) or "UNSAFE_OR_INFEASIBLE",
        utility_trace=scored.utility.trace,
        used_pareto=used_pareto,
        used_max_discount=used_max_discount,
        is_cheapest_in_space=is_cheapest_in_space,
        status=status,
        selectable=selectable,
        strategy_version=STRATEGY_VERSIONS.get(name, "v1"),
        commercial_intervention_count=_intervention_count(scored),
    )


def _intervention_count(scored: ScoredOffer) -> int:
    count = 0
    if scored.delivery_code != STANDARD_DELIVERY:
        count += 1
    if scored.warranty_code != STANDARD_WARRANTY:
        count += 1
    if scored.bundle_code:
        count += 1
    if scored.return_policy_code not in {None, STANDARD_RETURNS}:
        count += 1
    if scored.total_customer_price_cents != scored.product_price_cents:
        count += 1
    return count


def top_match_variant(context: ArenaContext) -> UUID | None:
    if not context.matches:
        return None
    return context.matches[0].variant_id


def baseline_pair(
    context: ArenaContext, variant_id: UUID
) -> tuple[ScoredOffer, OfferCandidate] | None:
    lookup = scored_by_id(context)
    for offer in context.offers:
        if offer.variant_id != variant_id or not is_conceptual_baseline(offer):
            continue
        scored = lookup.get(str(offer.id))
        if scored is not None:
            return scored, offer
    return None


def default_dims(offer: OfferCandidate) -> bool:
    return (
        offer.delivery_code == STANDARD_DELIVERY
        and offer.warranty_code == STANDARD_WARRANTY
        and offer.bundle_code is None
        and (offer.return_policy_code in {None, STANDARD_RETURNS})
    )


def cheapest_safe_id(context: ArenaContext) -> str | None:
    pairs: list[tuple[int, int, str, str]] = []
    lookup = offer_by_id(context)
    for scored in context.scored:
        offer = lookup.get(str(scored.offer_id))
        if offer is None or not scored.policy.policy_safe:
            continue
        if not hard_ok(scored, offer):
            continue
        pairs.append(
            (
                scored.total_customer_price_cents,
                scored.delivery_days,
                scored.sku,
                str(scored.offer_id),
            )
        )
    if not pairs:
        return None
    return min(pairs)[3]

"""Optimisation candidate gates. Hard constraints are not score terms."""

from __future__ import annotations

from app.decision.intent.models import ShoppingIntent
from app.decision.intent.price import max_customer_total_cents
from app.decision.optimisation.models import NearMissCandidate, ScoredOffer


def is_optimisation_candidate(item: ScoredOffer) -> bool:
    return (
        item.feasible
        and item.all_mandatory_buyer_constraints_satisfied
        and item.policy.policy_safe
    )


def mark_candidate_flags(item: ScoredOffer) -> ScoredOffer:
    allowed = is_optimisation_candidate(item)
    item.selectable = allowed
    item.pareto_eligible = allowed
    item.proposal_eligible = allowed
    if not allowed:
        item.is_pareto_efficient = False
        item.is_recommended = False
    return item


def ensure_selected_offer_compliant(offer: ScoredOffer | None) -> None:
    """Hard invariant: a selected offer must have passed every gate."""
    if offer is None:
        return
    if not offer.all_mandatory_buyer_constraints_satisfied:
        raise RuntimeError(
            "INVARIANT: selected_offer must satisfy all mandatory buyer constraints"
        )
    if not offer.policy.policy_safe:
        raise RuntimeError("INVARIANT: selected_offer must be merchant-policy-safe")
    if not offer.feasible:
        raise RuntimeError("INVARIANT: selected_offer must be feasible")


def pick_near_miss(
    scored: list[ScoredOffer],
    *,
    intent: ShoppingIntent,
) -> NearMissCandidate | None:
    """Closest merchant-safe configuration that still needs buyer relaxation."""
    pool = [
        item
        for item in scored
        if item.policy.policy_safe
        and item.feasible
        and not item.all_mandatory_buyer_constraints_satisfied
    ]
    if not pool:
        return None
    cap = max_customer_total_cents(intent)
    if cap is not None:
        over = [item for item in pool if item.total_customer_price_cents > cap]
        chosen = (
            min(over, key=lambda item: item.total_customer_price_cents)
            if over
            else min(pool, key=lambda item: item.total_customer_price_cents)
        )
        gap = max(0, chosen.total_customer_price_cents - cap)
    else:
        chosen = min(pool, key=lambda item: item.total_customer_price_cents)
        gap = None
    codes = list(chosen.buyer_constraint_codes)
    reason = (
        "Closest merchant-policy-safe configuration still violates a "
        "mandatory buyer constraint. It is not selectable until the buyer "
        "explicitly relaxes that constraint."
    )
    if codes:
        reason = f"{reason} Blocked by {', '.join(codes)}."
    return NearMissCandidate(
        offer_id=chosen.offer_id,
        product_name=chosen.product_name,
        sku=chosen.sku,
        total_customer_price_cents=chosen.total_customer_price_cents,
        currency=chosen.currency,
        gap_cents=gap,
        requested_max_price_cents=cap,
        blocked_codes=codes,
        reason=reason,
    )

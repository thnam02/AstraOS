"""Deterministic simulated buyer choice. Not a human abandonment model."""

from app.decision.arena.models import (
    STRATEGY_ORDER,
    BuyerSelection,
    StrategyResponse,
)


def choose_response(
    responses: list[StrategyResponse],
    *,
    outside_option_utility: float,
) -> BuyerSelection:
    """Highest utility wins. Ties: lower price, faster delivery, name order."""
    valid = [
        item
        for item in responses
        if item.policy_safe
        and item.hard_constraints_satisfied
        and item.buyer_utility is not None
        and item.offer_id is not None
    ]
    if not valid:
        return BuyerSelection(
            selected_strategy=None,
            no_purchase=True,
            reason="NO_VALID_OFFER",
        )
    ranked = sorted(
        valid,
        key=lambda item: (
            -(item.buyer_utility or 0),
            item.total_customer_price_cents or 10**12,
            item.delivery_days if item.delivery_days is not None else 99,
            STRATEGY_ORDER.index(item.strategy_name)
            if item.strategy_name in STRATEGY_ORDER
            else 99,
            item.strategy_name,
        ),
    )
    winner = ranked[0]
    assert winner.buyer_utility is not None
    if winner.buyer_utility < outside_option_utility:
        return BuyerSelection(
            selected_strategy=None,
            selected_offer_id=None,
            simulated_utility=winner.buyer_utility,
            no_purchase=True,
            reason="OUTSIDE_OPTION",
        )
    tied = [
        item
        for item in ranked
        if item.buyer_utility == winner.buyer_utility
        and item.total_customer_price_cents == winner.total_customer_price_cents
        and item.delivery_days == winner.delivery_days
    ]
    return BuyerSelection(
        selected_strategy=winner.strategy_name,
        selected_offer_id=winner.offer_id,
        simulated_utility=winner.buyer_utility,
        no_purchase=False,
        reason="HIGHEST_SIMULATED_UTILITY",
        tie_break="price_then_delivery_then_name" if len(tied) > 1 else None,
    )

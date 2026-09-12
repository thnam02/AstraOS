"""Transparent simulated Buyer Agent. Evaluation client, not AstraOS."""

from __future__ import annotations

from app.decision.negotiation.models import (
    BuyerAction,
    BuyerTurnInput,
    CounterConstraints,
)

SIMULATOR_MODES = (
    "BUDGET",
    "URGENT",
    "ASSURANCE",
    "BALANCED",
    "TRAVEL",
)


def simulate_buyer(
    *,
    mode: str,
    budget_cents: int | None,
    offer_price_cents: int,
    delivery_days: int,
    warranty_months: int,
    buyer_utility: float,
) -> BuyerTurnInput:
    """Visible decision table. Not a production consumer agent."""
    budget = budget_cents if budget_cents is not None else offer_price_cents
    key = mode.upper()
    if key == "BUDGET":
        if offer_price_cents <= budget and buyer_utility >= 0.50:
            return BuyerTurnInput(action=BuyerAction.ACCEPT, message="I'll take it.")
        if offer_price_cents > budget:
            return BuyerTurnInput(
                action=BuyerAction.COUNTER,
                constraints=CounterConstraints(max_total_price_cents=budget),
                message=f"Can you get this below A${budget / 100:.0f}?",
            )
        target = int(offer_price_cents * 0.95)
        return BuyerTurnInput(
            action=BuyerAction.COUNTER,
            constraints=CounterConstraints(max_total_price_cents=target),
            message=f"Can you do A${target / 100:.0f}?",
        )
    if key == "URGENT":
        if delivery_days == 0 and offer_price_cents <= budget:
            return BuyerTurnInput(action=BuyerAction.ACCEPT, message="I'll take it.")
        if delivery_days > 0:
            return BuyerTurnInput(
                action=BuyerAction.COUNTER,
                constraints=CounterConstraints(requested_delivery_days=0),
                message="I still need same-day delivery.",
            )
        return BuyerTurnInput(
            action=BuyerAction.COUNTER,
            constraints=CounterConstraints(max_total_price_cents=budget),
            message=f"Need it today, max A${budget / 100:.0f}.",
        )
    if key == "ASSURANCE":
        if warranty_months >= 24 and buyer_utility >= 0.50:
            return BuyerTurnInput(action=BuyerAction.ACCEPT, message="I'll take it.")
        return BuyerTurnInput(
            action=BuyerAction.COUNTER,
            constraints=CounterConstraints(requested_warranty_months=24),
            message="Can you give me a longer warranty?",
        )
    if key == "TRAVEL":
        if delivery_days == 0 and offer_price_cents <= budget:
            return BuyerTurnInput(action=BuyerAction.ACCEPT, message="I'll take it.")
        return BuyerTurnInput(
            action=BuyerAction.COUNTER,
            constraints=CounterConstraints(max_total_price_cents=min(budget, 31500)),
            message="Can you get this below A$315?",
        )
    if offer_price_cents <= budget and buyer_utility >= 0.60:
        return BuyerTurnInput(action=BuyerAction.ACCEPT, message="I'll take it.")
    if offer_price_cents > budget:
        return BuyerTurnInput(
            action=BuyerAction.COUNTER,
            constraints=CounterConstraints(max_total_price_cents=budget),
            message=f"Maximum A${budget / 100:.0f}.",
        )
    return BuyerTurnInput(action=BuyerAction.ACCEPT, message="I'll take it.")

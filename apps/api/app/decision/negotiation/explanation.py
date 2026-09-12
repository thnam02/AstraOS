"""Deterministic merchant-turn explanations. No LLM reasons."""

from __future__ import annotations

from decimal import Decimal

from app.decision.negotiation.models import (
    CounterConstraints,
    MerchantOutcome,
    ReasonCode,
)
from app.decision.optimisation.models import ScoredOffer


def money(cents: int) -> str:
    return f"A${cents / 100:.2f}"


def explain(
    *,
    outcome: MerchantOutcome,
    codes: list[ReasonCode],
    request: CounterConstraints,
    offer: ScoredOffer | None,
    previous: ScoredOffer | None,
    margin_floor: Decimal,
    prompt_injection: bool,
) -> list[str]:
    lines: list[str] = []
    floor_pct = f"{(margin_floor * 100):.0f}%"
    if prompt_injection:
        lines.append(
            "A buyer instruction that tried to override merchant policy was ignored."
        )
    if outcome == MerchantOutcome.CLARIFICATION_REQUIRED:
        lines.append(
            "The buyer message is not machine-actionable. "
            "Specify a price, delivery, warranty, bundle, or product change."
        )
        return lines
    if outcome == MerchantOutcome.DECLINE:
        lines.append("No policy-safe configuration exists for this request.")
        if request.max_total_price_cents is not None:
            lines.append(
                f"{money(request.max_total_price_cents)} cannot be offered "
                f"without violating the {floor_pct} margin floor or other "
                "merchant rules."
            )
        lines.append("AstraOS will not invent an unsafe deal.")
        return lines
    if offer is None:
        return lines
    if ReasonCode.ORIGINAL_CONSTRAINTS_RETAINED in codes:
        lines.append(
            "Original hard requirements remain in force unless the buyer "
            "explicitly changed them."
        )
    if outcome == MerchantOutcome.ACCEPT_BUYER_COUNTER:
        lines.append(
            "A policy-safe offer satisfies the buyer counter on this product."
        )
        lines.append(
            f"Selected {offer.product_name} at "
            f"{money(offer.total_customer_price_cents)}."
        )
    if outcome == MerchantOutcome.COUNTEROFFER:
        if (
            request.max_total_price_cents is not None
            and offer.total_customer_price_cents > request.max_total_price_cents
        ):
            lines.append(
                f"{money(request.max_total_price_cents)} cannot be reached "
                f"without violating the {floor_pct} margin floor."
            )
        lines.append(
            f"{money(offer.total_customer_price_cents)} is the closest "
            "policy-safe response for this product."
        )
        lines.append(f"Delivery remains {offer.delivery_name}.")
    if outcome == MerchantOutcome.ALTERNATIVE_PRODUCT:
        if previous is not None:
            lines.append(
                f"{previous.product_name} cannot meet the new request safely."
            )
        lines.append(
            f"Alternative: {offer.product_name} at "
            f"{money(offer.total_customer_price_cents)}."
        )
    if previous is not None and previous.offer_id != offer.offer_id:
        price_delta = (
            offer.total_customer_price_cents - previous.total_customer_price_cents
        )
        if price_delta:
            sign = "+" if price_delta > 0 else "-"
            lines.append(
                f"Price changed {sign}{money(abs(price_delta))} versus "
                "the previous proposal."
            )
    return lines


def next_actions(outcome: MerchantOutcome) -> list[str]:
    if outcome in {
        MerchantOutcome.DECLINE,
        MerchantOutcome.NEGOTIATION_LIMIT_REACHED,
    }:
        return ["REJECT", "COUNTER"]
    if outcome == MerchantOutcome.CLARIFICATION_REQUIRED:
        return ["ACCEPT", "REJECT", "COUNTER"]
    if outcome == MerchantOutcome.PROPOSAL_EXPIRED:
        return ["COUNTER", "REJECT"]
    return ["ACCEPT", "REJECT", "COUNTER"]

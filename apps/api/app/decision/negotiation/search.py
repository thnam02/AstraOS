"""Deterministic counteroffer search. No LLM judgment."""

from __future__ import annotations

from uuid import UUID

from app.decision.negotiation.models import (
    CompromiseBreakdown,
    CounterConstraints,
    MerchantOutcome,
    ProposalType,
    ReasonCode,
)
from app.decision.optimisation.candidates import is_optimisation_candidate
from app.decision.optimisation.models import ScoredOffer
from app.decision.optimisation.objective import MerchantObjectiveConfig
from app.decision.optimisation.selection import select_offer


def meets_request(offer: ScoredOffer, request: CounterConstraints) -> bool:
    if (
        request.max_total_price_cents is not None
        and offer.total_customer_price_cents > request.max_total_price_cents
    ):
        return False
    days = request.requested_delivery_days
    if days is not None and offer.delivery_days > days:
        return False
    months = request.requested_warranty_months
    if months is not None and offer.warranty_months < months:
        return False
    if request.requested_bundle and offer.bundle_code != request.requested_bundle:
        return False
    if request.requested_return_window_days is not None:
        window = offer.return_window_days or 0
        if window < request.requested_return_window_days:
            return False
    return True


def compromise(
    offer: ScoredOffer,
    request: CounterConstraints,
    *,
    price_w: float = 0.40,
    delivery_w: float = 0.25,
    warranty_w: float = 0.15,
    bundle_w: float = 0.10,
    returns_w: float = 0.10,
) -> CompromiseBreakdown:
    """Lower score is closer to the buyer request. 0 is an exact match."""
    total = price_w + delivery_w + warranty_w + bundle_w + returns_w
    price_w, delivery_w, warranty_w, bundle_w, returns_w = (
        price_w / total,
        delivery_w / total,
        warranty_w / total,
        bundle_w / total,
        returns_w / total,
    )
    price_gap = 0.0
    if request.max_total_price_cents:
        over = max(0, offer.total_customer_price_cents - request.max_total_price_cents)
        price_gap = over / request.max_total_price_cents
    delivery_gap = 0.0
    if request.requested_delivery_days is not None:
        extra = max(0, offer.delivery_days - request.requested_delivery_days)
        delivery_gap = min(1.0, extra / 7)
    warranty_gap = 0.0
    if request.requested_warranty_months:
        short = max(0, request.requested_warranty_months - offer.warranty_months)
        warranty_gap = min(1.0, short / request.requested_warranty_months)
    bundle_gap = 0.0
    if request.requested_bundle:
        bundle_gap = 0.0 if offer.bundle_code == request.requested_bundle else 1.0
    returns_gap = 0.0
    if request.requested_return_window_days:
        window = offer.return_window_days or 0
        short = max(0, request.requested_return_window_days - window)
        returns_gap = min(1.0, short / request.requested_return_window_days)
    score = (
        price_w * price_gap
        + delivery_w * delivery_gap
        + warranty_w * warranty_gap
        + bundle_w * bundle_gap
        + returns_w * returns_gap
    )
    return CompromiseBreakdown(
        price_gap=round(price_gap, 6),
        delivery_gap=round(delivery_gap, 6),
        warranty_gap=round(warranty_gap, 6),
        bundle_gap=round(bundle_gap, 6),
        returns_gap=round(returns_gap, 6),
        score=round(score, 6),
        formula=(
            "0.40*price_gap + 0.25*delivery_gap + 0.15*warranty_gap "
            "+ 0.10*bundle_gap + 0.10*returns_gap"
        ),
    )


def _pick(
    candidates: list[ScoredOffer],
    objective: MerchantObjectiveConfig | None = None,
) -> ScoredOffer | None:
    if not candidates:
        return None
    frontier = [item for item in candidates if item.is_pareto_efficient]
    pool = frontier or candidates
    winner, _score = select_offer(pool, objective=objective)
    return winner


class SearchResult:
    def __init__(
        self,
        *,
        outcome: MerchantOutcome,
        proposal_type: ProposalType,
        offer: ScoredOffer | None,
        reason_codes: list[ReasonCode],
        compromise_row: CompromiseBreakdown | None,
    ) -> None:
        self.outcome = outcome
        self.proposal_type = proposal_type
        self.offer = offer
        self.reason_codes = reason_codes
        self.compromise = compromise_row


def search_counter(
    scored: list[ScoredOffer],
    *,
    request: CounterConstraints,
    current_variant_id: UUID | None,
    objective: MerchantObjectiveConfig | None = None,
) -> SearchResult:
    safe = [item for item in scored if is_optimisation_candidate(item)]
    if not safe:
        return SearchResult(
            outcome=MerchantOutcome.DECLINE,
            proposal_type=ProposalType.COUNTER,
            offer=None,
            reason_codes=[ReasonCode.NO_COMPLIANT_OFFER],
            compromise_row=None,
        )

    matching = [item for item in safe if meets_request(item, request)]
    same_ok = [
        item
        for item in matching
        if current_variant_id is None or item.variant_id == current_variant_id
    ]
    other_ok = [
        item
        for item in matching
        if current_variant_id is not None and item.variant_id != current_variant_id
    ]

    if same_ok:
        winner = _pick(same_ok, objective)
        return SearchResult(
            outcome=MerchantOutcome.ACCEPT_BUYER_COUNTER,
            proposal_type=ProposalType.COUNTER,
            offer=winner,
            reason_codes=[
                ReasonCode.EXACT_COUNTER_SATISFIED,
                ReasonCode.ORIGINAL_CONSTRAINTS_RETAINED,
            ],
            compromise_row=compromise(winner, request) if winner else None,
        )

    if request.alternative_product_allowed and other_ok:
        winner = _pick(other_ok, objective)
        return SearchResult(
            outcome=MerchantOutcome.ALTERNATIVE_PRODUCT,
            proposal_type=ProposalType.ALTERNATIVE_PRODUCT,
            offer=winner,
            reason_codes=[
                ReasonCode.SAME_PRODUCT_UNAVAILABLE_AT_REQUEST,
                ReasonCode.ALTERNATIVE_PRODUCT_SELECTED,
            ],
            compromise_row=compromise(winner, request) if winner else None,
        )

    same_safe = [
        item
        for item in safe
        if current_variant_id is None or item.variant_id == current_variant_id
    ]
    pool = same_safe or (
        safe if request.alternative_product_allowed else []
    )
    if not pool:
        return SearchResult(
            outcome=MerchantOutcome.DECLINE,
            proposal_type=ProposalType.COUNTER,
            offer=None,
            reason_codes=[
                ReasonCode.NO_COMPLIANT_OFFER,
                ReasonCode.SAME_PRODUCT_UNAVAILABLE_AT_REQUEST,
            ],
            compromise_row=None,
        )

    ranked = sorted(
        pool,
        key=lambda item: (
            compromise(item, request).score,
            -item.utility.score,
            -item.economics.contribution_margin_cents,
        ),
    )
    winner = ranked[0]
    codes = [ReasonCode.CLOSEST_POLICY_SAFE_COUNTER]
    cap = request.max_total_price_cents
    if cap is not None and winner.total_customer_price_cents > cap:
        codes.insert(0, ReasonCode.REQUESTED_PRICE_BELOW_MARGIN_FLOOR)
    if current_variant_id and winner.variant_id != current_variant_id:
        return SearchResult(
            outcome=MerchantOutcome.ALTERNATIVE_PRODUCT,
            proposal_type=ProposalType.ALTERNATIVE_PRODUCT,
            offer=winner,
            reason_codes=[
                *codes,
                ReasonCode.ALTERNATIVE_PRODUCT_SELECTED,
            ],
            compromise_row=compromise(winner, request),
        )
    return SearchResult(
        outcome=MerchantOutcome.COUNTEROFFER,
        proposal_type=ProposalType.COUNTER,
        offer=winner,
        reason_codes=codes,
        compromise_row=compromise(winner, request),
    )

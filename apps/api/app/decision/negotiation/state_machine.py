"""Explicit negotiation transitions. Conversation text is not state."""

from app.decision.negotiation.models import NegotiationState

S = NegotiationState

ALLOWED: dict[NegotiationState, frozenset[NegotiationState]] = {
    S.CREATED: frozenset({S.BUYER_REQUEST_RECEIVED, S.CANCELLED, S.EXPIRED}),
    S.BUYER_REQUEST_RECEIVED: frozenset(
        {S.MERCHANT_PROPOSAL_CREATED, S.NO_POLICY_SAFE_COUNTER, S.CANCELLED, S.EXPIRED}
    ),
    S.MERCHANT_PROPOSAL_CREATED: frozenset(
        {
            S.BUYER_ACCEPTED,
            S.BUYER_REJECTED,
            S.BUYER_COUNTERED,
            S.EXPIRED,
            S.CANCELLED,
            S.NEGOTIATION_LIMIT_REACHED,
        }
    ),
    S.BUYER_COUNTERED: frozenset(
        {
            S.MERCHANT_COUNTER_CREATED,
            S.NO_POLICY_SAFE_COUNTER,
            S.CANCELLED,
            S.EXPIRED,
            S.NEGOTIATION_LIMIT_REACHED,
        }
    ),
    S.MERCHANT_COUNTER_CREATED: frozenset(
        {
            S.BUYER_ACCEPTED,
            S.BUYER_REJECTED,
            S.BUYER_COUNTERED,
            S.EXPIRED,
            S.CANCELLED,
            S.NEGOTIATION_LIMIT_REACHED,
        }
    ),
    S.NO_POLICY_SAFE_COUNTER: frozenset(
        {
            S.BUYER_COUNTERED,
            S.BUYER_REJECTED,
            S.CANCELLED,
            S.EXPIRED,
            S.NEGOTIATION_LIMIT_REACHED,
        }
    ),
    S.BUYER_ACCEPTED: frozenset({S.READY_FOR_CHECKOUT}),
    S.BUYER_REJECTED: frozenset(),
    S.READY_FOR_CHECKOUT: frozenset({S.EXPIRED, S.CANCELLED}),
    S.EXPIRED: frozenset(),
    S.CANCELLED: frozenset(),
    S.NEGOTIATION_LIMIT_REACHED: frozenset(),
}

OPEN_FOR_BUYER = frozenset(
    {
        S.MERCHANT_PROPOSAL_CREATED,
        S.MERCHANT_COUNTER_CREATED,
        S.NO_POLICY_SAFE_COUNTER,
    }
)

TERMINAL = frozenset(
    {
        S.BUYER_REJECTED,
        S.EXPIRED,
        S.CANCELLED,
        S.NEGOTIATION_LIMIT_REACHED,
        S.READY_FOR_CHECKOUT,
    }
)


class InvalidTransition(ValueError):
    """Buyer or merchant attempted a disallowed state change."""


def can_transition(current: NegotiationState, target: NegotiationState) -> bool:
    return target in ALLOWED.get(current, frozenset())


def transition(
    current: NegotiationState, target: NegotiationState
) -> NegotiationState:
    if not can_transition(current, target):
        raise InvalidTransition(f"Cannot move from {current} to {target}")
    return target


def buyer_may_act(state: NegotiationState) -> bool:
    return state in OPEN_FOR_BUYER

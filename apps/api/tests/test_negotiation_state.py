"""Negotiation state machine transitions."""

import pytest

from app.decision.negotiation.models import NegotiationState as S
from app.decision.negotiation.state_machine import (
    InvalidTransition,
    buyer_may_act,
    can_transition,
    transition,
)


def test_valid_opening() -> None:
    assert transition(S.CREATED, S.BUYER_REQUEST_RECEIVED) == S.BUYER_REQUEST_RECEIVED
    assert can_transition(S.BUYER_REQUEST_RECEIVED, S.MERCHANT_PROPOSAL_CREATED)


def test_invalid_transition() -> None:
    with pytest.raises(InvalidTransition):
        transition(S.CREATED, S.BUYER_ACCEPTED)


def test_buyer_may_act() -> None:
    assert buyer_may_act(S.MERCHANT_PROPOSAL_CREATED)
    assert buyer_may_act(S.MERCHANT_COUNTER_CREATED)
    assert not buyer_may_act(S.READY_FOR_CHECKOUT)
    assert not buyer_may_act(S.EXPIRED)


def test_accept_path() -> None:
    state = transition(S.MERCHANT_PROPOSAL_CREATED, S.BUYER_ACCEPTED)
    assert transition(state, S.READY_FOR_CHECKOUT) == S.READY_FOR_CHECKOUT


def test_limit_from_open_states() -> None:
    assert can_transition(
        S.MERCHANT_PROPOSAL_CREATED, S.NEGOTIATION_LIMIT_REACHED
    )
    assert can_transition(S.BUYER_COUNTERED, S.NO_POLICY_SAFE_COUNTER)

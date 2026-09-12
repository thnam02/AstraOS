"""Commerce transaction state machine."""

import pytest

from app.decision.transaction.models import TransactionState as S
from app.decision.transaction.state_machine import (
    InvalidTransactionTransition,
    can_transition,
    is_terminal,
    transition,
)


def test_successful_flow() -> None:
    state = S.PENDING
    for target in (
        S.REVALIDATING,
        S.READY_TO_RESERVE,
        S.RESERVING,
        S.RESERVED,
        S.CREATING_ORDER,
        S.CONFIRMED,
    ):
        state = transition(state, target)
    assert state == S.CONFIRMED
    assert is_terminal(state)


def test_invalid_transition() -> None:
    with pytest.raises(InvalidTransactionTransition):
        transition(S.PENDING, S.CONFIRMED)
    with pytest.raises(InvalidTransactionTransition):
        transition(S.CONFIRMED, S.PENDING)


def test_failure_transitions() -> None:
    assert transition(S.REVALIDATING, S.REVALIDATION_FAILED) == S.REVALIDATION_FAILED
    assert transition(S.RESERVING, S.RESERVATION_FAILED) == S.RESERVATION_FAILED
    assert transition(S.CREATING_ORDER, S.ORDER_FAILED) == S.ORDER_FAILED
    assert is_terminal(S.REVALIDATION_FAILED)
    assert is_terminal(S.RESERVATION_FAILED)
    assert is_terminal(S.ORDER_FAILED)


def test_cancellation() -> None:
    assert transition(S.PENDING, S.CANCELLED) == S.CANCELLED
    assert transition(S.RESERVED, S.CANCELLED) == S.CANCELLED
    assert transition(S.CONFIRMED, S.CANCELLED) == S.CANCELLED
    assert not can_transition(S.CANCELLED, S.PENDING)


def test_expiry() -> None:
    assert transition(S.PENDING, S.EXPIRED) == S.EXPIRED
    assert transition(S.RESERVED, S.EXPIRED) == S.EXPIRED
    assert is_terminal(S.EXPIRED)

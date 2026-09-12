"""Explicit commerce-transaction lifecycle. Timestamps are not state."""

from app.decision.transaction.models import TransactionState

S = TransactionState

ALLOWED: dict[TransactionState, frozenset[TransactionState]] = {
    S.PENDING: frozenset({S.REVALIDATING, S.CANCELLED, S.EXPIRED}),
    S.REVALIDATING: frozenset(
        {S.READY_TO_RESERVE, S.REVALIDATION_FAILED, S.CANCELLED, S.EXPIRED}
    ),
    S.REVALIDATION_FAILED: frozenset({S.CANCELLED, S.EXPIRED}),
    S.READY_TO_RESERVE: frozenset({S.RESERVING, S.CANCELLED, S.EXPIRED}),
    S.RESERVING: frozenset({S.RESERVED, S.RESERVATION_FAILED, S.CANCELLED}),
    S.RESERVATION_FAILED: frozenset({S.CANCELLED}),
    S.RESERVED: frozenset({S.CREATING_ORDER, S.CANCELLED, S.EXPIRED}),
    S.CREATING_ORDER: frozenset({S.CONFIRMED, S.ORDER_FAILED, S.CANCELLED}),
    S.ORDER_FAILED: frozenset({S.CANCELLED}),
    S.CONFIRMED: frozenset({S.CANCELLED}),
    S.CANCELLED: frozenset(),
    S.EXPIRED: frozenset(),
}

TERMINAL = frozenset(
    {
        S.REVALIDATION_FAILED,
        S.RESERVATION_FAILED,
        S.ORDER_FAILED,
        S.CONFIRMED,
        S.CANCELLED,
        S.EXPIRED,
    }
)

SUCCESS = frozenset({S.CONFIRMED})
FAILED = frozenset(
    {S.REVALIDATION_FAILED, S.RESERVATION_FAILED, S.ORDER_FAILED}
)


class InvalidTransactionTransition(ValueError):
    """Caller attempted a disallowed transaction state change."""


def can_transition(current: TransactionState, target: TransactionState) -> bool:
    return target in ALLOWED.get(current, frozenset())


def transition(
    current: TransactionState, target: TransactionState
) -> TransactionState:
    if not can_transition(current, target):
        raise InvalidTransactionTransition(
            f"Cannot move transaction from {current} to {target}"
        )
    return target


def is_terminal(state: TransactionState) -> bool:
    return state in TERMINAL

"""Simulated buyer choice, outside option, and deterministic ties."""

from uuid import uuid4

from app.decision.arena.models import StrategyResponse
from app.decision.arena.selection import choose_response


def _offer(
    name: str,
    utility: float,
    price: int,
    days: int,
    *,
    safe: bool = True,
    hard: bool = True,
) -> StrategyResponse:
    return StrategyResponse(
        strategy_name=name,
        offer_id=uuid4(),
        product_name=name,
        total_customer_price_cents=price,
        delivery_days=days,
        buyer_utility=utility,
        hard_constraints_satisfied=hard,
        policy_safe=safe,
        transaction_possible=safe and hard,
    )


def test_chooses_highest_utility() -> None:
    chosen = choose_response(
        [
            _offer("DEFAULT", 0.50, 32900, 2),
            _offer("ALWAYS_DISCOUNT", 0.60, 30900, 2),
            _offer("ASTRAOS", 0.80, 32900, 0),
        ],
        outside_option_utility=0.42,
    )
    assert chosen.selected_strategy == "ASTRAOS"
    assert chosen.no_purchase is False


def test_outside_option() -> None:
    chosen = choose_response(
        [
            _offer("DEFAULT", 0.30, 32900, 2),
            _offer("ASTRAOS", 0.35, 32900, 0),
        ],
        outside_option_utility=0.42,
    )
    assert chosen.no_purchase is True
    assert chosen.reason == "OUTSIDE_OPTION"
    assert chosen.selected_strategy is None


def test_no_valid_offer() -> None:
    chosen = choose_response(
        [_offer("DEFAULT", 0.90, 10000, 0, safe=False)],
        outside_option_utility=0.10,
    )
    assert chosen.no_purchase is True
    assert chosen.reason == "NO_VALID_OFFER"


def test_tie_break_price_then_delivery_then_name() -> None:
    chosen = choose_response(
        [
            _offer("ASTRAOS", 0.70, 32000, 2),
            _offer("DEFAULT", 0.70, 32000, 2),
            _offer("ALWAYS_DISCOUNT", 0.70, 32000, 0),
        ],
        outside_option_utility=0.10,
    )
    assert chosen.selected_strategy == "ALWAYS_DISCOUNT"
    chosen_price = choose_response(
        [
            _offer("ASTRAOS", 0.70, 33000, 0),
            _offer("DEFAULT", 0.70, 30000, 2),
        ],
        outside_option_utility=0.10,
    )
    assert chosen_price.selected_strategy == "DEFAULT"

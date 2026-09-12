"""Price option generation uses integer cents."""

from decimal import Decimal

from app.decision.offers.prices import cents_from_rate, generate_price_options


def test_base_and_discounts_within_authority() -> None:
    options = generate_price_options(32900, Decimal("0.10"))
    rates = [item.adjustment_rate for item in options]
    assert rates == [
        Decimal("0.00"),
        Decimal("0.03"),
        Decimal("0.05"),
        Decimal("0.07"),
        Decimal("0.10"),
    ]
    assert options[0].adjustment_type == "BASE"
    assert options[0].final_price_cents == 32900
    discounted = 32900 - cents_from_rate(32900, Decimal("0.10"))
    assert options[-1].final_price_cents == discounted


def test_never_exceeds_max_discount() -> None:
    options = generate_price_options(20000, Decimal("0.05"))
    assert max(item.adjustment_rate for item in options) == Decimal("0.05")
    assert all(item.adjustment_rate <= Decimal("0.05") for item in options)


def test_money_is_integer() -> None:
    options = generate_price_options(19999, Decimal("0.07"))
    for item in options:
        assert isinstance(item.adjustment_cents, int)
        assert isinstance(item.final_price_cents, int)
        assert item.final_price_cents == 19999 - item.adjustment_cents

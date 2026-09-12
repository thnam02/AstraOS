"""Bounded price-option generator. Does not decide that discounting is good."""

from decimal import ROUND_HALF_UP, Decimal

from app.decision.offers.models import PriceOption

CANDIDATE_RATES: tuple[Decimal, ...] = (
    Decimal("0.00"),
    Decimal("0.03"),
    Decimal("0.05"),
    Decimal("0.07"),
    Decimal("0.10"),
)


def money_rate(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def cents_from_rate(base_cents: int, rate: Decimal) -> int:
    """Integer cents from a Decimal rate. Never float money."""
    amount = (Decimal(base_cents) * money_rate(rate)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(amount)


def generate_price_options(
    base_cents: int,
    maximum_discount_rate: Decimal | float,
    *,
    limit: int = 5,
) -> list[PriceOption]:
    cap = money_rate(maximum_discount_rate)
    options: list[PriceOption] = []
    for rate in CANDIDATE_RATES:
        if rate > cap:
            continue
        adjustment = cents_from_rate(base_cents, rate)
        final = base_cents - adjustment
        if final <= 0:
            continue
        options.append(
            PriceOption(
                adjustment_type="BASE" if rate == 0 else "DISCOUNT",
                adjustment_rate=rate,
                adjustment_cents=adjustment,
                final_price_cents=final,
            )
        )
        if len(options) >= limit:
            break
    return options

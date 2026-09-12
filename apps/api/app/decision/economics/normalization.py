"""Shared numeric helpers. Money stays integer cents."""

from decimal import Decimal

from app.decision.offers.prices import money_rate


def ratio(numerator: int, denominator: int) -> Decimal:
    """contribution / revenue as a 4-decimal rate. Zero revenue → 0."""
    if denominator <= 0:
        return Decimal("0.0000")
    return money_rate(Decimal(numerator) / Decimal(denominator))


def subsidy_cents(merchant_cost: int, customer_charge: int) -> int:
    """Merchant-funded gap. Customer overpay is not a negative subsidy."""
    return max(0, int(merchant_cost) - int(customer_charge))


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

"""Complete-offer revalidation of buyer hard price constraints."""

from __future__ import annotations

from app.decision.eligibility.operators import OperatorError, apply_operator
from app.decision.intent.models import HardConstraint, PriceBasis, ShoppingIntent
from app.decision.intent.normalizer import expected_value
from app.decision.intent.price import price_constraints, resolved_price_basis
from app.decision.offers.models import RejectionCode, RejectionReason


def observed_price_cents(
    constraint: HardConstraint,
    *,
    total_customer_price_cents: int,
    product_price_cents: int,
) -> tuple[int, RejectionCode]:
    if resolved_price_basis(constraint) == PriceBasis.PRODUCT_BASE:
        return (
            product_price_cents,
            RejectionCode.BUYER_MAX_PRODUCT_PRICE_EXCEEDED,
        )
    return (
        total_customer_price_cents,
        RejectionCode.BUYER_MAX_TOTAL_EXCEEDED,
    )


def buyer_price_reasons(
    *,
    intent: ShoppingIntent,
    total_customer_price_cents: int,
    product_price_cents: int,
) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    seen: set[str] = set()
    for constraint in price_constraints(intent):
        observed, code = observed_price_cents(
            constraint,
            total_customer_price_cents=total_customer_price_cents,
            product_price_cents=product_price_cents,
        )
        expected = expected_value(constraint)
        try:
            matched = apply_operator(constraint.operator, observed, expected)
        except OperatorError:
            matched = False
        if matched:
            continue
        if code.value in seen:
            continue
        seen.add(code.value)
        basis = resolved_price_basis(constraint)
        target = (
            "base product price"
            if basis == PriceBasis.PRODUCT_BASE
            else "buyer-facing total"
        )
        reasons.append(
            RejectionReason(
                code=code,
                message=(
                    f"{target.capitalize()} {observed} violates "
                    f"{constraint.operator.value} {expected}."
                ),
            )
        )
    return reasons


def meets_buyer_price(
    *,
    intent: ShoppingIntent,
    total_customer_price_cents: int,
    product_price_cents: int,
) -> bool:
    return not buyer_price_reasons(
        intent=intent,
        total_customer_price_cents=total_customer_price_cents,
        product_price_cents=product_price_cents,
    )

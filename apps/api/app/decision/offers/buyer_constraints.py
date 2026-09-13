"""Complete-offer revalidation of mandatory buyer constraints.

Hard buyer constraints are gates, not score components. Price is judged
against the complete commercial configuration unless the buyer explicitly
bound the catalogue/base price only.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.decision.eligibility.models import ConstraintStatus
from app.decision.eligibility.operators import OperatorError, apply_operator
from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.intent.models import (
    ConstraintField,
    HardConstraint,
    PriceBasis,
    ShoppingIntent,
)
from app.decision.intent.normalizer import expected_value
from app.decision.intent.price import price_constraints, resolved_price_basis
from app.decision.offers.models import RejectionCode, RejectionReason

_DELIVERY_FIELDS = {
    ConstraintField.DELIVERY_DAYS,
    ConstraintField.SAME_DAY_DELIVERY,
}


class BuyerConstraintStatus(StrEnum):
    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    UNKNOWN = "UNKNOWN"


class BuyerConstraintReason(BaseModel):
    code: str
    field: str
    status: BuyerConstraintStatus
    message: str


class CompleteOfferBuyerEvaluation(BaseModel):
    """Outcome of complete-offer buyer-constraint validation."""

    status: BuyerConstraintStatus
    reasons: list[BuyerConstraintReason] = Field(default_factory=list)
    codes: list[str] = Field(default_factory=list)
    all_mandatory_satisfied: bool = False

    @property
    def buyer_safe(self) -> bool:
        return self.all_mandatory_satisfied


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


def _price_reasons(
    intent: ShoppingIntent,
    *,
    total_customer_price_cents: int,
    product_price_cents: int,
) -> list[BuyerConstraintReason]:
    return [
        BuyerConstraintReason(
            code=item.code.value,
            field=ConstraintField.PRICE.value,
            status=BuyerConstraintStatus.VIOLATED,
            message=item.message,
        )
        for item in buyer_price_reasons(
            intent=intent,
            total_customer_price_cents=total_customer_price_cents,
            product_price_cents=product_price_cents,
        )
    ]


def _delivery_reasons(
    intent: ShoppingIntent, *, delivery_days: int
) -> list[BuyerConstraintReason]:
    reasons: list[BuyerConstraintReason] = []
    for constraint in intent.hard_constraints:
        if constraint.field == ConstraintField.DELIVERY_DAYS:
            expected = expected_value(constraint)
            try:
                matched = apply_operator(
                    constraint.operator, delivery_days, expected
                )
                status = (
                    BuyerConstraintStatus.SATISFIED
                    if matched
                    else BuyerConstraintStatus.VIOLATED
                )
                code = (
                    "CONSTRAINT_SATISFIED"
                    if matched
                    else "BUYER_DELIVERY_CONSTRAINT_VIOLATED"
                )
            except OperatorError:
                status = BuyerConstraintStatus.UNKNOWN
                code = "INCOMPARABLE_VALUES"
            if status == BuyerConstraintStatus.SATISFIED:
                continue
            reasons.append(
                BuyerConstraintReason(
                    code=code,
                    field=constraint.field.value,
                    status=status,
                    message=(
                        f"Delivery {delivery_days} days violates "
                        f"{constraint.operator.value} {expected}."
                    ),
                )
            )
        if constraint.field == ConstraintField.SAME_DAY_DELIVERY:
            required = bool(expected_value(constraint))
            if required and delivery_days > 0:
                reasons.append(
                    BuyerConstraintReason(
                        code="BUYER_DELIVERY_CONSTRAINT_VIOLATED",
                        field=constraint.field.value,
                        status=BuyerConstraintStatus.VIOLATED,
                        message=(
                            "Same-day delivery is mandatory and this "
                            "offer is not same-day."
                        ),
                    )
                )
    return reasons


def _attribute_reasons(
    intent: ShoppingIntent, snapshot: VariantSnapshot | None
) -> list[BuyerConstraintReason]:
    from app.decision.eligibility.evaluator import EligibilityEvaluator

    reasons: list[BuyerConstraintReason] = []
    evaluator = EligibilityEvaluator()
    for constraint in intent.hard_constraints:
        if constraint.field in {ConstraintField.PRICE, *_DELIVERY_FIELDS}:
            continue
        if snapshot is None:
            reasons.append(
                BuyerConstraintReason(
                    code="MISSING_CATALOGUE_SNAPSHOT",
                    field=constraint.field.value,
                    status=BuyerConstraintStatus.UNKNOWN,
                    message=(
                        f"Mandatory {constraint.field.value} cannot be proven "
                        "on this complete offer."
                    ),
                )
            )
            continue
        evaluation = evaluator._evaluate_constraint(snapshot, constraint)
        if evaluation.status == ConstraintStatus.SATISFIED:
            continue
        status = (
            BuyerConstraintStatus.UNKNOWN
            if evaluation.status == ConstraintStatus.UNKNOWN
            else BuyerConstraintStatus.VIOLATED
        )
        reasons.append(
            BuyerConstraintReason(
                code=evaluation.reason or status.value,
                field=constraint.field.value,
                status=status,
                message=(
                    f"{constraint.field.value} {evaluation.status.value}: "
                    f"{evaluation.reason}."
                ),
            )
        )
    return reasons


def evaluate_complete_offer_constraints(
    *,
    intent: ShoppingIntent,
    total_customer_price_cents: int,
    product_price_cents: int,
    delivery_days: int,
    snapshot: VariantSnapshot | None = None,
    fail_closed: bool = True,
) -> CompleteOfferBuyerEvaluation:
    """Re-validate every mandatory buyer constraint on one complete offer."""
    reasons = [
        *_price_reasons(
            intent,
            total_customer_price_cents=total_customer_price_cents,
            product_price_cents=product_price_cents,
        ),
        *_delivery_reasons(intent, delivery_days=delivery_days),
        *_attribute_reasons(intent, snapshot),
    ]
    seen: set[str] = set()
    unique: list[BuyerConstraintReason] = []
    for item in reasons:
        key = f"{item.field}:{item.code}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    violated = [
        item for item in unique if item.status == BuyerConstraintStatus.VIOLATED
    ]
    unknown = [
        item for item in unique if item.status == BuyerConstraintStatus.UNKNOWN
    ]
    if violated:
        status = BuyerConstraintStatus.VIOLATED
    elif unknown:
        status = BuyerConstraintStatus.UNKNOWN
    else:
        status = BuyerConstraintStatus.SATISFIED
    satisfied = status == BuyerConstraintStatus.SATISFIED and (
        not unknown if fail_closed else True
    )
    if fail_closed and unknown:
        satisfied = False
    return CompleteOfferBuyerEvaluation(
        status=status,
        reasons=unique,
        codes=[item.code for item in unique],
        all_mandatory_satisfied=satisfied,
    )

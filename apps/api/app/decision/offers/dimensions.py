"""Load commercial dimensions from merchant rows. No invented options."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.decision.eligibility.operators import apply_operator
from app.decision.intent.models import ConstraintField, ShoppingIntent
from app.decision.intent.normalizer import expected_value
from app.models import DeliveryOption, ProductVariant, VariantDeliveryOption


@dataclass
class DeliveryDim:
    option_id: UUID
    code: str
    name: str
    days: int
    available: bool
    enabled: bool
    customer_charge_cents: int
    merchant_cost_cents: int
    updated_at: datetime | None


@dataclass
class WarrantyDim:
    option_id: UUID
    code: str
    name: str
    months: int
    available: bool
    enabled: bool
    customer_price_cents: int
    merchant_cost_cents: int
    is_standard: bool


@dataclass
class BundleDim:
    option_id: UUID | None
    code: str
    name: str
    available: bool
    enabled: bool
    customer_price_cents: int
    merchant_cost_cents: int
    context_relevant: bool


@dataclass
class ReturnDim:
    option_id: UUID
    code: str
    name: str
    window_days: int
    available: bool
    enabled: bool
    expected_cost_cents: int | None
    is_flexible: bool


def _delivery_charge(
    link: VariantDeliveryOption, option: DeliveryOption
) -> tuple[int, int]:
    merchant = link.merchant_cost_override_cents
    customer = link.customer_charge_override_cents
    return (
        int(merchant if merchant is not None else option.merchant_cost_cents),
        int(customer if customer is not None else option.customer_charge_cents),
    )


def load_deliveries(variant: ProductVariant) -> list[DeliveryDim]:
    rows: list[DeliveryDim] = []
    for link in variant.delivery_options:
        option = link.delivery_option
        if option is None:
            continue
        merchant, customer = _delivery_charge(link, option)
        rows.append(
            DeliveryDim(
                option_id=option.id,
                code=option.code,
                name=option.name,
                days=int(option.delivery_days),
                available=bool(link.available),
                enabled=bool(option.enabled),
                customer_charge_cents=customer,
                merchant_cost_cents=merchant,
                updated_at=getattr(link, "updated_at", None),
            )
        )
    return sorted(rows, key=lambda item: (item.days, item.code))


def load_warranties(variant: ProductVariant) -> list[WarrantyDim]:
    rows: list[WarrantyDim] = []
    for link in variant.warranty_options:
        option = link.warranty_option
        if option is None:
            continue
        rows.append(
            WarrantyDim(
                option_id=option.id,
                code=option.code,
                name=option.name,
                months=int(option.months),
                available=bool(link.available),
                enabled=bool(option.enabled),
                customer_price_cents=int(option.customer_price_cents),
                merchant_cost_cents=int(option.merchant_cost_cents),
                is_standard=option.code.startswith("STANDARD"),
            )
        )
    return sorted(rows, key=lambda item: (item.months, item.code))


def load_bundles(variant: ProductVariant, relevant: set[str]) -> list[BundleDim]:
    none = BundleDim(
        option_id=None,
        code="NONE",
        name="No bundle",
        available=True,
        enabled=True,
        customer_price_cents=0,
        merchant_cost_cents=0,
        context_relevant=True,
    )
    rows = [none]
    for link in variant.bundle_options:
        option = link.bundle_option
        if option is None:
            continue
        rows.append(
            BundleDim(
                option_id=option.id,
                code=option.code,
                name=option.name,
                available=bool(link.available),
                enabled=bool(option.enabled),
                customer_price_cents=int(option.customer_price_cents),
                merchant_cost_cents=int(option.merchant_cost_cents),
                context_relevant=option.code in relevant,
            )
        )
    return rows


def load_returns(variant: ProductVariant) -> list[ReturnDim]:
    rows: list[ReturnDim] = []
    for link in variant.return_policies:
        option = link.return_policy
        if option is None:
            continue
        rows.append(
            ReturnDim(
                option_id=option.id,
                code=option.code,
                name=option.name,
                window_days=int(option.return_window_days),
                available=bool(link.available),
                enabled=bool(option.enabled),
                expected_cost_cents=option.merchant_expected_cost_cents,
                is_flexible=not option.code.startswith("STANDARD"),
            )
        )
    return sorted(rows, key=lambda item: (item.window_days, item.code))


def delivery_meets_intent(days: int, intent: ShoppingIntent) -> bool:
    for constraint in intent.hard_constraints:
        if constraint.field == ConstraintField.DELIVERY_DAYS and not apply_operator(
            constraint.operator, days, expected_value(constraint)
        ):
            return False
        if (
            constraint.field == ConstraintField.SAME_DAY_DELIVERY
            and bool(expected_value(constraint))
            and days > 0
        ):
            return False
    return True

"""In-memory merchant graphs for offer-construction unit tests."""

from decimal import Decimal

from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    ContextLabel,
    IntentContext,
)
from app.models import (
    VariantBundleOption,
    VariantDeliveryOption,
    VariantReturnPolicy,
    VariantWarrantyOption,
)
from tests.factories import (
    make_bundle,
    make_delivery,
    make_inventory,
    make_merchant,
    make_policy,
    make_product,
    make_return_policy,
    make_variant,
    make_warranty,
)
from tests.qualification_fixtures import constraint, intent_with


def travel_intent():
    return intent_with(
        constraint(ConstraintField.ANC, ConstraintOperator.EQ, True),
        constraint(
            ConstraintField.PRICE, ConstraintOperator.LT, 35000, unit="AUD_CENTS"
        ),
        constraint(
            ConstraintField.DELIVERY_DAYS, ConstraintOperator.LTE, 0, unit="DAYS"
        ),
        context_items=[
            IntentContext(label=ContextLabel.LONG_HAUL_TRAVEL, source_phrase="flight")
        ],
    )


def construction_intent():
    """Same-day construction mechanics without a tight spend cap."""
    return intent_with(
        constraint(ConstraintField.ANC, ConstraintOperator.EQ, True),
        constraint(
            ConstraintField.DELIVERY_DAYS, ConstraintOperator.LTE, 0, unit="DAYS"
        ),
        context_items=[
            IntentContext(label=ContextLabel.LONG_HAUL_TRAVEL, source_phrase="flight")
        ],
    )


def wired_variant(
    *,
    stock: int = 8,
    reserved: int = 0,
    same_day: bool = True,
    express: bool = True,
    travel_bundle: bool = True,
    flex_returns: bool = True,
    upgrades: bool = True,
    base_price: int = 32900,
    policy_discount: Decimal = Decimal("0.10"),
    bundle_enabled: bool = True,
    warranty_upgrade_enabled: bool = True,
    flexible_returns_enabled: bool = True,
):
    product = make_product(name="Aurora Travel Pro")
    variant = make_variant(product.id, base_price_cents=base_price, sku="AUR-T01-BLK")
    variant.product = product
    variant.inventory = make_inventory(
        variant.id, units_available=stock, units_reserved=reserved
    )
    variant.evidence = []

    standard = make_delivery(code="STANDARD", delivery_days=2, name="Standard")
    express_opt = make_delivery(
        code="EXPRESS",
        delivery_days=1,
        name="Express",
        merchant_cost_cents=400,
        customer_charge_cents=600,
    )
    same = make_delivery(
        code="SAME_DAY",
        delivery_days=0,
        name="Same Day",
        merchant_cost_cents=800,
        customer_charge_cents=1000,
    )
    deliveries = [
        (standard, True),
        (express_opt, express),
        (same, same_day),
    ]
    variant.delivery_options = []
    for option, available in deliveries:
        link = VariantDeliveryOption(
            variant_id=variant.id,
            delivery_option_id=option.id,
            available=available,
        )
        link.delivery_option = option
        variant.delivery_options.append(link)

    w12 = make_warranty(code="STANDARD_12", months=12)
    w24 = make_warranty(
        code="EXTENDED_24",
        months=24,
        merchant_cost_cents=900,
        customer_price_cents=1900,
    )
    variant.warranty_options = []
    for option, available in ((w12, True), (w24, upgrades)):
        link = VariantWarrantyOption(
            variant_id=variant.id,
            warranty_option_id=option.id,
            available=available,
        )
        link.warranty_option = option
        variant.warranty_options.append(link)

    adapter = make_bundle(code="TRAVEL_ADAPTER", name="Travel adapter")
    case = make_bundle(code="HARD_CASE", name="Hard case")
    variant.bundle_options = []
    for option, available in ((adapter, travel_bundle), (case, True)):
        link = VariantBundleOption(
            variant_id=variant.id,
            bundle_option_id=option.id,
            available=available,
        )
        link.bundle_option = option
        variant.bundle_options.append(link)

    std_ret = make_return_policy(code="STANDARD_30", return_window_days=30)
    flex = make_return_policy(
        code="FLEX_60", return_window_days=60, merchant_expected_cost_cents=900
    )
    variant.return_policies = []
    for option, available in ((std_ret, True), (flex, flex_returns)):
        link = VariantReturnPolicy(
            variant_id=variant.id,
            return_policy_id=option.id,
            available=available,
        )
        link.return_policy = option
        variant.return_policies.append(link)

    merchant = make_merchant()
    policy = make_policy(
        merchant.id,
        is_active=True,
        maximum_discount_rate=policy_discount,
        bundle_enabled=bundle_enabled,
        warranty_upgrade_enabled=warranty_upgrade_enabled,
        flexible_returns_enabled=flexible_returns_enabled,
    )
    return variant, policy

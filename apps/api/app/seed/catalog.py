"""Static merchant option catalogues used by the seeder."""

import uuid
from decimal import Decimal

from app.models import (
    BundleOption,
    DataSource,
    DeliveryOption,
    Merchant,
    MerchantPolicy,
    ReturnPolicy,
    WarrantyOption,
)
from app.seed.ids import stable_uuid

MERCHANT_CODE = "ASTRA_ELECTRONICS"


def merchant() -> Merchant:
    return Merchant(
        id=stable_uuid("merchant", MERCHANT_CODE),
        name="Astra Electronics",
        code=MERCHANT_CODE,
        currency="AUD",
    )


def data_sources() -> list[DataSource]:
    rows = [
        (
            "manufacturer_specs",
            "Manufacturer specifications",
            "MANUFACTURER",
            "spec-sheet",
        ),
        ("merchant_pim", "Astra PIM", "MERCHANT_PIM", "pim://headphones"),
        (
            "merchant_inventory",
            "Warehouse on-hand",
            "MERCHANT_INVENTORY",
            "wh://SYD-01",
        ),
        (
            "merchant_pricing",
            "Merchant price book",
            "MERCHANT_PRICING",
            "pricebook://aud",
        ),
        (
            "merchant_policy",
            "Merchant policy store",
            "MERCHANT_POLICY",
            "policy://default",
        ),
        ("fulfilment", "Fulfilment capability file", "FULFILMENT", "fulfilment://au"),
        ("synthetic", "AstraOS synthetic fixture", "SYNTHETIC", "seed://2026"),
    ]
    return [
        DataSource(
            id=stable_uuid("source", code),
            name=name,
            source_type=source_type,
            reference=reference,
            description=f"{name} for Stage 1 merchant fixtures.",
        )
        for code, name, source_type, reference in rows
    ]


def delivery_options() -> list[DeliveryOption]:
    return [
        DeliveryOption(
            id=stable_uuid("delivery", "STANDARD"),
            code="STANDARD",
            name="Standard Delivery",
            description="Two-business-day metro delivery.",
            delivery_days=2,
            merchant_cost_cents=0,
            customer_charge_cents=0,
            enabled=True,
        ),
        DeliveryOption(
            id=stable_uuid("delivery", "EXPRESS"),
            code="EXPRESS",
            name="Express Delivery",
            description="Next-business-day delivery.",
            delivery_days=1,
            merchant_cost_cents=400,
            customer_charge_cents=600,
            enabled=True,
        ),
        DeliveryOption(
            id=stable_uuid("delivery", "SAME_DAY"),
            code="SAME_DAY",
            name="Same Day Delivery",
            description="Metro same-day when ordered before cutoff.",
            delivery_days=0,
            merchant_cost_cents=800,
            customer_charge_cents=1000,
            enabled=True,
        ),
    ]


def warranty_options() -> list[WarrantyOption]:
    return [
        WarrantyOption(
            id=stable_uuid("warranty", "STANDARD_12"),
            code="STANDARD_12",
            name="Standard 12-month warranty",
            months=12,
            merchant_cost_cents=0,
            customer_price_cents=0,
            enabled=True,
        ),
        WarrantyOption(
            id=stable_uuid("warranty", "EXTENDED_24"),
            code="EXTENDED_24",
            name="Extended 24-month warranty",
            months=24,
            merchant_cost_cents=900,
            customer_price_cents=1900,
            enabled=True,
        ),
        WarrantyOption(
            id=stable_uuid("warranty", "EXTENDED_36"),
            code="EXTENDED_36",
            name="Extended 36-month warranty",
            months=36,
            merchant_cost_cents=1400,
            customer_price_cents=2900,
            enabled=True,
        ),
    ]


def bundle_options() -> list[BundleOption]:
    return [
        BundleOption(
            id=stable_uuid("bundle", "TRAVEL_ADAPTER"),
            code="TRAVEL_ADAPTER",
            name="Travel charging adapter",
            description="Multi-region USB-C adapter.",
            merchant_cost_cents=700,
            customer_price_cents=1500,
            enabled=True,
            attributes={"weight_g": 68},
        ),
        BundleOption(
            id=stable_uuid("bundle", "AIRPLANE_ADAPTER"),
            code="AIRPLANE_ADAPTER",
            name="Airplane audio adapter",
            description="Dual-prong inflight adapter.",
            merchant_cost_cents=500,
            customer_price_cents=1200,
            enabled=True,
            attributes={"inflight": True},
        ),
        BundleOption(
            id=stable_uuid("bundle", "HARD_CASE"),
            code="HARD_CASE",
            name="Hard travel case",
            description="Crush-resistant carry case.",
            merchant_cost_cents=900,
            customer_price_cents=1800,
            enabled=True,
            attributes={"protected": True},
        ),
    ]


def return_policies() -> list[ReturnPolicy]:
    return [
        ReturnPolicy(
            id=stable_uuid("return", "STANDARD_30"),
            code="STANDARD_30",
            name="30-day standard returns",
            return_window_days=30,
            restocking_fee_rate=None,
            conditions="Unopened or lightly used with original packaging.",
            merchant_expected_cost_cents=400,
            enabled=True,
        ),
        ReturnPolicy(
            id=stable_uuid("return", "FLEX_60"),
            code="FLEX_60",
            name="60-day flexible returns",
            return_window_days=60,
            restocking_fee_rate=Decimal("0.0500"),
            conditions="Extended window for premium and travel SKUs.",
            merchant_expected_cost_cents=900,
            enabled=True,
        ),
    ]


def merchant_policy(merchant_id: uuid.UUID) -> MerchantPolicy:
    return MerchantPolicy(
        id=stable_uuid("policy", "default"),
        merchant_id=merchant_id,
        name="Astra Electronics Default Policy",
        is_active=True,
        minimum_margin_rate=Decimal("0.1500"),
        maximum_discount_rate=Decimal("0.1000"),
        delivery_subsidy_enabled=True,
        warranty_upgrade_enabled=True,
        bundle_enabled=True,
        flexible_returns_enabled=True,
        loyalty_enabled=False,
        maximum_delivery_subsidy_cents=1000,
        maximum_warranty_subsidy_cents=1400,
        maximum_bundle_subsidy_cents=900,
    )

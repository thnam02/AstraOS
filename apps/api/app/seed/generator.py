"""Deterministic synthetic headphone catalogue."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from typing import Any

from app.models import (
    AttributeEvidence,
    InventoryRecord,
    Product,
    ProductVariant,
    VariantBundleOption,
    VariantDeliveryOption,
    VariantReturnPolicy,
    VariantWarrantyOption,
)
from app.seed.ids import stable_uuid

CATEGORY = "headphones"
AS_OF = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
OBSERVED_AT = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)

BRANDS: list[tuple[str, str, str]] = [
    ("Aurora Audio", "AUR", "Aurora"),
    ("NovaSound", "NOV", "Nova"),
    ("SonicEdge", "SON", "Sonic"),
    ("Verve", "VRV", "Verve"),
    ("Helix", "HLX", "Helix"),
    ("Atlas Audio", "ATL", "Atlas"),
    ("EchoWorks", "ECH", "Echo"),
    ("Nimbus", "NIM", "Nimbus"),
    ("Orion", "ORI", "Orion"),
    ("PulseLab", "PLS", "Pulse"),
    ("Vanta", "VAN", "Vanta"),
    ("Zenith Audio", "ZEN", "Zenith"),
]

SEGMENTS: list[dict[str, Any]] = [
    {
        "name": "Budget",
        "series": ["Lite", "Go", "Mini", "Everyday"],
        "price": (7900, 14900),
        "anc": 0.25,
        "battery": (15, 32),
        "weight": (200, 320),
        "comfort": (0.45, 0.72),
        "travel": (0.30, 0.70),
    },
    {
        "name": "Midrange",
        "series": ["Plus", "Air", "Shift", "Pulse"],
        "price": (14900, 29900),
        "anc": 0.70,
        "battery": (24, 50),
        "weight": (190, 300),
        "comfort": (0.62, 0.86),
        "travel": (0.50, 0.84),
    },
    {
        "name": "Premium",
        "series": ["Pro", "Elite", "Signature", "Ultra"],
        "price": (29900, 69900),
        "anc": 0.95,
        "battery": (28, 60),
        "weight": (180, 280),
        "comfort": (0.78, 0.98),
        "travel": (0.60, 0.92),
    },
    {
        "name": "Travel",
        "series": ["Travel Pro", "Commute", "Fold", "Cabin"],
        "price": (17900, 44900),
        "anc": 0.88,
        "battery": (30, 80),
        "weight": (180, 260),
        "comfort": (0.70, 0.94),
        "travel": (0.72, 0.98),
    },
    {
        "name": "Gaming",
        "series": ["Play", "Arena", "Pulse GX", "Rig"],
        "price": (9900, 39900),
        "anc": 0.40,
        "battery": (18, 40),
        "weight": (240, 420),
        "comfort": (0.55, 0.88),
        "travel": (0.30, 0.55),
    },
    {
        "name": "Studio",
        "series": ["Studio", "Monitor", "Mix", "Reference"],
        "price": (19900, 59900),
        "anc": 0.20,
        "battery": (20, 45),
        "weight": (210, 360),
        "comfort": (0.68, 0.93),
        "travel": (0.35, 0.62),
    },
    {
        "name": "Sports",
        "series": ["Sport", "Run", "Flex", "Active"],
        "price": (8900, 24900),
        "anc": 0.35,
        "battery": (16, 36),
        "weight": (180, 250),
        "comfort": (0.50, 0.82),
        "travel": (0.40, 0.75),
    },
]

COLORS = ["Black", "Silver", "White", "Navy", "Graphite", "Sage"]
COLOR_CODES = {
    "Black": "BLK",
    "Silver": "SLV",
    "White": "WHT",
    "Navy": "NVY",
    "Graphite": "GPH",
    "Sage": "SGE",
}
MISSING_KEYS = ("anc", "battery_hours", "comfort_score", "travel_score")


@dataclass
class GeneratedCatalogue:
    """All generated merchant rows for one seed pass."""

    products: list[Product] = field(default_factory=list)
    variants: list[ProductVariant] = field(default_factory=list)
    inventory: list[InventoryRecord] = field(default_factory=list)
    deliveries: list[VariantDeliveryOption] = field(default_factory=list)
    warranties: list[VariantWarrantyOption] = field(default_factory=list)
    bundles: list[VariantBundleOption] = field(default_factory=list)
    returns: list[VariantReturnPolicy] = field(default_factory=list)
    evidence: list[AttributeEvidence] = field(default_factory=list)


def _choice_range(rng: random.Random, bounds: tuple[int, int]) -> int:
    return rng.randint(bounds[0], bounds[1])


def _float_range(
    rng: random.Random, bounds: tuple[float, float], digits: int = 2
) -> float:
    return round(rng.uniform(bounds[0], bounds[1]), digits)


def generate_catalogue(
    rng: random.Random,
    *,
    source_ids: dict[str, Any],
    delivery_ids: dict[str, Any],
    warranty_ids: dict[str, Any],
    bundle_ids: dict[str, Any],
    return_ids: dict[str, Any],
) -> GeneratedCatalogue:
    """Build a deterministic headphones catalogue."""
    out = GeneratedCatalogue()
    product_index = 0
    for brand, prefix, short in BRANDS:
        for segment_index, segment in enumerate(SEGMENTS):
            for _ in range(2 if segment["name"] != "Premium" else 1):
                product_index += 1
                series = segment["series"][
                    (product_index + segment_index) % len(segment["series"])
                ]
                model_number = f"{prefix}-{segment['name'][:1]}{product_index:02d}"
                name = f"{short} {series} {product_index:02d}"
                product_id = stable_uuid("product", model_number)
                out.products.append(
                    Product(
                        id=product_id,
                        name=name,
                        brand=brand,
                        category=CATEGORY,
                        description=(
                            f"{name} {segment['name'].lower()} "
                            f"headphones from {brand}. "
                            "Synthetic Astra Electronics catalogue item."
                        ),
                        model_number=model_number,
                        manufacturer=brand,
                        is_active=True,
                    )
                )
                color_count = 2
                if (
                    segment["name"] in {"Premium", "Travel", "Studio"}
                    and rng.random() < 0.45
                ):
                    color_count = 3
                colors = COLORS[:color_count]
                for color in colors:
                    _add_variant(
                        out,
                        rng,
                        brand=brand,
                        prefix=prefix,
                        product_id=product_id,
                        product_name=name,
                        model_number=model_number,
                        segment=segment,
                        color=color,
                        source_ids=source_ids,
                        delivery_ids=delivery_ids,
                        warranty_ids=warranty_ids,
                        bundle_ids=bundle_ids,
                        return_ids=return_ids,
                    )
    return out


def _add_variant(
    out: GeneratedCatalogue,
    rng: random.Random,
    *,
    brand: str,
    prefix: str,
    product_id: Any,
    product_name: str,
    model_number: str,
    segment: dict[str, Any],
    color: str,
    source_ids: dict[str, Any],
    delivery_ids: dict[str, Any],
    warranty_ids: dict[str, Any],
    bundle_ids: dict[str, Any],
    return_ids: dict[str, Any],
) -> None:
    sku = f"{prefix}-{model_number.split('-')[1]}-{COLOR_CODES[color]}"
    variant_id = stable_uuid("variant", sku)
    price = _choice_range(rng, segment["price"])
    cogs_rate = rng.uniform(0.45, 0.75)
    if rng.random() < 0.05:
        cogs_rate = rng.uniform(0.72, 0.75)
    cogs = int(price * cogs_rate)
    if cogs >= price:
        cogs = max(price - 100, 1)

    attributes: dict[str, Any] = {
        "segment": segment["name"],
        "anc": rng.random() < float(segment["anc"]),
        "battery_hours": _choice_range(rng, segment["battery"]),
        "weight_g": _choice_range(rng, segment["weight"]),
        "foldable": segment["name"] in {"Travel", "Budget"} or rng.random() < 0.35,
        "wireless": rng.random() < 0.92,
        "bluetooth_version": rng.choice(["5.0", "5.1", "5.2", "5.3"]),
        "comfort_score": _float_range(rng, segment["comfort"]),
        "travel_score": _float_range(rng, segment["travel"]),
        "microphone": rng.random() < 0.85,
    }
    if rng.random() < 0.45:
        attributes["water_resistance"] = rng.choice(["IPX4", "IPX5", None])

    if rng.random() < 0.08:
        for key in rng.sample(MISSING_KEYS, k=rng.randint(1, 2)):
            attributes.pop(key, None)

    out.variants.append(
        ProductVariant(
            id=variant_id,
            product_id=product_id,
            sku=sku,
            variant_name=f"{product_name} {color}",
            currency="AUD",
            base_price_cents=price,
            cogs_cents=cogs,
            attributes=attributes,
            is_active=rng.random() > 0.02,
        )
    )

    roll = rng.random()
    if roll < 0.14:
        units_available = 0
    elif roll < 0.22:
        units_available = rng.randint(1, 3)
    else:
        units_available = rng.randint(4, 50)
    units_reserved = (
        0 if units_available == 0 else rng.randint(0, min(2, units_available))
    )

    out.inventory.append(
        InventoryRecord(
            id=stable_uuid("inventory", sku),
            variant_id=variant_id,
            units_available=units_available,
            units_reserved=units_reserved,
            warehouse_code="SYD-01",
        )
    )

    same_day = rng.random() < 0.52
    for code, available in (
        ("STANDARD", True),
        ("EXPRESS", rng.random() < 0.86),
        ("SAME_DAY", same_day),
    ):
        out.deliveries.append(
            VariantDeliveryOption(
                id=stable_uuid("vdel", sku, code),
                variant_id=variant_id,
                delivery_option_id=delivery_ids[code],
                available=available,
                cutoff_time=time(11, 0) if code == "SAME_DAY" and available else None,
            )
        )

    for code, available in (
        ("STANDARD_12", True),
        ("EXTENDED_24", segment["name"] != "Budget" or rng.random() < 0.4),
        ("EXTENDED_36", segment["name"] in {"Premium", "Travel", "Studio"}),
    ):
        out.warranties.append(
            VariantWarrantyOption(
                id=stable_uuid("vwar", sku, code),
                variant_id=variant_id,
                warranty_option_id=warranty_ids[code],
                available=available,
            )
        )

    for code, available in (
        ("TRAVEL_ADAPTER", segment["name"] in {"Travel", "Premium", "Midrange"}),
        ("AIRPLANE_ADAPTER", segment["name"] in {"Travel", "Premium"}),
        ("HARD_CASE", True),
    ):
        out.bundles.append(
            VariantBundleOption(
                id=stable_uuid("vbun", sku, code),
                variant_id=variant_id,
                bundle_option_id=bundle_ids[code],
                available=available,
            )
        )

    out.returns.append(
        VariantReturnPolicy(
            id=stable_uuid("vret", sku, "STANDARD_30"),
            variant_id=variant_id,
            return_policy_id=return_ids["STANDARD_30"],
            available=True,
        )
    )
    out.returns.append(
        VariantReturnPolicy(
            id=stable_uuid("vret", sku, "FLEX_60"),
            variant_id=variant_id,
            return_policy_id=return_ids["FLEX_60"],
            available=segment["name"] in {"Premium", "Travel", "Studio"},
        )
    )

    _add_evidence(
        out,
        rng,
        sku=sku,
        variant_id=variant_id,
        attributes=attributes,
        price=price,
        units_available=units_available,
        source_ids=source_ids,
        brand=brand,
    )


def _add_evidence(
    out: GeneratedCatalogue,
    rng: random.Random,
    *,
    sku: str,
    variant_id: Any,
    attributes: dict[str, Any],
    price: int,
    units_available: int,
    source_ids: dict[str, Any],
    brand: str,
) -> None:
    facts: list[tuple[str, Any, str, str]] = [
        ("base_price_cents", price, "merchant_pricing", "MERCHANT_DECLARED"),
        ("units_available", units_available, "merchant_inventory", "MERCHANT_DECLARED"),
    ]
    for key, value in attributes.items():
        if key == "segment":
            source = "merchant_pim"
            status = "MERCHANT_DECLARED"
        elif key in {
            "anc",
            "battery_hours",
            "weight_g",
            "bluetooth_version",
            "wireless",
        }:
            source = "manufacturer_specs"
            status = "VERIFIED"
        else:
            source = "synthetic"
            status = "SYNTHETIC"
        facts.append((key, value, source, status))

    for index, (name, value, source, status) in enumerate(facts):
        stale = rng.random() < 0.03
        out.evidence.append(
            AttributeEvidence(
                id=stable_uuid("evidence", sku, name, str(index)),
                variant_id=variant_id,
                attribute_name=name,
                value=value,
                source_id=source_ids[source],
                source_reference=f"{brand}:{sku}:{name}",
                confidence=1.0
                if status == "VERIFIED"
                else 0.72
                if status == "MERCHANT_DECLARED"
                else 0.5,
                verification_status=status,
                observed_at=OBSERVED_AT,
                expires_at=(AS_OF - timedelta(days=20))
                if stale
                else (AS_OF + timedelta(days=180)),
            )
        )

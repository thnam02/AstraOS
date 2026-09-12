"""Explicit Stage 2 qualification fixtures."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.decision.eligibility.snapshot import (
    DeliverySnapshot,
    EvidenceSnapshot,
    InventorySnapshot,
    VariantSnapshot,
)
from app.decision.intent.models import (
    PARSER_VERSION_RULE,
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    IntentAmbiguity,
    PreferenceDirection,
    PreferenceField,
    ShoppingIntent,
    SoftPreference,
)

HERO_INTENT = (
    "I need noise-cancelling headphones under A$350 for a 12-hour flight. "
    "I need them today. "
    "Comfort and reliability matter more than getting the absolute cheapest option."
)

HERO_INTENT_DELIVERED = (
    "I need noise-cancelling headphones under A$350 for a 12-hour flight.\n"
    "I need them delivered today.\n"
    "Comfort and reliability matter more than getting the absolute cheapest option."
)

NOW = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)
_INVENTORY_DEFAULT = object()


def constraint(
    field: ConstraintField,
    operator: ConstraintOperator,
    value: object,
    *,
    cid: str = "c1",
    unit: str | None = None,
    phrase: str = "test",
) -> HardConstraint:
    return HardConstraint(
        id=cid,
        field=field,
        operator=operator,
        value=value,
        unit=unit,
        source_phrase=phrase,
        normalized_value=value,
    )


def intent_with(*constraints: HardConstraint, **kwargs: object) -> ShoppingIntent:
    payload: dict[str, object] = {
        "raw_text": "test",
        "category": "headphones",
        "hard_constraints": list(constraints),
        "soft_preferences": [],
        "context_tags": [],
        "ambiguities": [],
        "parser_type": "rule_based",
        "parser_version": PARSER_VERSION_RULE,
    }
    payload.update(kwargs)
    return ShoppingIntent.model_validate(payload)


def snapshot(
    *,
    sku: str = "AUR-T01-BLK",
    name: str = "Aurora A9",
    brand: str = "Aurora Audio",
    price: int = 32900,
    attributes: dict[str, object] | None = None,
    inventory: InventorySnapshot | None | object = _INVENTORY_DEFAULT,
    deliveries: list[DeliverySnapshot] | None = None,
    evidence: list[EvidenceSnapshot] | None = None,
) -> VariantSnapshot:
    return VariantSnapshot(
        product_id=uuid4(),
        variant_id=uuid4(),
        sku=sku,
        product_name=name,
        brand=brand,
        category="headphones",
        variant_name=f"{name} Black",
        base_price_cents=price,
        attributes=attributes
        if attributes is not None
        else {
            "anc": True,
            "battery_hours": 36,
            "weight_g": 240,
            "foldable": True,
            "wireless": True,
            "microphone": True,
        },
        inventory=(
            InventorySnapshot(12, 1) if inventory is _INVENTORY_DEFAULT else inventory  # type: ignore[arg-type]
        ),
        deliveries=deliveries
        if deliveries is not None
        else [
            DeliverySnapshot("STANDARD", "Standard Delivery", 2, True, True),
            DeliverySnapshot("SAME_DAY", "Same Day Delivery", 0, True, True),
        ],
        evidence=evidence or [],
    )


def evidence(
    attribute: str,
    value: object,
    *,
    stale: bool = False,
    source: str = "Manufacturer specifications",
    status: str = "VERIFIED",
) -> EvidenceSnapshot:
    expires = NOW - timedelta(days=10) if stale else NOW + timedelta(days=180)
    return EvidenceSnapshot(
        id=str(uuid4()),
        attribute_name=attribute,
        value=value,
        source_name=source,
        source_type="MANUFACTURER",
        source_reference=f"spec:{attribute}",
        verification_status=status,
        observed_at=NOW - timedelta(days=5),
        expires_at=expires,
    )


# CASE 1 — ANC under $350 delivered today
CASE1_INTENT = intent_with(
    constraint(ConstraintField.ANC, ConstraintOperator.EQ, True, cid="anc"),
    constraint(
        ConstraintField.PRICE,
        ConstraintOperator.LT,
        35000,
        cid="price",
        unit="AUD_CENTS",
    ),
    constraint(
        ConstraintField.DELIVERY_DAYS,
        ConstraintOperator.LTE,
        0,
        cid="delivery",
        unit="DAYS",
    ),
    raw_text=HERO_INTENT,
    soft_preferences=[
        SoftPreference(
            id="p1",
            field=PreferenceField.COMFORT,
            direction=PreferenceDirection.MAXIMIZE,
            importance=0.9,
            source_phrase="Comfort",
        ),
        SoftPreference(
            id="p2",
            field=PreferenceField.RELIABILITY,
            direction=PreferenceDirection.MAXIMIZE,
            importance=0.85,
            source_phrase="reliability",
        ),
        SoftPreference(
            id="p3",
            field=PreferenceField.PRICE,
            direction=PreferenceDirection.MINIMIZE,
            importance=0.3,
            source_phrase="absolute cheapest",
        ),
    ],
    context_tags=["long_haul_travel"],
)

CASE1_AURORA = snapshot(name="Aurora A9", price=32900)
CASE1_NIMBUS = snapshot(
    name="Nimbus Travel Pro",
    brand="Nimbus",
    sku="NIM-T01-BLK",
    price=29900,
    deliveries=[DeliverySnapshot("STANDARD", "Standard Delivery", 2, True, True)],
)
CASE1_VANTA = snapshot(
    name="Vanta Studio X2",
    brand="Vanta",
    sku="VAN-S01-BLK",
    price=42900,
)

# CASE 2 — battery >= 40h
CASE2_INTENT = intent_with(
    constraint(ConstraintField.BATTERY_HOURS, ConstraintOperator.GTE, 40, cid="bat")
)

# CASE 3 — under $200 + wireless
CASE3_INTENT = intent_with(
    constraint(ConstraintField.PRICE, ConstraintOperator.LT, 20000, cid="price"),
    constraint(ConstraintField.WIRELESS, ConstraintOperator.EQ, True, cid="wl"),
)

# CASE 4 — foldable required
CASE4_INTENT = intent_with(
    constraint(ConstraintField.FOLDABLE, ConstraintOperator.EQ, True, cid="fold")
)

# CASE 5 — same-day on variant without same-day
CASE5_INTENT = intent_with(
    constraint(ConstraintField.DELIVERY_DAYS, ConstraintOperator.LTE, 0, cid="day")
)
CASE5_NO_SAME_DAY = snapshot(
    name="Nimbus Travel Pro",
    deliveries=[DeliverySnapshot("STANDARD", "Standard Delivery", 2, True, True)],
)

# CASE 6 — missing battery
CASE6_INTENT = CASE2_INTENT
CASE6_MISSING_BATTERY = snapshot(attributes={"anc": True, "wireless": True})

# CASE 7 — out of stock
CASE7_INTENT = intent_with(
    constraint(ConstraintField.IN_STOCK, ConstraintOperator.EQ, True, cid="stock")
)
CASE7_OOS = snapshot(inventory=InventorySnapshot(0, 0))
CASE7_RESERVED = snapshot(inventory=InventorySnapshot(3, 3))
CASE7_MISSING_INV = snapshot(inventory=None)

# CASE 8 — price exactly at boundary
CASE8_LT = intent_with(
    constraint(ConstraintField.PRICE, ConstraintOperator.LT, 35000, cid="lt")
)
CASE8_LTE = intent_with(
    constraint(ConstraintField.PRICE, ConstraintOperator.LTE, 35000, cid="lte")
)
CASE8_AT_BOUNDARY = snapshot(price=35000)

# CASE 9 — unsupported mandatory
CASE9_INTENT = intent_with(
    constraint(ConstraintField.ANC, ConstraintOperator.EQ, True, cid="anc"),
    ambiguities=[
        IntentAmbiguity(
            source_phrase="must look luxurious",
            reason="unsupported_attribute",
            appears_mandatory=True,
        )
    ],
)

# CASE 10 — multiple AND conditions
CASE10_INTENT = intent_with(
    constraint(ConstraintField.ANC, ConstraintOperator.EQ, True, cid="anc"),
    constraint(ConstraintField.PRICE, ConstraintOperator.LT, 35000, cid="price"),
    constraint(ConstraintField.WIRELESS, ConstraintOperator.EQ, True, cid="wl"),
    constraint(ConstraintField.IN_STOCK, ConstraintOperator.EQ, True, cid="stock"),
)

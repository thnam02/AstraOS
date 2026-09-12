"""Normalise merchant feed values into canonical AstraOS units."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

from app.ingestion.constants import (
    CURRENCY_AUD,
    DELIVERY_ALIASES,
    OPTIONAL_VARIANT_WARNINGS,
    SCHEMA_VERSION,
)
from app.ingestion.result import IngestionIssue
from app.ingestion.schemas import (
    CanonicalBundleOption,
    CanonicalDeliveryOption,
    CanonicalEvidence,
    CanonicalInventory,
    CanonicalMerchantSnapshot,
    CanonicalProduct,
    CanonicalReturnPolicy,
    CanonicalVariant,
    CanonicalVariantLink,
    CanonicalWarrantyOption,
    ExternalMerchantSnapshot,
)

_MONEY_RE = re.compile(
    r"^\s*(?:a\$|aud)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:aud)?\s*$",
    re.IGNORECASE,
)
_WEIGHT_RE = re.compile(
    r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(kg|g|grams|gram|kilograms?)?\s*$",
    re.IGNORECASE,
)
_TERM_RE = re.compile(
    r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(years?|months?|days?)?\s*$",
    re.IGNORECASE,
)


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_bool(value: Any, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return default


def parse_money_cents(
    value: Any,
    *,
    already_cents: bool = False,
    field: str,
    location: str,
    issues: list[IngestionIssue],
) -> int | None:
    if value is None or value == "":
        issues.append(
            IngestionIssue(
                "ERROR",
                "missing_money",
                f"{field} is required and was not invented.",
                location=location,
            )
        )
        return None
    if already_cents or (isinstance(field, str) and field.endswith("_cents")):
        try:
            cents = int(value)
        except (TypeError, ValueError):
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_money",
                    f"{field} must be an integer cent amount.",
                    location=location,
                )
            )
            return None
    else:
        if isinstance(value, bool) or (
            isinstance(value, float) and (math.isnan(value) or math.isinf(value))
        ):
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_money",
                    f"{field} is not a usable amount.",
                    location=location,
                )
            )
            return None
        if isinstance(value, int | float):
            cents = int(round(float(value) * 100))
        else:
            match = _MONEY_RE.match(str(value))
            if match is None:
                issues.append(
                    IngestionIssue(
                        "ERROR",
                        "invalid_money",
                        f"{field} value {value!r} could not be normalised "
                        "to AUD cents.",
                        location=location,
                    )
                )
                return None
            cents = int(round(float(match.group(1)) * 100))
    if cents < 0:
        issues.append(
            IngestionIssue(
                "ERROR",
                "negative_money",
                f"{field} cannot be negative.",
                location=location,
            )
        )
        return None
    return cents


def parse_weight_g(
    value: Any,
    *,
    location: str,
    issues: list[IngestionIssue],
) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float) and not isinstance(value, bool):
        if math.isnan(float(value)) or math.isinf(float(value)):
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_weight",
                    "Weight is not a finite number.",
                    location,
                )
            )
            return None
        return float(value)
    match = _WEIGHT_RE.match(str(value))
    if match is None:
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_weight",
                f"Weight {value!r} could not be normalised to grams.",
                location=location,
            )
        )
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "g").lower()
    if unit.startswith("kg"):
        return amount * 1000
    return amount


def parse_months(
    value: Any,
    *,
    location: str,
    issues: list[IngestionIssue],
) -> int | None:
    if value is None or value == "":
        issues.append(
            IngestionIssue(
                "ERROR",
                "missing_warranty_term",
                "Warranty term is required.",
                location=location,
            )
        )
        return None
    if isinstance(value, int | float) and not isinstance(value, bool):
        months = int(value)
    else:
        match = _TERM_RE.match(str(value))
        if match is None:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_warranty_term",
                    f"Warranty term {value!r} could not be normalised.",
                    location=location,
                )
            )
            return None
        amount = float(match.group(1))
        unit = (match.group(2) or "months").lower()
        if unit.startswith("year"):
            months = int(round(amount * 12))
        elif unit.startswith("day"):
            months = max(1, int(round(amount / 30)))
        else:
            months = int(amount)
    if months <= 0:
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_warranty_term",
                "Warranty term must be positive.",
                location=location,
            )
        )
        return None
    return months


def parse_delivery_code(value: Any) -> str | None:
    text = _as_str(value)
    if text is None:
        return None
    key = text.lower().replace("_", " ").replace("-", " ")
    compact = key.replace(" ", "_")
    if compact in DELIVERY_ALIASES:
        return DELIVERY_ALIASES[compact]
    spaced = key
    if spaced in DELIVERY_ALIASES:
        return DELIVERY_ALIASES[spaced]
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").upper()


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _money_from_row(
    row: dict[str, Any],
    dollar_key: str,
    cents_key: str,
    *,
    location: str,
    issues: list[IngestionIssue],
    required: bool = True,
) -> int | None:
    if cents_key in row and row[cents_key] not in (None, ""):
        return parse_money_cents(
            row[cents_key],
            already_cents=True,
            field=cents_key,
            location=location,
            issues=issues,
        )
    if dollar_key in row and row[dollar_key] not in (None, ""):
        return parse_money_cents(
            row[dollar_key],
            field=dollar_key,
            location=location,
            issues=issues,
        )
    if required:
        issues.append(
            IngestionIssue(
                "ERROR",
                "missing_money",
                f"{dollar_key} is required and was not invented.",
                location=location,
            )
        )
    return None


def _variant_attributes(
    row: dict[str, Any],
    *,
    sku: str,
    issues: list[IngestionIssue],
) -> dict[str, Any]:
    raw = row.get("attributes")
    attrs: dict[str, Any] = dict(raw) if isinstance(raw, dict) else {}
    for key in (
        "anc",
        "wireless",
        "foldable",
        "microphone",
        "battery_hours",
        "weight_g",
        "comfort_score",
        "travel_score",
        "water_resistance",
        "bluetooth_version",
    ):
        if key in row and row[key] not in (None, "") and key not in attrs:
            attrs[key] = row[key]
    if "weight" in row and "weight_g" not in attrs:
        weight = parse_weight_g(
            row.get("weight"), location=f"variants[{sku}].weight", issues=issues
        )
        if weight is not None:
            attrs["weight_g"] = weight
    elif "weight_g" in attrs:
        weight = parse_weight_g(
            attrs.get("weight_g"), location=f"variants[{sku}].weight_g", issues=issues
        )
        if weight is not None:
            attrs["weight_g"] = weight
    for key in ("anc", "wireless", "foldable", "microphone"):
        if key in attrs and attrs[key] not in (None, ""):
            attrs[key] = _as_bool(attrs[key], default=bool(attrs[key]))
    for key in OPTIONAL_VARIANT_WARNINGS:
        if key not in attrs or attrs[key] in (None, ""):
            issues.append(
                IngestionIssue(
                    "WARNING",
                    "missing_optional_attribute",
                    f"Variant {sku} has no {key}; the value remains unknown.",
                    location=f"variants[{sku}].{key}",
                    record_id=sku,
                )
            )
            attrs.pop(key, None)
    return {key: value for key, value in attrs.items() if value != ""}


def normalize_snapshot(
    external: ExternalMerchantSnapshot,
) -> tuple[CanonicalMerchantSnapshot, list[IngestionIssue]]:
    issues: list[IngestionIssue] = []
    merchant = external.merchant or {}
    currency = (_as_str(merchant.get("currency")) or CURRENCY_AUD).upper()
    products: list[CanonicalProduct] = []
    for index, row in enumerate(external.products):
        loc = f"products[{index}]"
        external_id = _as_str(row.get("external_id") or row.get("id"))
        name = _as_str(row.get("name"))
        brand = _as_str(row.get("brand"))
        category = _as_str(row.get("category")) or "headphones"
        if not external_id or not name or not brand:
            continue
        products.append(
            CanonicalProduct(
                external_id=external_id,
                name=name,
                brand=brand,
                category=category,
                description=_as_str(row.get("description")),
                model_number=_as_str(row.get("model_number")),
                manufacturer=_as_str(row.get("manufacturer")),
                is_active=_as_bool(row.get("is_active"), default=True),
            )
        )

    variants: list[CanonicalVariant] = []
    for index, row in enumerate(external.variants):
        loc = f"variants[{index}]"
        sku = _as_str(row.get("sku") or row.get("external_variant_id"))
        product_id = _as_str(
            row.get("product_external_id")
            or row.get("product_id")
            or row.get("product")
        )
        if not sku or not product_id:
            continue
        variant_currency = (_as_str(row.get("currency")) or currency).upper()
        price = _money_from_row(
            row, "price", "price_cents", location=f"{loc}.price", issues=issues
        )
        cogs = _money_from_row(
            row, "cogs", "cogs_cents", location=f"{loc}.cogs", issues=issues
        )
        if price is None or cogs is None:
            continue
        if price <= 0:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "non_positive_price",
                    f"Variant {sku} price must be greater than zero.",
                    location=f"{loc}.price",
                    record_id=sku,
                )
            )
            continue
        variants.append(
            CanonicalVariant(
                sku=sku,
                product_external_id=product_id,
                variant_name=_as_str(row.get("variant_name") or row.get("name")),
                currency=variant_currency,
                base_price_cents=price,
                cogs_cents=cogs,
                attributes=_variant_attributes(row, sku=sku, issues=issues),
                is_active=_as_bool(row.get("is_active"), default=True),
            )
        )

    inventory: list[CanonicalInventory] = []
    for index, row in enumerate(external.inventory):
        loc = f"inventory[{index}]"
        sku = _as_str(row.get("sku") or row.get("external_variant_id"))
        if not sku:
            continue
        try:
            raw_units = (
                row.get("units_available")
                if "units_available" in row
                else row.get("quantity")
            )
            if raw_units is None:
                raise TypeError("missing inventory quantity")
            units = int(raw_units)
        except (TypeError, ValueError):
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_inventory",
                    f"Inventory quantity for {sku} is not an integer.",
                    location=loc,
                    record_id=sku,
                )
            )
            continue
        if units < 0:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "negative_inventory",
                    f"Inventory for {sku} cannot be negative.",
                    location=loc,
                    record_id=sku,
                )
            )
            continue
        inventory.append(
            CanonicalInventory(
                sku=sku,
                units_available=units,
                warehouse_code=_as_str(row.get("warehouse_code") or row.get("location"))
                or "DEFAULT",
                observed_at=parse_datetime(
                    row.get("observed_at") or row.get("updated_at")
                ),
            )
        )

    deliveries = [_normalize_delivery(row, issues) for row in external.delivery_options]
    warranties = [_normalize_warranty(row, issues) for row in external.warranties]
    bundles = [_normalize_bundle(row, issues) for row in external.bundles]
    returns = [_normalize_return(row, issues) for row in external.return_policies]

    snapshot = CanonicalMerchantSnapshot(
        schema_version=external.schema_version or SCHEMA_VERSION,
        source_type=external.source_type,
        source_name=external.source_name,
        merchant_name=_as_str(merchant.get("name")),
        merchant_code=_as_str(merchant.get("code")),
        currency=currency,
        products=products,
        variants=variants,
        inventory=inventory,
        delivery_options=[row for row in deliveries if row is not None],
        warranties=[row for row in warranties if row is not None],
        bundles=[row for row in bundles if row is not None],
        return_policies=[row for row in returns if row is not None],
        variant_delivery=_links(external.variant_delivery, "delivery"),
        variant_warranty=_links(external.variant_warranty, "warranty"),
        variant_bundle=_links(external.variant_bundle, "bundle"),
        variant_returns=_links(external.variant_returns, "return"),
        evidence=_normalize_evidence(external.evidence, issues),
    )
    return snapshot, issues


def _links(rows: list[dict[str, Any]], kind: str) -> list[CanonicalVariantLink]:
    out: list[CanonicalVariantLink] = []
    for row in rows:
        sku = _as_str(row.get("sku"))
        code = parse_delivery_code(row.get(f"{kind}_code") or row.get("code"))
        if kind != "delivery":
            code = _as_str(
                row.get(f"{kind}_code") or row.get("code") or row.get("option_code")
            )
            if code:
                code = code.upper()
        if not sku or not code:
            continue
        out.append(
            CanonicalVariantLink(
                sku=sku,
                option_code=code,
                available=_as_bool(row.get("available"), default=True),
            )
        )
    return out


def _normalize_delivery(
    row: dict[str, Any], issues: list[IngestionIssue]
) -> CanonicalDeliveryOption | None:
    code = parse_delivery_code(row.get("code"))
    name = _as_str(row.get("name")) or code
    if not code or not name:
        return None
    loc = f"delivery_options[{code}]"
    merchant_cost = _money_from_row(
        row,
        "merchant_cost",
        "merchant_cost_cents",
        location=f"{loc}.merchant_cost",
        issues=issues,
    )
    customer = _money_from_row(
        row,
        "customer_charge",
        "customer_charge_cents",
        location=f"{loc}.customer_charge",
        issues=issues,
    )
    try:
        days = int(row.get("delivery_days", 0))
    except (TypeError, ValueError):
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_delivery_days",
                "delivery_days must be an integer.",
                loc,
            )
        )
        return None
    if days < 0 or merchant_cost is None or customer is None:
        return None
    return CanonicalDeliveryOption(
        code=code,
        name=name,
        description=_as_str(row.get("description")),
        delivery_days=days,
        merchant_cost_cents=merchant_cost,
        customer_charge_cents=customer,
        enabled=_as_bool(row.get("enabled"), default=True),
    )


def _normalize_warranty(
    row: dict[str, Any], issues: list[IngestionIssue]
) -> CanonicalWarrantyOption | None:
    code = _as_str(row.get("code"))
    name = _as_str(row.get("name")) or code
    if not code or not name:
        return None
    code = code.upper()
    loc = f"warranties[{code}]"
    months = parse_months(
        row.get("months") or row.get("term"), location=loc, issues=issues
    )
    merchant_cost = _money_from_row(
        row,
        "merchant_cost",
        "merchant_cost_cents",
        location=f"{loc}.merchant_cost",
        issues=issues,
    )
    customer = _money_from_row(
        row,
        "customer_price",
        "customer_price_cents",
        location=f"{loc}.customer_price",
        issues=issues,
    )
    if months is None or merchant_cost is None or customer is None:
        return None
    return CanonicalWarrantyOption(
        code=code,
        name=name,
        months=months,
        merchant_cost_cents=merchant_cost,
        customer_price_cents=customer,
        enabled=_as_bool(row.get("enabled"), default=True),
    )


def _normalize_bundle(
    row: dict[str, Any], issues: list[IngestionIssue]
) -> CanonicalBundleOption | None:
    code = _as_str(row.get("code"))
    name = _as_str(row.get("name")) or code
    if not code or not name:
        return None
    code = code.upper()
    loc = f"bundles[{code}]"
    merchant_cost = _money_from_row(
        row,
        "merchant_cost",
        "merchant_cost_cents",
        location=f"{loc}.merchant_cost",
        issues=issues,
    )
    customer = _money_from_row(
        row,
        "customer_price",
        "customer_price_cents",
        location=f"{loc}.customer_price",
        issues=issues,
    )
    if merchant_cost is None or customer is None:
        return None
    attrs = row.get("attributes")
    return CanonicalBundleOption(
        code=code,
        name=name,
        description=_as_str(row.get("description")),
        merchant_cost_cents=merchant_cost,
        customer_price_cents=customer,
        enabled=_as_bool(row.get("enabled"), default=True),
        attributes=dict(attrs) if isinstance(attrs, dict) else None,
    )


def _normalize_return(
    row: dict[str, Any], issues: list[IngestionIssue]
) -> CanonicalReturnPolicy | None:
    code = _as_str(row.get("code"))
    name = _as_str(row.get("name")) or code
    if not code or not name:
        return None
    code = code.upper()
    loc = f"return_policies[{code}]"
    try:
        window = int(row.get("return_window_days") or row.get("window_days") or 0)
    except (TypeError, ValueError):
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_return_window",
                "return_window_days must be a positive integer.",
                loc,
            )
        )
        return None
    if window <= 0:
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_return_window",
                "return_window_days must be a positive integer.",
                loc,
            )
        )
        return None
    rate_raw = row.get("restocking_fee_rate")
    rate: float | None
    if rate_raw in (None, ""):
        rate = None
    else:
        try:
            rate = float(rate_raw)
        except (TypeError, ValueError):
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_restocking_rate",
                    "restocking_fee_rate must be between 0 and 1.",
                    loc,
                )
            )
            return None
        if rate < 0 or rate > 1:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_restocking_rate",
                    "restocking_fee_rate must be between 0 and 1.",
                    loc,
                )
            )
            return None
    cost = None
    if row.get("merchant_expected_cost") not in (None, "") or row.get(
        "merchant_expected_cost_cents"
    ) not in (None, ""):
        cost = _money_from_row(
            row,
            "merchant_expected_cost",
            "merchant_expected_cost_cents",
            location=f"{loc}.merchant_expected_cost",
            issues=issues,
            required=False,
        )
    return CanonicalReturnPolicy(
        code=code,
        name=name,
        return_window_days=window,
        restocking_fee_rate=rate,
        conditions=_as_str(row.get("conditions")),
        merchant_expected_cost_cents=cost,
        enabled=_as_bool(row.get("enabled"), default=True),
    )


def _normalize_evidence(
    rows: list[dict[str, Any]], issues: list[IngestionIssue]
) -> list[CanonicalEvidence]:
    out: list[CanonicalEvidence] = []
    for index, row in enumerate(rows):
        loc = f"evidence[{index}]"
        sku = _as_str(row.get("sku"))
        name = _as_str(row.get("attribute_name") or row.get("field"))
        source_type = (
            _as_str(row.get("source_type")) or "MERCHANT_PRODUCT_FEED"
        ).upper()
        source_name = _as_str(row.get("source_name")) or source_type.replace("_", " ")
        if not sku or not name:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_evidence",
                    "Evidence requires sku and attribute_name.",
                    loc,
                )
            )
            continue
        observed = parse_datetime(row.get("observed_at")) or datetime.now(UTC)
        expires = parse_datetime(row.get("expires_at") or row.get("valid_until"))
        status = (
            _as_str(row.get("verification_status")) or "MERCHANT_DECLARED"
        ).upper()
        confidence = row.get("confidence")
        conf: float | None
        try:
            conf = float(confidence) if confidence not in (None, "") else None
        except (TypeError, ValueError):
            conf = None
        out.append(
            CanonicalEvidence(
                sku=sku,
                attribute_name=name,
                value=row.get("value"),
                source_type=source_type,
                source_name=source_name,
                source_reference=_as_str(
                    row.get("source_reference") or row.get("source_record")
                ),
                verification_status=status,
                observed_at=observed,
                expires_at=expires,
                confidence=conf,
            )
        )
    return out

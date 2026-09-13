"""Validate external merchant feeds. Do not invent missing values."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.ingestion.constants import (
    CURRENCY_AUD,
    PROVENANCE_SOURCE_TYPES,
    SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    VERIFICATION_STATUSES,
)
from app.ingestion.result import IngestionIssue
from app.ingestion.schemas import CanonicalMerchantSnapshot, ExternalMerchantSnapshot


def validate_external(snapshot: ExternalMerchantSnapshot) -> list[IngestionIssue]:
    issues: list[IngestionIssue] = []
    version = snapshot.schema_version or ""
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        issues.append(
            IngestionIssue(
                "ERROR",
                "unsupported_schema_version",
                f"Schema version {version!r} is not supported. "
                f"Expected {SCHEMA_VERSION}.",
                location="schema_version",
            )
        )
    currency = str((snapshot.merchant or {}).get("currency") or CURRENCY_AUD).upper()
    if currency != CURRENCY_AUD:
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_currency",
                f"Phase 6 accepts AUD only. Received {currency}.",
                location="merchant.currency",
            )
        )
    _duplicate_ids(
        issues,
        [row.get("external_id") or row.get("id") for row in snapshot.products],
        entity="product",
        location="products",
    )
    _duplicate_ids(
        issues,
        [row.get("sku") or row.get("external_variant_id") for row in snapshot.variants],
        entity="variant SKU",
        location="variants",
    )
    for index, row in enumerate(snapshot.products):
        loc = f"products[{index}]"
        if not str(row.get("external_id") or row.get("id") or "").strip():
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "missing_product_id",
                    "Product is missing external_id. Name is not an identifier.",
                    location=loc,
                )
            )
        if not str(row.get("name") or "").strip():
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "missing_product_name",
                    "Product name is required.",
                    location=loc,
                )
            )
        if not str(row.get("brand") or "").strip():
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "missing_product_brand",
                    "Product brand is required.",
                    location=loc,
                )
            )
    for index, row in enumerate(snapshot.variants):
        loc = f"variants[{index}]"
        sku = str(row.get("sku") or row.get("external_variant_id") or "").strip()
        if not sku:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "missing_variant_sku",
                    "Variant SKU is required.",
                    location=loc,
                )
            )
        if not str(
            row.get("product_external_id")
            or row.get("product_id")
            or row.get("product")
            or ""
        ).strip():
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "missing_variant_product",
                    f"Variant {sku or index} does not reference a product.",
                    location=loc,
                    record_id=sku or None,
                )
            )
        if _has_cogs_missing(row):
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "missing_cogs",
                    f"Variant {sku or index} has no COGS. "
                    "AstraOS will not invent margin.",
                    location=f"{loc}.cogs",
                    record_id=sku or None,
                )
            )
    _conflict_rows(issues, snapshot.variants, "sku", "variants")
    _conflict_rows(issues, snapshot.products, "external_id", "products", alt="id")
    return issues


def validate_canonical(snapshot: CanonicalMerchantSnapshot) -> list[IngestionIssue]:
    issues: list[IngestionIssue] = []
    if snapshot.currency != CURRENCY_AUD:
        issues.append(
            IngestionIssue(
                "ERROR",
                "invalid_currency",
                f"Phase 6 accepts AUD only. Received {snapshot.currency}.",
                location="merchant.currency",
            )
        )
    products = {row.external_id for row in snapshot.products}
    skus = {row.sku for row in snapshot.variants}
    deliveries = {row.code for row in snapshot.delivery_options}
    warranties = {row.code for row in snapshot.warranties}
    bundles = {row.code for row in snapshot.bundles}
    returns = {row.code for row in snapshot.return_policies}

    for row in snapshot.variants:
        if row.product_external_id not in products:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "orphan_variant",
                    f"Variant SKU {row.sku} references unknown product "
                    f"{row.product_external_id}.",
                    location=f"variants[{row.sku}].product_external_id",
                    record_id=row.sku,
                )
            )
        if row.currency != CURRENCY_AUD:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_currency",
                    f"Variant {row.sku} currency {row.currency} is not AUD.",
                    location=f"variants[{row.sku}].currency",
                    record_id=row.sku,
                )
            )
        if row.base_price_cents <= 0:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "non_positive_price",
                    f"Variant {row.sku} price must be greater than zero.",
                    location=f"variants[{row.sku}].price",
                    record_id=row.sku,
                )
            )
        if row.cogs_cents < 0:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "negative_cogs",
                    f"Variant {row.sku} COGS cannot be negative.",
                    location=f"variants[{row.sku}].cogs",
                    record_id=row.sku,
                )
            )

    for stock in snapshot.inventory:
        if stock.sku not in skus:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "orphan_inventory",
                    f"Inventory references unknown SKU {stock.sku}.",
                    location=f"inventory[{stock.sku}]",
                    record_id=stock.sku,
                )
            )
        if stock.units_available < 0:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "negative_inventory",
                    f"Inventory for {stock.sku} cannot be negative.",
                    location=f"inventory[{stock.sku}]",
                    record_id=stock.sku,
                )
            )

    _link_refs(issues, snapshot.variant_delivery, skus, deliveries, "delivery")
    _link_refs(issues, snapshot.variant_warranty, skus, warranties, "warranty")
    _link_refs(issues, snapshot.variant_bundle, skus, bundles, "bundle")
    _link_refs(issues, snapshot.variant_returns, skus, returns, "return")

    for fact in snapshot.evidence:
        if fact.sku not in skus:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "orphan_evidence",
                    f"Evidence for {fact.attribute_name} references "
                    f"unknown SKU {fact.sku}.",
                    location=f"evidence[{fact.sku}].{fact.attribute_name}",
                    record_id=fact.sku,
                )
            )
        if fact.source_type not in PROVENANCE_SOURCE_TYPES:
            issues.append(
                IngestionIssue(
                    "WARNING",
                    "unknown_source_type",
                    f"Evidence source_type {fact.source_type} is not "
                    "a named provenance type.",
                    location=f"evidence[{fact.sku}].source_type",
                    record_id=fact.sku,
                )
            )
        if fact.verification_status not in VERIFICATION_STATUSES:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "invalid_verification_status",
                    f"Evidence verification_status "
                    f"{fact.verification_status} is not supported.",
                    location=f"evidence[{fact.sku}].verification_status",
                    record_id=fact.sku,
                )
            )
    return issues


def humanize_issue(issue: IngestionIssue) -> str:
    return issue.message


def _duplicate_ids(
    issues: list[IngestionIssue],
    values: list[Any],
    *,
    entity: str,
    location: str,
) -> None:
    cleaned = [str(value).strip() for value in values if str(value or "").strip()]
    counts = Counter(cleaned)
    for value, count in counts.items():
        if count > 1:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "duplicate_external_id",
                    f"Duplicate {entity} {value} appears {count} times.",
                    location=location,
                    record_id=value,
                )
            )


def _conflict_rows(
    issues: list[IngestionIssue],
    rows: list[dict[str, Any]],
    key: str,
    location: str,
    alt: str | None = None,
) -> None:
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        ident = str(row.get(key) or (row.get(alt) if alt else "") or "").strip()
        if not ident:
            continue
        previous = seen.get(ident)
        if previous is None:
            seen[ident] = row
            continue
        if previous != row:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    "conflicting_record",
                    f"{location} record {ident} appears with conflicting values.",
                    location=location,
                    record_id=ident,
                )
            )


def _link_refs(
    issues: list[IngestionIssue],
    links: list[Any],
    skus: set[str],
    codes: set[str],
    kind: str,
) -> None:
    if not codes:
        return
    for link in links:
        if link.sku not in skus:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    f"orphan_{kind}_link",
                    f"{kind.title()} link references unknown SKU {link.sku}.",
                    location=f"variant_{kind}[{link.sku}]",
                    record_id=link.sku,
                )
            )
        if link.option_code not in codes:
            issues.append(
                IngestionIssue(
                    "ERROR",
                    f"invalid_{kind}_reference",
                    f"SKU {link.sku} references unknown {kind} {link.option_code}.",
                    location=f"variant_{kind}[{link.sku}]",
                    record_id=link.sku,
                )
            )


def _has_cogs_missing(row: dict[str, Any]) -> bool:
    return row.get("cogs") in (None, "") and row.get("cogs_cents") in (None, "")

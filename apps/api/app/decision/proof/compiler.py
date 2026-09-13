"""Deterministic offer/match proof. No LLM. No invented facts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.proof.coverage import coverage_of
from app.decision.proof.derived import derive_lightweight, derive_same_day
from app.decision.proof.freshness import freshness_of, operational_freshness
from app.decision.proof.models import (
    ProofBundle,
    ProofGroup,
    ProofItem,
)
from app.decision.proof.resolver import resolve_attribute
from app.decision.retrieval.models import RankedProductMatch

_DISPLAY = {
    "anc": ("ANC", None),
    "wireless": ("Wireless", None),
    "foldable": ("Foldable", None),
    "microphone": ("Built-in microphone", None),
    "battery_hours": ("battery", "h"),
    "weight_g": ("weight", "g"),
    "comfort_score": ("Comfort score", None),
    "travel_score": ("Travel score", None),
    "water_resistance": ("Water resistance", None),
    "same_day": ("Same-day capable", None),
    "same_day_delivery": ("Same-day delivery", None),
    "base_price_cents": ("Price", "AUD cents"),
    "units_available": ("In stock", "units"),
}

def _display(attribute: str, value: Any) -> tuple[str, str | None]:
    label, unit = _DISPLAY.get(attribute, (attribute, None))
    if attribute == "battery_hours":
        return f"{value}h battery", "h"
    if attribute == "weight_g":
        return f"{value}g", "g"
    if isinstance(value, bool):
        return label if value else f"No {label.lower()}", unit
    return f"{label} {value}", unit


def _from_evidence(
    snapshot: VariantSnapshot,
    attribute: str,
    *,
    group: ProofGroup = "PRODUCT",
    value: Any | None = None,
) -> ProofItem | None:
    evidence, verification = resolve_attribute(snapshot, attribute)
    if evidence is None:
        return None
    if verification == "CONFLICTED":
        item_value = evidence.value if value is None else value
        return ProofItem(
            claim_key=attribute,
            display_claim=_display(attribute, item_value)[0],
            value=item_value,
            unit=_display(attribute, item_value)[1],
            evidence_id=evidence.id,
            source_type=evidence.source_type,
            source_name=evidence.source_name,
            source_record_id=evidence.source_reference,
            verification_status="CONFLICTED",
            freshness_status=freshness_of(evidence, attribute=attribute),
            observed_at=evidence.observed_at,
            valid_until=evidence.expires_at,
            group=group,
            sku=snapshot.sku,
            incomplete=True,
        )
    shown = evidence.value if value is None else value
    label, unit = _display(attribute, shown)
    return ProofItem(
        claim_key=attribute,
        display_claim=label,
        value=shown,
        unit=unit,
        evidence_id=evidence.id,
        source_type=evidence.source_type,
        source_name=evidence.source_name,
        source_record_id=evidence.source_reference or snapshot.sku,
        verification_status=verification,
        freshness_status=freshness_of(evidence, attribute=attribute),
        observed_at=evidence.observed_at,
        valid_until=evidence.expires_at,
        group=group,
        sku=snapshot.sku,
    )


def compile_match_proof(
    snapshot: VariantSnapshot, match: RankedProductMatch
) -> ProofBundle:
    items: list[ProofItem] = []
    seen: set[str] = set()
    for reason in match.reasons:
        for fact in reason.facts:
            if fact.attribute in seen:
                continue
            seen.add(fact.attribute)
            if fact.attribute == "same_day":
                derived = derive_same_day(snapshot)
                if derived:
                    items.append(
                        ProofItem(
                            claim_key="same_day",
                            display_claim=str(derived["display_claim"]),
                            value=True,
                            source_type=str(derived["source_type"]),
                            source_name=str(derived.get("source_name")),
                            source_record_id=str(derived.get("source_record_id")),
                            verification_status="VERIFIED",
                            freshness_status="CURRENT",
                            derived=True,
                            derivation_rule=str(derived["derivation_rule"]),
                            group="DELIVERY",
                            sku=snapshot.sku,
                        )
                    )
                continue
            item = _from_evidence(snapshot, fact.attribute, value=fact.value)
            if item is not None and not item.incomplete:
                items.append(item)
    light = derive_lightweight(snapshot)
    if light and resolve_attribute(snapshot, "weight_g")[0] is not None:
        weight = _from_evidence(snapshot, "weight_g")
        items.append(
            ProofItem(
                claim_key="lightweight",
                display_claim=str(light["display_claim"]),
                value=True,
                source_type=weight.source_type if weight else "DERIVED",
                source_name=weight.source_name if weight else None,
                source_record_id=weight.source_record_id if weight else snapshot.sku,
                evidence_id=weight.evidence_id if weight else None,
                verification_status=(
                    weight.verification_status if weight else "UNKNOWN"
                ),
                freshness_status=weight.freshness_status if weight else "UNKNOWN",
                observed_at=weight.observed_at if weight else None,
                derived=True,
                derivation_rule=str(light["derivation_rule"]),
                group="PRODUCT",
                sku=snapshot.sku,
            )
        )
    issued = datetime.now(UTC)
    return ProofBundle(
        items=items,
        coverage=coverage_of(items),
        issued_at=issued,
    )


def compile_offer_proof(
    snapshot: VariantSnapshot,
    offer: dict[str, Any],
    *,
    match: RankedProductMatch | None = None,
) -> ProofBundle:
    items: list[ProofItem] = []
    if match is not None:
        items.extend(compile_match_proof(snapshot, match).items)
    pricing = offer.get("pricing") or {}
    price = pricing.get("total_price_cents") or pricing.get("product_price_cents")
    price_item = _from_evidence(
        snapshot, "base_price_cents", group="PRICE", value=price
    )
    if price is not None and price_item is None:
        price_item = ProofItem(
            claim_key="price",
            display_claim=f"A${int(price) / 100:.2f}",
            value=price,
            unit="AUD cents",
            source_type="PRICING_FEED",
            source_name="variant commercial price",
            source_record_id=snapshot.sku,
            verification_status="VERIFIED",
            freshness_status="CURRENT",
            derived=True,
            derivation_rule="variant_list_price_v1",
            group="PRICE",
            sku=snapshot.sku,
        )
    elif price_item is not None:
        price_item = price_item.model_copy(
            update={
                "claim_key": "price",
                "display_claim": f"A${int(price or price_item.value) / 100:.2f}",
                "value": price or price_item.value,
                "group": "PRICE",
            }
        )
    if price_item:
        items.append(price_item)
    delivery = offer.get("delivery") or {}
    if delivery.get("code"):
        items.append(
            ProofItem(
                claim_key="delivery",
                display_claim=str(delivery.get("name") or delivery["code"]),
                value=delivery.get("code"),
                source_type="FULFILMENT_CONFIGURATION",
                source_name=delivery.get("name"),
                source_record_id=str(delivery.get("code")),
                verification_status="VERIFIED",
                freshness_status="CURRENT",
                derived=True,
                derivation_rule="selected_delivery_option_v1",
                group="DELIVERY",
                sku=snapshot.sku,
            )
        )
        days = delivery.get("days")
        if days is not None and int(days) <= 0:
            items.append(
                ProofItem(
                    claim_key="same_day_delivery",
                    display_claim="Same-day delivery",
                    value=True,
                    source_type="FULFILMENT_CONFIGURATION",
                    source_name=delivery.get("name"),
                    source_record_id=str(delivery.get("code")),
                    verification_status="VERIFIED",
                    freshness_status="CURRENT",
                    derived=True,
                    derivation_rule="selected_delivery_option_v1",
                    group="DELIVERY",
                    sku=snapshot.sku,
                )
            )
    warranty = offer.get("warranty") or {}
    if warranty.get("code"):
        items.append(
            ProofItem(
                claim_key="warranty",
                display_claim=str(warranty.get("name") or warranty["code"]),
                value=warranty.get("months"),
                unit="months",
                source_type="WARRANTY_POLICY",
                source_name=warranty.get("name"),
                source_record_id=str(warranty.get("code")),
                verification_status="VERIFIED",
                freshness_status="CURRENT",
                derived=True,
                derivation_rule="selected_warranty_option_v1",
                group="WARRANTY",
                sku=snapshot.sku,
            )
        )
    bundle = offer.get("bundle") or {}
    if bundle.get("code"):
        items.append(
            ProofItem(
                claim_key="bundle",
                display_claim=str(bundle.get("name") or bundle["code"]),
                value=bundle.get("code"),
                source_type="BUNDLE_CONFIGURATION",
                source_name=bundle.get("name"),
                source_record_id=str(bundle.get("code")),
                verification_status="VERIFIED",
                freshness_status="CURRENT",
                derived=True,
                derivation_rule="selected_bundle_option_v1",
                group="BUNDLE",
                sku=snapshot.sku,
            )
        )
    returns = offer.get("returns") or {}
    if returns.get("code"):
        items.append(
            ProofItem(
                claim_key="returns",
                display_claim=str(returns.get("name") or returns["code"]),
                value=returns.get("window_days") or returns.get("code"),
                source_type="RETURN_POLICY",
                source_name=returns.get("name"),
                source_record_id=str(returns.get("code")),
                verification_status="VERIFIED",
                freshness_status="CURRENT",
                derived=True,
                derivation_rule="selected_return_policy_v1",
                group="RETURNS",
                sku=snapshot.sku,
            )
        )
    stock = _from_evidence(snapshot, "units_available", group="INVENTORY")
    if stock is None and snapshot.inventory is not None:
        stock = ProofItem(
            claim_key="units_available",
            display_claim="In stock",
            value=snapshot.inventory.sellable_units,
            unit="units",
            source_type="MERCHANT_INVENTORY",
            source_name="inventory_records",
            source_record_id=snapshot.sku,
            verification_status="VERIFIED",
            freshness_status=operational_freshness(
                updated_at=snapshot.inventory.updated_at,
                attribute="units_available",
            ),
            derived=True,
            derivation_rule="inventory_on_hand_v1",
            group="INVENTORY",
            sku=snapshot.sku,
        )
    if stock:
        items.append(stock)
    commercial = [
        item
        for item in items
        if item.group in {"PRICE", "DELIVERY", "WARRANTY", "BUNDLE", "RETURNS"}
    ]
    issued = datetime.now(UTC)
    return ProofBundle(
        items=_dedupe(items),
        coverage=coverage_of(
            _dedupe(items),
            commercial_terms=len(commercial),
            commercial_with_proof=sum(
                1 for item in commercial if item.evidence_id or item.derived
            ),
        ),
        issued_at=issued,
    )


def attach_proof_bundle(
    offer: dict[str, Any],
    match_proof: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items = list(match_proof or [])
    items.extend(
        item.model_dump(mode="json")
        for item in compile_commercial_terms(offer, sku=offer.get("sku"))
    )
    offer["proof_bundle"] = {
        "items": _dedupe_dicts(items),
        "issued_at": datetime.now(UTC).isoformat(),
    }
    return offer


def _dedupe_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = f"{item.get('claim_key')}:{item.get('value')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def compile_commercial_terms(
    offer: dict[str, Any], *, sku: str | None = None
) -> list[ProofItem]:
    """Operational terms from the selected offer. No product attributes invented."""
    return [
        item
        for item in compile_offer_proof(
            _empty_snapshot(sku),
            offer,
        ).items
        if item.group in {"PRICE", "DELIVERY", "WARRANTY", "BUNDLE", "RETURNS"}
    ]


def _empty_snapshot(sku: str | None) -> VariantSnapshot:
    from uuid import uuid4

    from app.decision.eligibility.snapshot import VariantSnapshot

    return VariantSnapshot(
        product_id=uuid4(),
        variant_id=uuid4(),
        sku=sku or "",
        product_name="",
        brand="",
        category="",
        variant_name=None,
        base_price_cents=1,
        attributes={},
        inventory=None,
        deliveries=[],
        evidence=[],
    )


def _dedupe(items: list[ProofItem]) -> list[ProofItem]:
    seen: set[str] = set()
    out: list[ProofItem] = []
    for item in items:
        key = f"{item.claim_key}:{item.value}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out

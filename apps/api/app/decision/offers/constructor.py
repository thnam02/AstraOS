"""Cartesian offer construction. Does not rank or recommend."""

from __future__ import annotations

import itertools
import uuid
from datetime import UTC, datetime
from typing import Any

from app.decision.intent.models import ShoppingIntent
from app.decision.offers.bundles import trigger_labels_for
from app.decision.offers.buyer_constraints import buyer_price_reasons
from app.decision.offers.dimensions import (
    BundleDim,
    DeliveryDim,
    ReturnDim,
    WarrantyDim,
    delivery_meets_intent,
    load_bundles,
    load_deliveries,
    load_returns,
    load_warranties,
)
from app.decision.offers.feasibility import combination_reasons, variant_blockers
from app.decision.offers.models import (
    CONSTRUCTION_VERSION,
    CURRENCY,
    BundleRelevance,
    ConstructionLimits,
    ConstructionStatus,
    FeasibilityStatus,
    OfferCandidate,
    OfferProof,
    PriceOption,
    RejectionCode,
    RejectionReason,
)
from app.decision.offers.prices import generate_price_options
from app.models import MerchantPolicy, ProductVariant


def _cap(items: list[Any], limit: int) -> list[Any]:
    return items[: max(limit, 0)]


def estimate_count(
    prices: int,
    deliveries: int,
    warranties: int,
    bundles: int,
    returns: int,
) -> int:
    return prices * deliveries * warranties * bundles * returns


def prune_limits(
    *,
    product_count: int,
    dim_counts: list[tuple[int, int, int, int, int]],
    limits: ConstructionLimits,
) -> tuple[ConstructionLimits, str | None, int]:
    """Shrink products then dimensions until estimated size fits."""
    working = limits.model_copy()
    estimated = sum(
        estimate_count(
            min(p, working.max_price_options),
            min(d, working.max_delivery_options),
            min(w, working.max_warranty_options),
            min(b, working.max_bundles_per_product),
            min(r, working.max_return_options),
        )
        for p, d, w, b, r in dim_counts[:product_count]
    )
    if estimated <= working.max_total_candidates:
        return working, None, estimated

    reason = "reduced_product_count"
    while product_count > 1 and estimated > working.max_total_candidates:
        product_count -= 1
        estimated = sum(
            estimate_count(
                min(p, working.max_price_options),
                min(d, working.max_delivery_options),
                min(w, working.max_warranty_options),
                min(b, working.max_bundles_per_product),
                min(r, working.max_return_options),
            )
            for p, d, w, b, r in dim_counts[:product_count]
        )
    if estimated <= working.max_total_candidates:
        working.max_products = product_count
        return working, reason, estimated

    def _recount() -> int:
        return sum(
            estimate_count(
                min(p, working.max_price_options),
                min(d, working.max_delivery_options),
                min(w, working.max_warranty_options),
                min(b, working.max_bundles_per_product),
                min(r, working.max_return_options),
            )
            for p, d, w, b, r in dim_counts[:product_count]
        )

    reductions: tuple[tuple[str, str], ...] = (
        ("max_price_options", "reduced_price_options"),
        ("max_bundles_per_product", "reduced_bundle_options"),
        ("max_warranty_options", "reduced_warranty_options"),
        ("max_delivery_options", "reduced_delivery_options"),
        ("max_return_options", "reduced_return_options"),
    )
    for field, label in reductions:
        while getattr(working, field) > 1 and estimated > working.max_total_candidates:
            setattr(working, field, getattr(working, field) - 1)
            reason = label
            estimated = _recount()
        if estimated <= working.max_total_candidates:
            break

    working.max_products = product_count
    return working, reason, estimated


def _intervention(
    price: PriceOption,
    delivery: DeliveryDim,
    warranty: WarrantyDim,
    bundle: BundleDim,
    returns: ReturnDim,
) -> int:
    return (
        price.adjustment_cents
        + delivery.merchant_cost_cents
        + warranty.merchant_cost_cents
        + bundle.merchant_cost_cents
        + int(returns.expected_cost_cents or 0)
    )


def _proofs(
    variant: ProductVariant,
    price: PriceOption,
    delivery: DeliveryDim,
    warranty: WarrantyDim,
    bundle: BundleDim,
    returns: ReturnDim,
) -> list[OfferProof]:
    now = datetime.now(UTC)
    inventory = variant.inventory
    proofs = [
        OfferProof(
            type="product",
            value=variant.sku,
            source="CATALOGUE",
            source_name="product_variants",
        ),
        OfferProof(
            type="price",
            value=price.final_price_cents,
            source="PRICING",
            source_name="product_variants.base_price_cents",
        ),
        OfferProof(
            type="delivery",
            value=delivery.code,
            source="FULFILMENT",
            source_name="variant_delivery_options",
            updated_at=delivery.updated_at or now,
        ),
        OfferProof(
            type="warranty",
            value=warranty.code,
            source="WARRANTY",
            source_name="variant_warranty_options",
        ),
        OfferProof(
            type="bundle",
            value=bundle.code,
            source="BUNDLE",
            source_name="variant_bundle_options",
        ),
        OfferProof(
            type="returns",
            value=returns.code,
            source="RETURNS",
            source_name="variant_return_policies",
        ),
    ]
    if inventory is not None:
        proofs.append(
            OfferProof(
                type="inventory",
                value=inventory.units_available - inventory.units_reserved,
                source="INVENTORY",
                source_name="inventory_records",
                updated_at=inventory.updated_at,
            )
        )
    for row in variant.evidence:
        if row.attribute_name in {"base_price_cents", "anc", "wireless"}:
            source = row.source
            proofs.append(
                OfferProof(
                    type=row.attribute_name,
                    value=row.value,
                    source=source.source_type if source else "EVIDENCE",
                    source_name=source.name if source else None,
                    evidence_id=str(row.id),
                    updated_at=row.observed_at,
                )
            )
    return proofs


def _assemble(
    *,
    variant: ProductVariant,
    intent: ShoppingIntent,
    price: PriceOption,
    delivery: DeliveryDim,
    warranty: WarrantyDim,
    bundle: BundleDim,
    returns: ReturnDim,
    reasons: list[RejectionReason],
    expires_at: datetime,
    metadata: dict[str, Any],
) -> OfferCandidate:
    total = (
        price.final_price_cents
        + delivery.customer_charge_cents
        + warranty.customer_price_cents
        + bundle.customer_price_cents
    )
    operational = list(reasons)
    buyer_reasons = buyer_price_reasons(
        intent=intent,
        total_customer_price_cents=total,
        product_price_cents=price.final_price_cents,
    )
    seen_codes: set[str] = set()
    unique_reasons: list[RejectionReason] = []
    for reason in [*operational, *buyer_reasons]:
        if reason.code.value in seen_codes:
            continue
        seen_codes.add(reason.code.value)
        unique_reasons.append(reason)
    reasons = unique_reasons
    blocked = any(
        item.code
        in {
            RejectionCode.PRODUCT_INACTIVE,
            RejectionCode.OUT_OF_STOCK,
            RejectionCode.MISSING_OPERATIONAL_DATA,
        }
        for item in operational
    )
    relevance = None
    if bundle.code != "NONE":
        relevance = BundleRelevance(
            code=bundle.code,
            name=bundle.name,
            triggered_by=trigger_labels_for(bundle.code, intent),
            variant_compatible=bundle.available and bundle.enabled,
            merchant_available=bundle.available and bundle.enabled,
        )
    return OfferCandidate(
        id=uuid.uuid4(),
        product_id=variant.product_id,
        variant_id=variant.id,
        sku=variant.sku,
        product_name=variant.product.name,
        brand=variant.product.brand,
        variant_name=variant.variant_name,
        currency=variant.currency or CURRENCY,
        base_price_cents=variant.base_price_cents,
        price_adjustment_cents=price.adjustment_cents,
        final_product_price_cents=price.final_price_cents,
        price_adjustment_type=price.adjustment_type,
        price_adjustment_rate=price.adjustment_rate,
        delivery_option_id=delivery.option_id,
        delivery_code=delivery.code,
        delivery_name=delivery.name,
        delivery_days=delivery.days,
        delivery_customer_charge_cents=delivery.customer_charge_cents,
        delivery_merchant_cost_cents=delivery.merchant_cost_cents,
        warranty_option_id=warranty.option_id,
        warranty_code=warranty.code,
        warranty_name=warranty.name,
        warranty_months=warranty.months,
        warranty_customer_price_cents=warranty.customer_price_cents,
        warranty_merchant_cost_cents=warranty.merchant_cost_cents,
        bundle_option_id=bundle.option_id,
        bundle_code=None if bundle.code == "NONE" else bundle.code,
        bundle_name=None if bundle.code == "NONE" else bundle.name,
        bundle_customer_price_cents=bundle.customer_price_cents,
        bundle_merchant_cost_cents=bundle.merchant_cost_cents,
        bundle_relevance=relevance,
        return_policy_id=returns.option_id,
        return_policy_code=returns.code,
        return_policy_name=returns.name,
        return_window_days=returns.window_days,
        return_policy_expected_cost_cents=returns.expected_cost_cents,
        total_customer_price_cents=total,
        direct_intervention_cost_cents=_intervention(
            price, delivery, warranty, bundle, returns
        ),
        construction_status=(
            ConstructionStatus.BLOCKED if blocked else ConstructionStatus.GENERATED
        ),
        feasibility_status=(
            FeasibilityStatus.REJECTED if operational else FeasibilityStatus.FEASIBLE
        ),
        rejection_reasons=reasons,
        proof=_proofs(variant, price, delivery, warranty, bundle, returns),
        construction_metadata={
            **metadata,
            "construction_version": CONSTRUCTION_VERSION,
        },
        expires_at=expires_at,
    )


def construct_variant(
    *,
    variant: ProductVariant,
    intent: ShoppingIntent,
    policy: MerchantPolicy,
    relevant_bundles: set[str],
    limits: ConstructionLimits,
    expires_at: datetime,
) -> tuple[list[OfferCandidate], dict[str, int]]:
    prices = generate_price_options(
        variant.base_price_cents,
        policy.maximum_discount_rate,
        limit=limits.max_price_options,
    )
    deliveries = _cap(load_deliveries(variant), limits.max_delivery_options)
    warranties = _cap(load_warranties(variant), limits.max_warranty_options)
    bundles = _cap(
        load_bundles(variant, relevant_bundles), limits.max_bundles_per_product
    )
    returns = _cap(load_returns(variant), limits.max_return_options)

    blockers = variant_blockers(variant)
    candidates: list[OfferCandidate] = []
    if not prices or not deliveries or not warranties or not returns:
        return candidates, {
            "prices": len(prices),
            "deliveries": len(deliveries),
            "warranties": len(warranties),
            "bundles": len(bundles),
            "returns": len(returns),
            "estimated": 0,
        }

    for price, delivery, warranty, bundle, ret in itertools.product(
        prices, deliveries, warranties, bundles, returns
    ):
        reasons = list(blockers)
        reasons.extend(
            combination_reasons(
                price=price,
                delivery=delivery,
                warranty=warranty,
                bundle=bundle,
                returns=ret,
                policy=policy,
                delivery_allowed=delivery_meets_intent(delivery.days, intent),
                bundles_enabled=policy.bundle_enabled,
            )
        )
        # Deduplicate codes while keeping first message.
        seen: set[str] = set()
        unique: list[RejectionReason] = []
        for reason in reasons:
            if reason.code.value in seen:
                continue
            seen.add(reason.code.value)
            unique.append(reason)
        candidates.append(
            _assemble(
                variant=variant,
                intent=intent,
                price=price,
                delivery=delivery,
                warranty=warranty,
                bundle=bundle,
                returns=ret,
                reasons=unique,
                expires_at=expires_at,
                metadata={
                    "price_options": len(prices),
                    "delivery_options": len(deliveries),
                    "warranty_options": len(warranties),
                    "bundle_options": len(bundles),
                    "return_options": len(returns),
                },
            )
        )
    return candidates, {
        "prices": len(prices),
        "deliveries": len(deliveries),
        "warranties": len(warranties),
        "bundles": len(bundles),
        "returns": len(returns),
        "estimated": estimate_count(
            len(prices),
            len(deliveries),
            len(warranties),
            len(bundles),
            len(returns),
        ),
    }

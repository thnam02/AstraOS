"""Static feasibility. Not contribution-margin optimisation."""

from app.decision.offers.dimensions import (
    BundleDim,
    DeliveryDim,
    ReturnDim,
    WarrantyDim,
)
from app.decision.offers.models import (
    PriceOption,
    RejectionCode,
    RejectionReason,
)
from app.decision.offers.prices import money_rate
from app.models import MerchantPolicy, ProductVariant


def sellable_units(variant: ProductVariant) -> int | None:
    inventory = variant.inventory
    if inventory is None:
        return None
    return int(inventory.units_available) - int(inventory.units_reserved)


def variant_blockers(variant: ProductVariant) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    if not variant.is_active or not variant.product.is_active:
        reasons.append(
            RejectionReason(
                code=RejectionCode.PRODUCT_INACTIVE,
                message="Product or variant is inactive.",
            )
        )
    units = sellable_units(variant)
    if units is None:
        reasons.append(
            RejectionReason(
                code=RejectionCode.MISSING_OPERATIONAL_DATA,
                message="Inventory is missing; availability is unknown.",
            )
        )
    elif units <= 0:
        reasons.append(
            RejectionReason(
                code=RejectionCode.OUT_OF_STOCK,
                message="No sellable units (available minus reserved).",
            )
        )
    return reasons


def combination_reasons(
    *,
    price: PriceOption,
    delivery: DeliveryDim,
    warranty: WarrantyDim,
    bundle: BundleDim,
    returns: ReturnDim,
    policy: MerchantPolicy,
    delivery_allowed: bool,
    bundles_enabled: bool,
) -> list[RejectionReason]:
    reasons: list[RejectionReason] = []
    cap = money_rate(policy.maximum_discount_rate)
    if price.adjustment_rate > cap:
        reasons.append(
            RejectionReason(
                code=RejectionCode.DISCOUNT_EXCEEDS_AUTHORITY,
                message=(
                    f"Discount {price.adjustment_rate} exceeds "
                    f"maximum_discount_rate {cap}."
                ),
            )
        )
    if not delivery.available or not delivery.enabled or not delivery_allowed:
        reasons.append(
            RejectionReason(
                code=RejectionCode.DELIVERY_NOT_AVAILABLE,
                message=f"Delivery {delivery.code} is not usable for this request.",
            )
        )
    if not warranty.available or not warranty.enabled:
        reasons.append(
            RejectionReason(
                code=RejectionCode.WARRANTY_NOT_AVAILABLE,
                message=f"Warranty {warranty.code} is not available.",
            )
        )
    elif not policy.warranty_upgrade_enabled and not warranty.is_standard:
        reasons.append(
            RejectionReason(
                code=RejectionCode.WARRANTY_NOT_AVAILABLE,
                message="Warranty upgrades are disabled by merchant policy.",
            )
        )
    if bundle.code != "NONE":
        if not bundles_enabled or not policy.bundle_enabled:
            reasons.append(
                RejectionReason(
                    code=RejectionCode.BUNDLE_INCOMPATIBLE,
                    message="Bundles are disabled by merchant policy.",
                )
            )
        elif not bundle.available or not bundle.enabled:
            reasons.append(
                RejectionReason(
                    code=RejectionCode.BUNDLE_INCOMPATIBLE,
                    message=f"Bundle {bundle.code} is not available on this SKU.",
                )
            )
        elif not bundle.context_relevant:
            reasons.append(
                RejectionReason(
                    code=RejectionCode.BUNDLE_INCOMPATIBLE,
                    message=f"Bundle {bundle.code} is not context-relevant.",
                )
            )
    if not returns.available or not returns.enabled:
        reasons.append(
            RejectionReason(
                code=RejectionCode.RETURN_POLICY_DISABLED,
                message=f"Return policy {returns.code} is not available.",
            )
        )
    elif returns.is_flexible and not policy.flexible_returns_enabled:
        reasons.append(
            RejectionReason(
                code=RejectionCode.RETURN_POLICY_DISABLED,
                message="Flexible returns are disabled by merchant policy.",
            )
        )
    return reasons

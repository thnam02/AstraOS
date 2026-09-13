"""Offer-level merchant guardrails. Unsafe offers never reach the frontier."""

from pydantic import BaseModel, Field

from app.decision.economics.models import OfferEconomics
from app.decision.intent.models import ShoppingIntent
from app.decision.offers.buyer_constraints import (
    buyer_price_reasons,
    observed_price_cents,
)
from app.decision.offers.dimensions import delivery_meets_intent
from app.decision.intent.normalizer import expected_value
from app.decision.intent.price import price_constraints
from app.decision.offers.models import FeasibilityStatus, OfferCandidate, RejectionCode
from app.decision.offers.prices import money_rate
from app.decision.policies.rejection_codes import PolicyRejectionCode
from app.models import MerchantPolicy


class PolicyCheck(BaseModel):
    code: str
    passed: bool
    message: str
    observed: str | int | float | None = None
    limit: str | int | float | None = None


class OfferPolicyEvaluation(BaseModel):
    policy_safe: bool
    checks: list[PolicyCheck] = Field(default_factory=list)
    rejection_codes: list[str] = Field(default_factory=list)


_CONSTRUCTION_MAP: dict[RejectionCode, PolicyRejectionCode] = {
    RejectionCode.OUT_OF_STOCK: PolicyRejectionCode.OUT_OF_STOCK,
    RejectionCode.DELIVERY_NOT_AVAILABLE: PolicyRejectionCode.DELIVERY_DISABLED,
    RejectionCode.WARRANTY_NOT_AVAILABLE: PolicyRejectionCode.WARRANTY_DISABLED,
    RejectionCode.BUNDLE_INCOMPATIBLE: PolicyRejectionCode.BUNDLE_DISABLED,
    RejectionCode.RETURN_POLICY_DISABLED: PolicyRejectionCode.RETURNS_DISABLED,
    RejectionCode.DISCOUNT_EXCEEDS_AUTHORITY: (
        PolicyRejectionCode.DISCOUNT_EXCEEDS_LIMIT
    ),
    RejectionCode.PRODUCT_INACTIVE: PolicyRejectionCode.PRODUCT_INACTIVE,
    RejectionCode.MISSING_OPERATIONAL_DATA: (
        PolicyRejectionCode.MISSING_OPERATIONAL_DATA
    ),
    RejectionCode.BUYER_MAX_TOTAL_EXCEEDED: (
        PolicyRejectionCode.BUYER_MAX_TOTAL_EXCEEDED
    ),
    RejectionCode.BUYER_MAX_PRODUCT_PRICE_EXCEEDED: (
        PolicyRejectionCode.BUYER_MAX_PRODUCT_PRICE_EXCEEDED
    ),
}


def _add(
    checks: list[PolicyCheck],
    *,
    code: PolicyRejectionCode,
    passed: bool,
    message: str,
    observed: str | int | float | None = None,
    limit: str | int | float | None = None,
) -> None:
    checks.append(
        PolicyCheck(
            code=code.value,
            passed=passed,
            message=message,
            observed=observed,
            limit=limit,
        )
    )


def evaluate_offer_policy(
    offer: OfferCandidate,
    *,
    economics: OfferEconomics,
    policy: MerchantPolicy,
    intent: ShoppingIntent,
    sellable_units: int | None,
    product_active: bool = True,
) -> OfferPolicyEvaluation:
    """Evaluate current merchant policy against one constructed offer."""
    checks: list[PolicyCheck] = []
    floor = money_rate(policy.minimum_margin_rate)
    cap = money_rate(policy.maximum_discount_rate)
    rate = economics.contribution_margin_rate
    _add(
        checks,
        code=PolicyRejectionCode.MARGIN_BELOW_FLOOR,
        passed=rate >= floor,
        message=(
            f"Contribution rate {rate} "
            f"{'meets' if rate >= floor else 'is below'} floor {floor}."
        ),
        observed=str(rate),
        limit=str(floor),
    )
    discount = money_rate(offer.price_adjustment_rate)
    _add(
        checks,
        code=PolicyRejectionCode.DISCOUNT_EXCEEDS_LIMIT,
        passed=discount <= cap,
        message=(
            f"Discount {discount} "
            f"{'within' if discount <= cap else 'exceeds'} authority {cap}."
        ),
        observed=str(discount),
        limit=str(cap),
    )

    max_delivery = policy.maximum_delivery_subsidy_cents
    delivery_ok = (
        max_delivery is None or economics.delivery_subsidy_cents <= max_delivery
    )
    _add(
        checks,
        code=PolicyRejectionCode.DELIVERY_SUBSIDY_EXCEEDS_LIMIT,
        passed=delivery_ok,
        message="Delivery subsidy within authority."
        if delivery_ok
        else "Delivery subsidy exceeds merchant cap.",
        observed=economics.delivery_subsidy_cents,
        limit=max_delivery,
    )
    max_warranty = policy.maximum_warranty_subsidy_cents
    warranty_ok = (
        max_warranty is None or economics.warranty_subsidy_cents <= max_warranty
    )
    _add(
        checks,
        code=PolicyRejectionCode.WARRANTY_SUBSIDY_EXCEEDS_LIMIT,
        passed=warranty_ok,
        message="Warranty subsidy within authority."
        if warranty_ok
        else "Warranty subsidy exceeds merchant cap.",
        observed=economics.warranty_subsidy_cents,
        limit=max_warranty,
    )
    max_bundle = policy.maximum_bundle_subsidy_cents
    bundle_ok = max_bundle is None or economics.bundle_subsidy_cents <= max_bundle
    _add(
        checks,
        code=PolicyRejectionCode.BUNDLE_SUBSIDY_EXCEEDS_LIMIT,
        passed=bundle_ok,
        message="Bundle subsidy within authority."
        if bundle_ok
        else "Bundle subsidy exceeds merchant cap.",
        observed=economics.bundle_subsidy_cents,
        limit=max_bundle,
    )

    if sellable_units is None:
        _add(
            checks,
            code=PolicyRejectionCode.MISSING_OPERATIONAL_DATA,
            passed=False,
            message="Inventory is missing; availability is unknown.",
        )
    else:
        _add(
            checks,
            code=PolicyRejectionCode.OUT_OF_STOCK,
            passed=sellable_units > 0,
            message="Sellable stock is available."
            if sellable_units > 0
            else "No sellable units.",
            observed=sellable_units,
            limit=1,
        )

    _add(
        checks,
        code=PolicyRejectionCode.PRODUCT_INACTIVE,
        passed=product_active,
        message="Product is active." if product_active else "Product is inactive.",
    )

    delivery_enabled = True
    if not policy.delivery_subsidy_enabled and economics.delivery_subsidy_cents > 0:
        delivery_enabled = False
    intent_ok = delivery_meets_intent(offer.delivery_days, intent)
    _add(
        checks,
        code=PolicyRejectionCode.DELIVERY_DISABLED,
        passed=delivery_enabled,
        message="Delivery is authorised."
        if delivery_enabled
        else "Delivery subsidy is disabled by merchant policy.",
    )
    _add(
        checks,
        code=PolicyRejectionCode.INTENT_DELIVERY_INCOMPATIBLE,
        passed=intent_ok,
        message="Delivery satisfies the request."
        if intent_ok
        else "Delivery does not satisfy the buyer's mandatory timing.",
    )

    warranty_enabled = True
    upgrade = offer.warranty_code not in {"STANDARD_12", None}
    if upgrade and not policy.warranty_upgrade_enabled:
        warranty_enabled = False
    _add(
        checks,
        code=PolicyRejectionCode.WARRANTY_DISABLED,
        passed=warranty_enabled,
        message="Warranty is authorised."
        if warranty_enabled
        else "Warranty upgrades are disabled by merchant policy.",
    )

    bundle_enabled = True
    if offer.bundle_code and not policy.bundle_enabled:
        bundle_enabled = False
    _add(
        checks,
        code=PolicyRejectionCode.BUNDLE_DISABLED,
        passed=bundle_enabled,
        message="Bundle is authorised."
        if bundle_enabled
        else "Bundles are disabled by merchant policy.",
    )

    returns_enabled = True
    if offer.return_policy_code == "FLEX_60" and not policy.flexible_returns_enabled:
        returns_enabled = False
    _add(
        checks,
        code=PolicyRejectionCode.RETURNS_DISABLED,
        passed=returns_enabled,
        message="Return policy is authorised."
        if returns_enabled
        else "Flexible returns are disabled by merchant policy.",
    )

    price_failures = buyer_price_reasons(
        intent=intent,
        total_customer_price_cents=offer.total_customer_price_cents,
        product_price_cents=offer.final_product_price_cents,
    )
    failed_codes = {item.code for item in price_failures}
    seen_price_codes: set[str] = set()
    for constraint in price_constraints(intent):
        observed, reject_code = observed_price_cents(
            constraint,
            total_customer_price_cents=offer.total_customer_price_cents,
            product_price_cents=offer.final_product_price_cents,
        )
        policy_code = _CONSTRUCTION_MAP[reject_code]
        if policy_code.value in seen_price_codes:
            continue
        seen_price_codes.add(policy_code.value)
        passed = reject_code not in failed_codes
        expected = expected_value(constraint)
        _add(
            checks,
            code=policy_code,
            passed=passed,
            message=(
                "Buyer price constraint holds."
                if passed
                else "Offer exceeds the buyer's mandatory spend."
            ),
            observed=observed,
            limit=expected if isinstance(expected, int | float) else None,
        )

    if offer.feasibility_status == FeasibilityStatus.REJECTED:
        for reason in offer.rejection_reasons:
            mapped = _CONSTRUCTION_MAP.get(reason.code)
            if mapped is None:
                continue
            already = any(item.code == mapped.value for item in checks)
            if already:
                # Keep the live policy check; construction reason is supporting.
                continue
            _add(
                checks,
                code=mapped,
                passed=False,
                message=reason.message,
            )

    rejected = [item.code for item in checks if not item.passed]
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for code in rejected:
        if code in seen:
            continue
        seen.add(code)
        unique.append(code)
    return OfferPolicyEvaluation(
        policy_safe=len(unique) == 0,
        checks=checks,
        rejection_codes=unique,
    )

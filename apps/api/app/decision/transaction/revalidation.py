"""Revalidate an immutable proposal against live merchant state."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.config import settings
from app.decision.economics.calculator import compute_economics
from app.decision.intent.models import ShoppingIntent
from app.decision.offers.buyer_constraints import buyer_price_reasons
from app.decision.intent.price import price_constraints
from app.decision.offers.feasibility import sellable_units
from app.decision.offers.models import OfferCandidate
from app.decision.offers.prices import money_rate
from app.decision.policies.offer_policy_evaluator import evaluate_offer_policy
from app.decision.transaction.models import (
    RevalidationCheck,
    RevalidationCheckStatus,
    TransactionFailureCode,
    TransactionRevalidationResult,
)
from app.models import MerchantPolicy, ProductVariant
from app.models.negotiation import MerchantProposal, NegotiationSession


class TransactionRevalidationService:
    """Never trust Stage 5 scores or client-submitted prices."""

    def validate(
        self,
        *,
        session: NegotiationSession,
        proposal: MerchantProposal,
        variant: ProductVariant | None,
        policy: MerchantPolicy | None,
        offer: OfferCandidate | None,
        quantity: int,
        now: datetime | None = None,
        honor_locked_price: bool | None = None,
    ) -> TransactionRevalidationResult:
        moment = now or datetime.now(UTC)
        honor = (
            settings.honor_locked_proposal_price
            if honor_locked_price is None
            else honor_locked_price
        )
        checks: list[RevalidationCheck] = []
        codes: list[TransactionFailureCode] = []
        snapshot: dict[str, Any] = {}

        def add(
            name: str,
            passed: bool,
            code: TransactionFailureCode | None = None,
            **extra: Any,
        ) -> None:
            checks.append(
                RevalidationCheck(
                    check=name,
                    status=(
                        RevalidationCheckStatus.PASS
                        if passed
                        else RevalidationCheckStatus.FAIL
                    ),
                    **extra,
                )
            )
            if not passed and code is not None and code not in codes:
                codes.append(code)

        add(
            "PROPOSAL_EXISTS",
            proposal is not None,
            TransactionFailureCode.PROPOSAL_NOT_FOUND,
        )
        belongs = proposal.session_id == session.id
        add(
            "PROPOSAL_SESSION",
            belongs,
            TransactionFailureCode.PROPOSAL_NOT_FOUND,
        )
        current = session.current_proposal_id == proposal.id
        add(
            "PROPOSAL_CURRENT",
            current,
            TransactionFailureCode.PROPOSAL_NOT_CURRENT,
        )
        expired = proposal.expires_at is not None and moment > proposal.expires_at
        add(
            "PROPOSAL_EXPIRY",
            not expired,
            TransactionFailureCode.PROPOSAL_EXPIRED,
            observed=proposal.expires_at.isoformat() if proposal.expires_at else None,
        )

        if variant is None or offer is None:
            add(
                "PRODUCT",
                False,
                TransactionFailureCode.PRODUCT_INACTIVE,
                message="Variant or offer could not be reloaded.",
            )
            return TransactionRevalidationResult(
                valid=False,
                checks=checks,
                failure_codes=codes,
                current_state_snapshot=snapshot,
                validated_at=moment,
            )

        product_active = bool(variant.product.is_active)
        variant_active = bool(variant.is_active)
        add(
            "PRODUCT",
            product_active,
            TransactionFailureCode.PRODUCT_INACTIVE,
        )
        add(
            "VARIANT",
            variant_active,
            TransactionFailureCode.VARIANT_INACTIVE,
        )

        units = sellable_units(variant)
        snapshot["available_units"] = units
        snapshot["units_available"] = (
            int(variant.inventory.units_available) if variant.inventory else None
        )
        snapshot["units_reserved"] = (
            int(variant.inventory.units_reserved) if variant.inventory else None
        )
        snapshot["base_price_cents"] = variant.base_price_cents
        snapshot["sku"] = variant.sku
        if units is None:
            add(
                "INVENTORY",
                False,
                TransactionFailureCode.OUT_OF_STOCK,
                message="Inventory is missing.",
            )
        elif units <= 0:
            add(
                "INVENTORY",
                False,
                TransactionFailureCode.OUT_OF_STOCK,
                available_units=units,
            )
        elif units < quantity:
            add(
                "INVENTORY",
                False,
                TransactionFailureCode.INSUFFICIENT_STOCK,
                available_units=units,
                observed=quantity,
            )
        else:
            add("INVENTORY", True, available_units=units)

        intent = ShoppingIntent.model_validate(session.working_intent)
        price_failures = buyer_price_reasons(
            intent=intent,
            total_customer_price_cents=offer.total_customer_price_cents,
            product_price_cents=offer.final_product_price_cents,
        )
        if price_constraints(intent):
            failure = price_failures[0] if price_failures else None
            add(
                "BUYER_PRICE",
                failure is None,
                TransactionFailureCode(
                    failure.code.value
                    if failure
                    else TransactionFailureCode.BUYER_MAX_TOTAL_EXCEEDED.value
                ),
                observed=offer.total_customer_price_cents,
                message=failure.message if failure else None,
            )

        catalogue_changed = int(variant.base_price_cents) != int(offer.base_price_cents)
        snapshot["catalogue_price_changed"] = catalogue_changed
        snapshot["locked_base_price_cents"] = offer.base_price_cents
        if catalogue_changed and (not honor or expired):
            add(
                "PRICE",
                False,
                TransactionFailureCode.PRICE_CHANGED,
                observed=variant.base_price_cents,
            )
        else:
            add(
                "PRICE",
                True,
                observed=offer.final_product_price_cents,
                message=(
                    "Locked proposal price honoured until expiry."
                    if catalogue_changed
                    else None
                ),
            )

        if policy is None:
            add(
                "DISCOUNT",
                False,
                TransactionFailureCode.MERCHANT_POLICY_CHANGED,
                message="No active merchant policy.",
            )
            add(
                "MARGIN_POLICY",
                False,
                TransactionFailureCode.MERCHANT_POLICY_CHANGED,
            )
        else:
            cap = money_rate(policy.maximum_discount_rate)
            discount = money_rate(offer.price_adjustment_rate)
            add(
                "DISCOUNT",
                discount <= cap,
                TransactionFailureCode.DISCOUNT_NO_LONGER_ALLOWED,
                observed=str(discount),
            )
            _delivery_check(add, variant, offer)
            _warranty_check(add, variant, offer)
            _bundle_check(add, variant, offer)
            _returns_check(add, variant, offer)
            economics = compute_economics(offer, cogs_cents=int(variant.cogs_cents))
            intent = ShoppingIntent.model_validate(session.working_intent)
            evaluation = evaluate_offer_policy(
                offer,
                economics=economics,
                policy=policy,
                intent=intent,
                sellable_units=units,
                product_active=product_active and variant_active,
            )
            snapshot["contribution_margin_rate"] = str(
                economics.contribution_margin_rate
            )
            snapshot["minimum_margin_rate"] = str(policy.minimum_margin_rate)
            floor = money_rate(policy.minimum_margin_rate)
            margin_ok = economics.contribution_margin_rate >= floor
            add(
                "MARGIN_POLICY",
                margin_ok,
                TransactionFailureCode.MARGIN_POLICY_VIOLATION,
                observed=str(economics.contribution_margin_rate),
            )
            stored = (session.session_metadata or {}).get("policy_snapshot") or {}
            live_margin = str(Decimal(str(policy.minimum_margin_rate)))
            live_discount = str(Decimal(str(policy.maximum_discount_rate)))
            policy_changed = stored and (
                str(stored.get("minimum_margin_rate")) != live_margin
                or str(stored.get("maximum_discount_rate")) != live_discount
            )
            add(
                "MERCHANT_POLICY",
                not policy_changed or (margin_ok and evaluation.policy_safe),
                TransactionFailureCode.MERCHANT_POLICY_CHANGED,
            )
            if (
                policy_changed
                and not margin_ok
                and TransactionFailureCode.MERCHANT_POLICY_CHANGED not in codes
            ):
                codes.append(TransactionFailureCode.MERCHANT_POLICY_CHANGED)

        valid = all(item.status == RevalidationCheckStatus.PASS for item in checks)
        return TransactionRevalidationResult(
            valid=valid,
            checks=checks,
            failure_codes=codes,
            current_state_snapshot=snapshot,
            validated_at=moment,
        )


def _option_available(
    links: list[Any],
    *,
    option_id: UUID | None,
    code: str | None,
    code_attr: str,
) -> bool:
    for link in links:
        option = getattr(link, code_attr, None)
        if option is None:
            continue
        match_id = option_id is not None and option.id == option_id
        match_code = code is not None and getattr(option, "code", None) == code
        if not (match_id or match_code):
            continue
        enabled = bool(getattr(option, "enabled", True))
        return bool(link.available) and enabled
    return False


def _delivery_check(
    add: Any, variant: ProductVariant, offer: OfferCandidate
) -> None:
    ok = _option_available(
        list(variant.delivery_options),
        option_id=offer.delivery_option_id,
        code=offer.delivery_code,
        code_attr="delivery_option",
    )
    add(
        "DELIVERY",
        ok,
        TransactionFailureCode.DELIVERY_NO_LONGER_AVAILABLE,
        observed=offer.delivery_code,
    )


def _warranty_check(
    add: Any, variant: ProductVariant, offer: OfferCandidate
) -> None:
    ok = _option_available(
        list(variant.warranty_options),
        option_id=offer.warranty_option_id,
        code=offer.warranty_code,
        code_attr="warranty_option",
    )
    add(
        "WARRANTY",
        ok,
        TransactionFailureCode.WARRANTY_NO_LONGER_AVAILABLE,
        observed=offer.warranty_code,
    )


def _bundle_check(
    add: Any, variant: ProductVariant, offer: OfferCandidate
) -> None:
    if not offer.bundle_code:
        add("BUNDLE", True)
        return
    ok = _option_available(
        list(variant.bundle_options),
        option_id=offer.bundle_option_id,
        code=offer.bundle_code,
        code_attr="bundle_option",
    )
    add(
        "BUNDLE",
        ok,
        TransactionFailureCode.BUNDLE_NO_LONGER_AVAILABLE,
        observed=offer.bundle_code,
    )


def _returns_check(
    add: Any, variant: ProductVariant, offer: OfferCandidate
) -> None:
    if not offer.return_policy_code:
        add("RETURNS", True)
        return
    ok = _option_available(
        list(variant.return_policies),
        option_id=offer.return_policy_id,
        code=offer.return_policy_code,
        code_attr="return_policy",
    )
    add(
        "RETURNS",
        ok,
        TransactionFailureCode.RETURN_POLICY_CHANGED,
        observed=offer.return_policy_code,
    )

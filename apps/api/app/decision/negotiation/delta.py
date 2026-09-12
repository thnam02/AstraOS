"""Apply a NegotiationDelta onto the original ShoppingIntent.

Unrelated original hard constraints stay mandatory unless the buyer
explicitly relaxes them. The interpreter never writes commercial terms
onto an offer.
"""

from __future__ import annotations

from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    HardConstraint,
    ShoppingIntent,
)
from app.decision.negotiation.models import (
    CounterConstraints,
    InterpretedBuyerTurn,
    NegotiationDelta,
)

_PRODUCT_FIELDS = {
    ConstraintField.CATEGORY,
    ConstraintField.BRAND,
    ConstraintField.ANC,
    ConstraintField.BATTERY_HOURS,
    ConstraintField.WEIGHT_G,
    ConstraintField.FOLDABLE,
    ConstraintField.WIRELESS,
    ConstraintField.MICROPHONE,
    ConstraintField.IN_STOCK,
}


def delta_from_turn(turn: InterpretedBuyerTurn) -> NegotiationDelta:
    asked = turn.constraints
    rematch = bool(
        asked.foldable_required is not None
        or asked.relax_same_day
        or asked.requested_delivery_days is not None
    )
    return NegotiationDelta(
        price_constraint_change=asked.max_total_price_cents,
        delivery_constraint_change=asked.requested_delivery_days,
        relax_same_day=asked.relax_same_day,
        warranty_constraint_change=asked.requested_warranty_months,
        bundle_change=asked.requested_bundle,
        returns_change=asked.requested_return_window_days,
        product_substitution_allowed=asked.alternative_product_allowed,
        foldable_required=asked.foldable_required,
        preference_adjustments=list(asked.preference_changes),
        rematch_required=rematch,
        reconstruct_required=True,
    )


def apply_working_intent(
    original: ShoppingIntent, deltas: list[NegotiationDelta]
) -> ShoppingIntent:
    """Working intent used for rematch/reconstruct.

    Tightened price is NOT applied here. Price counters filter constructed
    offers so a $329 list-price SKU can still yield a $319 counteroffer.
    """
    intent = original.model_copy(deep=True)
    for delta in deltas:
        if delta.relax_same_day:
            intent.hard_constraints = [
                item
                for item in intent.hard_constraints
                if item.field
                not in {
                    ConstraintField.SAME_DAY_DELIVERY,
                    ConstraintField.DELIVERY_DAYS,
                }
            ]
        if delta.delivery_constraint_change is not None and not delta.relax_same_day:
            intent.hard_constraints = [
                item
                for item in intent.hard_constraints
                if item.field
                not in {
                    ConstraintField.SAME_DAY_DELIVERY,
                    ConstraintField.DELIVERY_DAYS,
                }
            ]
            days = delta.delivery_constraint_change
            if days <= 0:
                intent.hard_constraints.append(
                    HardConstraint(
                        id="nego-same-day",
                        field=ConstraintField.SAME_DAY_DELIVERY,
                        operator=ConstraintOperator.EQ,
                        value=True,
                        source_phrase="negotiation delivery",
                    )
                )
            else:
                intent.hard_constraints.append(
                    HardConstraint(
                        id="nego-delivery-days",
                        field=ConstraintField.DELIVERY_DAYS,
                        operator=ConstraintOperator.LTE,
                        value=days,
                        unit="DAYS",
                        source_phrase="negotiation delivery",
                        normalized_value=days,
                    )
                )
        if delta.foldable_required is True:
            intent.hard_constraints = [
                item
                for item in intent.hard_constraints
                if item.field != ConstraintField.FOLDABLE
            ]
            intent.hard_constraints.append(
                HardConstraint(
                    id="nego-foldable",
                    field=ConstraintField.FOLDABLE,
                    operator=ConstraintOperator.EQ,
                    value=True,
                    source_phrase="negotiation foldable",
                    normalized_value=True,
                )
            )
    return intent


def merged_constraints(deltas: list[NegotiationDelta]) -> CounterConstraints:
    merged = CounterConstraints()
    for delta in deltas:
        if delta.price_constraint_change is not None:
            merged.max_total_price_cents = delta.price_constraint_change
        if delta.delivery_constraint_change is not None:
            merged.requested_delivery_days = delta.delivery_constraint_change
        if delta.relax_same_day:
            merged.relax_same_day = True
            merged.requested_delivery_days = (
                delta.delivery_constraint_change
                if delta.delivery_constraint_change is not None
                else 2
            )
        if delta.warranty_constraint_change is not None:
            merged.requested_warranty_months = delta.warranty_constraint_change
        if delta.bundle_change is not None:
            merged.requested_bundle = delta.bundle_change
        if delta.returns_change is not None:
            merged.requested_return_window_days = delta.returns_change
        if delta.foldable_required is not None:
            merged.foldable_required = delta.foldable_required
        merged.alternative_product_allowed = delta.product_substitution_allowed
        merged.preference_changes.extend(delta.preference_adjustments)
    return merged


def product_fields_unchanged(original: ShoppingIntent, working: ShoppingIntent) -> bool:
    def key(intent: ShoppingIntent) -> list[tuple[str, str, str]]:
        rows = [
            (item.field.value, item.operator.value, str(item.value))
            for item in intent.hard_constraints
            if item.field in _PRODUCT_FIELDS
        ]
        return sorted(rows)

    return key(original) == key(working)

"""Deterministic eligibility. LLMs must not call this module."""

from __future__ import annotations

from app.decision.eligibility.delivery_evaluator import evaluate_delivery
from app.decision.eligibility.explanation import describe_evaluation
from app.decision.eligibility.models import (
    ConstraintEvaluation,
    ConstraintStatus,
    EvidenceFreshness,
    ProductEligibilityResult,
)
from app.decision.eligibility.operators import OperatorError, apply_operator
from app.decision.eligibility.product_fields import FieldResolution, resolve_field
from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.intent.models import HardConstraint, ShoppingIntent
from app.decision.intent.normalizer import expected_value


class EligibilityEvaluator:
    """Evaluate every mandatory constraint on one variant."""

    def evaluate_variant(
        self,
        variant: VariantSnapshot,
        shopping_intent: ShoppingIntent,
    ) -> ProductEligibilityResult:
        evaluations = [
            self._evaluate_constraint(variant, constraint)
            for constraint in shopping_intent.hard_constraints
        ]
        evaluations.extend(self._unsupported_mandatory(shopping_intent))
        satisfied = sum(
            1 for item in evaluations if item.status == ConstraintStatus.SATISFIED
        )
        violated = sum(
            1 for item in evaluations if item.status == ConstraintStatus.VIOLATED
        )
        unknown = sum(
            1 for item in evaluations if item.status == ConstraintStatus.UNKNOWN
        )
        eligible = violated == 0 and unknown == 0 and bool(evaluations)
        if not shopping_intent.hard_constraints and not any(
            item.appears_mandatory for item in shopping_intent.ambiguities
        ):
            eligible = False
            unknown = max(unknown, 1)
            evaluations.append(
                ConstraintEvaluation(
                    constraint_id="empty_intent",
                    field="intent",
                    operator="EQ",
                    expected_value=None,
                    observed_value=None,
                    status=ConstraintStatus.UNKNOWN,
                    reason="NO_MANDATORY_CONSTRAINTS",
                )
            )
        exclusions = [
            describe_evaluation(item)
            for item in evaluations
            if item.status != ConstraintStatus.SATISFIED
        ]
        return ProductEligibilityResult(
            product_id=variant.product_id,
            variant_id=variant.variant_id,
            sku=variant.sku,
            product_name=variant.product_name,
            brand=variant.brand,
            variant_name=variant.variant_name,
            base_price_cents=variant.base_price_cents,
            evaluations=evaluations,
            eligible=eligible,
            violated_count=violated,
            unknown_count=unknown,
            satisfied_count=satisfied,
            exclusion_reasons=exclusions,
        )

    def _evaluate_constraint(
        self, variant: VariantSnapshot, constraint: HardConstraint
    ) -> ConstraintEvaluation:
        expected = expected_value(constraint)
        resolved = resolve_field(constraint.field, variant)
        if resolved.kind == "delivery":
            status, observed, reason, detail = evaluate_delivery(
                field=constraint.field,
                operator=constraint.operator,
                expected=expected,
                snapshot=variant,
            )
            return ConstraintEvaluation(
                constraint_id=constraint.id,
                field=constraint.field.value,
                operator=constraint.operator.value,
                expected_value=expected,
                observed_value=observed,
                status=status,
                reason=reason,
                source_name="Fulfilment capability file",
                source_reference="variant_delivery_options",
                evidence_freshness=EvidenceFreshness.OPERATIONAL,
                verification_status="MERCHANT_DECLARED",
                supporting_detail=detail,
            )

        if not resolved.present:
            return self._unknown(constraint, expected, resolved)

        if _stale_blocks(resolved):
            return self._unknown(
                constraint,
                expected,
                resolved,
                reason="STALE_EVIDENCE",
                freshness=EvidenceFreshness.STALE,
            )

        try:
            matched = apply_operator(constraint.operator, resolved.value, expected)
        except OperatorError:
            return self._unknown(
                constraint,
                expected,
                resolved,
                reason="INCOMPARABLE_VALUES",
            )
        status = ConstraintStatus.SATISFIED if matched else ConstraintStatus.VIOLATED
        evidence = resolved.evidence
        freshness = EvidenceFreshness.MISSING
        if resolved.kind == "inventory":
            freshness = EvidenceFreshness.OPERATIONAL
        elif evidence is not None:
            freshness = (
                EvidenceFreshness.STALE
                if evidence.is_stale
                else EvidenceFreshness.FRESH
            )
        return ConstraintEvaluation(
            constraint_id=constraint.id,
            field=constraint.field.value,
            operator=constraint.operator.value,
            expected_value=expected,
            observed_value=resolved.value,
            status=status,
            reason=(
                "CONSTRAINT_SATISFIED"
                if status == ConstraintStatus.SATISFIED
                else "CONSTRAINT_VIOLATED"
            ),
            source_name=resolved.source_name,
            source_reference=resolved.source_reference,
            evidence_id=evidence.id if evidence else None,
            evidence_freshness=freshness,
            verification_status=(
                evidence.verification_status
                if evidence
                else ("MERCHANT_DECLARED" if resolved.kind == "inventory" else None)
            ),
            observed_at=evidence.observed_at if evidence else None,
            expires_at=evidence.expires_at if evidence else None,
        )

    def _unknown(
        self,
        constraint: HardConstraint,
        expected: object,
        resolved: FieldResolution,
        *,
        reason: str | None = None,
        freshness: EvidenceFreshness | None = None,
    ) -> ConstraintEvaluation:
        evidence = resolved.evidence
        return ConstraintEvaluation(
            constraint_id=constraint.id,
            field=constraint.field.value,
            operator=constraint.operator.value,
            expected_value=expected,
            observed_value=resolved.value,
            status=ConstraintStatus.UNKNOWN,
            reason=reason or resolved.missing_reason or "MISSING_ATTRIBUTE",
            source_name=resolved.source_name,
            source_reference=resolved.source_reference,
            evidence_id=evidence.id if evidence else None,
            evidence_freshness=freshness
            or (
                EvidenceFreshness.STALE
                if evidence is not None and evidence.is_stale
                else EvidenceFreshness.MISSING
            ),
            verification_status=evidence.verification_status if evidence else None,
            observed_at=evidence.observed_at if evidence else None,
            expires_at=evidence.expires_at if evidence else None,
        )

    def _unsupported_mandatory(
        self, shopping_intent: ShoppingIntent
    ) -> list[ConstraintEvaluation]:
        evaluations: list[ConstraintEvaluation] = []
        for index, ambiguity in enumerate(shopping_intent.ambiguities, start=1):
            if not ambiguity.appears_mandatory:
                continue
            evaluations.append(
                ConstraintEvaluation(
                    constraint_id=f"unsupported_{index}",
                    field="unsupported",
                    operator="EQ",
                    expected_value=ambiguity.source_phrase,
                    observed_value=None,
                    status=ConstraintStatus.UNKNOWN,
                    reason="UNSUPPORTED_ATTRIBUTE",
                    source_reference=ambiguity.source_phrase,
                    evidence_freshness=EvidenceFreshness.MISSING,
                )
            )
        return evaluations


def _stale_blocks(resolved: FieldResolution) -> bool:
    """Stale evidence blocks attribute-backed facts, not live stock rows."""
    if resolved.kind != "scalar":
        return False
    evidence = resolved.evidence
    if evidence is None:
        return False
    return evidence.is_stale

"""Deterministic eligibility: SATISFIED / VIOLATED / UNKNOWN."""

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.models import ConstraintStatus
from app.decision.eligibility.snapshot import DeliverySnapshot
from app.decision.intent.models import (
    ConstraintField,
    ConstraintOperator,
    IntentAmbiguity,
)
from tests.qualification_fixtures import (
    CASE1_AURORA,
    CASE1_INTENT,
    CASE1_NIMBUS,
    CASE1_VANTA,
    CASE2_INTENT,
    CASE3_INTENT,
    CASE4_INTENT,
    CASE5_INTENT,
    CASE5_NO_SAME_DAY,
    CASE6_MISSING_BATTERY,
    CASE7_INTENT,
    CASE7_MISSING_INV,
    CASE7_OOS,
    CASE7_RESERVED,
    CASE8_AT_BOUNDARY,
    CASE8_LT,
    CASE8_LTE,
    CASE9_INTENT,
    CASE10_INTENT,
    constraint,
    evidence,
    intent_with,
    snapshot,
)

evaluator = EligibilityEvaluator()


def _status(result, field: str) -> ConstraintStatus:
    return next(item.status for item in result.evaluations if item.field == field)


def test_case1_aurora_eligible() -> None:
    result = evaluator.evaluate_variant(CASE1_AURORA, CASE1_INTENT)
    assert _status(result, "anc") == ConstraintStatus.SATISFIED
    assert _status(result, "price") == ConstraintStatus.SATISFIED
    assert _status(result, "delivery_days") == ConstraintStatus.SATISFIED
    assert result.eligible is True
    assert result.outcome == "eligible"


def test_case1_nimbus_unknown_delivery_not_eligible() -> None:
    missing = snapshot(
        name="Nimbus Travel Pro",
        deliveries=[],
    )
    result = evaluator.evaluate_variant(missing, CASE1_INTENT)
    assert _status(result, "delivery_days") == ConstraintStatus.UNKNOWN
    assert result.eligible is False
    assert result.outcome == "uncertain"


def test_case1_nimbus_no_same_day_rejected() -> None:
    result = evaluator.evaluate_variant(CASE1_NIMBUS, CASE1_INTENT)
    assert _status(result, "anc") == ConstraintStatus.SATISFIED
    assert _status(result, "price") == ConstraintStatus.SATISFIED
    assert _status(result, "delivery_days") == ConstraintStatus.VIOLATED
    assert result.eligible is False
    assert result.outcome == "rejected"


def test_case1_vanta_price_violated() -> None:
    result = evaluator.evaluate_variant(CASE1_VANTA, CASE1_INTENT)
    assert _status(result, "price") == ConstraintStatus.VIOLATED
    assert result.eligible is False
    assert result.outcome == "rejected"


def test_case2_battery_threshold() -> None:
    ok = snapshot(attributes={"battery_hours": 42})
    short = snapshot(attributes={"battery_hours": 20})
    assert evaluator.evaluate_variant(ok, CASE2_INTENT).eligible is True
    assert evaluator.evaluate_variant(short, CASE2_INTENT).eligible is False


def test_case3_price_and_wireless() -> None:
    ok = snapshot(price=17900, attributes={"wireless": True})
    wired = snapshot(price=17900, attributes={"wireless": False})
    assert evaluator.evaluate_variant(ok, CASE3_INTENT).eligible is True
    assert evaluator.evaluate_variant(wired, CASE3_INTENT).outcome == "rejected"


def test_case4_foldable_required() -> None:
    yes = snapshot(attributes={"foldable": True})
    no = snapshot(attributes={"foldable": False})
    assert evaluator.evaluate_variant(yes, CASE4_INTENT).eligible is True
    assert evaluator.evaluate_variant(no, CASE4_INTENT).eligible is False


def test_case5_same_day_unavailable() -> None:
    result = evaluator.evaluate_variant(CASE5_NO_SAME_DAY, CASE5_INTENT)
    assert _status(result, "delivery_days") == ConstraintStatus.VIOLATED
    assert result.eligible is False


def test_case5_same_day_available() -> None:
    result = evaluator.evaluate_variant(CASE1_AURORA, CASE5_INTENT)
    assert result.eligible is True
    delivery = next(
        item for item in result.evaluations if item.field == "delivery_days"
    )
    assert delivery.supporting_detail == "Same Day Delivery"


def test_case6_missing_battery_unknown() -> None:
    result = evaluator.evaluate_variant(CASE6_MISSING_BATTERY, CASE2_INTENT)
    assert _status(result, "battery_hours") == ConstraintStatus.UNKNOWN
    assert result.eligible is False
    assert result.outcome == "uncertain"
    assert result.evaluations[0].reason == "MISSING_ATTRIBUTE"


def test_null_attribute_is_unknown() -> None:
    variant = snapshot(attributes={"battery_hours": None})
    result = evaluator.evaluate_variant(variant, CASE2_INTENT)
    assert result.evaluations[0].status == ConstraintStatus.UNKNOWN


def test_case7_in_stock_and_reserved() -> None:
    assert evaluator.evaluate_variant(CASE1_AURORA, CASE7_INTENT).eligible is True
    oos = evaluator.evaluate_variant(CASE7_OOS, CASE7_INTENT)
    reserved = evaluator.evaluate_variant(CASE7_RESERVED, CASE7_INTENT)
    missing = evaluator.evaluate_variant(CASE7_MISSING_INV, CASE7_INTENT)
    assert oos.outcome == "rejected"
    assert reserved.outcome == "rejected"
    assert missing.outcome == "uncertain"
    assert missing.evaluations[0].reason == "MISSING_INVENTORY"


def test_case8_price_boundary() -> None:
    lt = evaluator.evaluate_variant(CASE8_AT_BOUNDARY, CASE8_LT)
    lte = evaluator.evaluate_variant(CASE8_AT_BOUNDARY, CASE8_LTE)
    assert lt.eligible is False
    assert lte.eligible is True


def test_case9_unsupported_blocks_eligibility() -> None:
    result = evaluator.evaluate_variant(CASE1_AURORA, CASE9_INTENT)
    assert result.eligible is False
    assert any(item.reason == "UNSUPPORTED_ATTRIBUTE" for item in result.evaluations)
    assert result.unknown_count >= 1


def test_case10_multiple_and_conditions() -> None:
    result = evaluator.evaluate_variant(CASE1_AURORA, CASE10_INTENT)
    assert result.eligible is True
    assert result.satisfied_count == 4


def test_soft_preferences_do_not_affect_eligibility() -> None:
    result = evaluator.evaluate_variant(CASE1_AURORA, CASE1_INTENT)
    assert all(item.field != "comfort" for item in result.evaluations)


def test_one_unknown_blocks_eligibility() -> None:
    intent = intent_with(
        constraint(ConstraintField.ANC, ConstraintOperator.EQ, True),
        constraint(ConstraintField.BATTERY_HOURS, ConstraintOperator.GTE, 40, cid="b"),
    )
    variant = snapshot(attributes={"anc": True})
    result = evaluator.evaluate_variant(variant, intent)
    assert result.satisfied_count == 1
    assert result.unknown_count == 1
    assert result.eligible is False


def test_valid_evidence_attached() -> None:
    variant = snapshot(
        evidence=[evidence("anc", True)],
    )
    intent = intent_with(constraint(ConstraintField.ANC, ConstraintOperator.EQ, True))
    result = evaluator.evaluate_variant(variant, intent)
    ev = result.evaluations[0]
    assert ev.status == ConstraintStatus.SATISFIED
    assert ev.source_name == "Manufacturer specifications"
    assert ev.verification_status == "VERIFIED"
    assert ev.evidence_id is not None
    assert ev.evidence_freshness is not None
    assert ev.evidence_freshness.value == "FRESH"


def test_stale_evidence_is_unknown() -> None:
    variant = snapshot(
        attributes={"anc": True},
        evidence=[evidence("anc", True, stale=True)],
    )
    intent = intent_with(constraint(ConstraintField.ANC, ConstraintOperator.EQ, True))
    result = evaluator.evaluate_variant(variant, intent)
    assert result.evaluations[0].status == ConstraintStatus.UNKNOWN
    assert result.evaluations[0].reason == "STALE_EVIDENCE"
    assert result.eligible is False


def test_missing_evidence_still_uses_attribute() -> None:
    variant = snapshot(attributes={"anc": True}, evidence=[])
    intent = intent_with(constraint(ConstraintField.ANC, ConstraintOperator.EQ, True))
    result = evaluator.evaluate_variant(variant, intent)
    assert result.eligible is True
    assert result.evaluations[0].evidence_freshness is not None
    assert result.evaluations[0].evidence_freshness.value == "MISSING"


def test_delivery_data_missing_unknown() -> None:
    variant = snapshot(deliveries=[])
    result = evaluator.evaluate_variant(variant, CASE5_INTENT)
    assert result.evaluations[0].status == ConstraintStatus.UNKNOWN
    assert result.evaluations[0].reason == "MISSING_DELIVERY_DATA"


def test_disabled_only_delivery_is_unknown() -> None:
    variant = snapshot(
        deliveries=[DeliverySnapshot("SAME_DAY", "Same Day Delivery", 0, False, True)]
    )
    result = evaluator.evaluate_variant(variant, CASE5_INTENT)
    assert result.evaluations[0].status == ConstraintStatus.UNKNOWN


def test_absence_of_leather_is_not_satisfied() -> None:
    """Absence of evidence is not evidence of absence."""
    variant = snapshot(attributes={"anc": True, "wireless": True})
    intent = intent_with(
        ambiguities=[
            IntentAmbiguity(
                source_phrase="No animal leather",
                reason="unsupported_attribute",
                appears_mandatory=True,
            )
        ]
    )
    result = evaluator.evaluate_variant(variant, intent)
    assert result.eligible is False
    assert any(item.reason == "UNSUPPORTED_ATTRIBUTE" for item in result.evaluations)
    assert not any(
        item.status == ConstraintStatus.SATISFIED
        and "leather" in str(item.expected_value).lower()
        for item in result.evaluations
    )

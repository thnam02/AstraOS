"""Central outcome mapping tests."""

from app.decision.eligibility.snapshot import DeliverySnapshot
from app.decision.intent.taxonomy import ContextLabel, OutcomeLabel
from app.decision.retrieval.mapping import (
    OUTCOME_SUPPORT,
    features_for,
    observe_attribute,
    support_hits,
    weighted_score,
)
from tests.qualification_fixtures import snapshot


def test_long_haul_uses_travel_features() -> None:
    names = {
        item.attribute
        for item in features_for("context", ContextLabel.LONG_HAUL_TRAVEL.value)
    }
    assert {"anc", "battery_hours", "weight_g", "foldable", "travel_score"} <= names


def test_low_fatigue_uses_comfort_and_weight() -> None:
    names = {
        item.attribute
        for item in features_for("outcome", OutcomeLabel.LOW_FATIGUE.value)
    }
    assert names == {"comfort_score", "weight_g"}


def test_battery_endurance_mapping() -> None:
    assert OUTCOME_SUPPORT[OutcomeLabel.LONG_BATTERY_ENDURANCE.value][0].attribute == (
        "battery_hours"
    )


def test_travel_convenience_uses_fulfilment() -> None:
    variant = snapshot()
    hits = support_hits(
        variant, features_for("outcome", OutcomeLabel.TRAVEL_CONVENIENCE.value)
    )
    attrs = {hit.attribute for hit in hits}
    assert "same_day" in attrs
    assert weighted_score(hits) is not None


def test_missing_feature_does_not_score_as_zero() -> None:
    variant = snapshot(attributes={"anc": True}, deliveries=[])
    assert observe_attribute(variant, "same_day") is None
    hits = support_hits(
        variant, features_for("outcome", OutcomeLabel.TRAVEL_CONVENIENCE.value)
    )
    assert "same_day" not in {hit.attribute for hit in hits}


def test_no_same_day_is_observed_false() -> None:
    variant = snapshot(
        deliveries=[DeliverySnapshot("STANDARD", "Standard", 2, True, True)]
    )
    assert observe_attribute(variant, "same_day") is False

"""Training features must not include the label-generating utility total."""

from app.decision.learning.features import FEATURE_NAMES
from app.decision.learning.leakage import leakage_violations


def test_primary_schema_has_no_utility_or_outcome() -> None:
    assert leakage_violations(FEATURE_NAMES) == []
    blob = " ".join(FEATURE_NAMES).lower()
    assert "utility" not in blob
    assert "selected" not in blob
    assert "accepted" not in blob
    assert "strategy_name" not in FEATURE_NAMES


def test_extract_features_excludes_utility_total() -> None:
    from app.decision.learning import FORBIDDEN_FEATURE_NAMES
    from app.decision.learning.features import FEATURE_NAMES

    overlap = set(FEATURE_NAMES) & FORBIDDEN_FEATURE_NAMES
    assert not overlap


def test_leakage_detector_flags_utility() -> None:
    assert "buyer_utility" in leakage_violations(["buyer_utility", "product_fit"])
    assert leakage_violations(["product_fit", "delivery_days"]) == []

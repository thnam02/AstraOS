"""Refuse features that would leak the synthetic label-generating process."""

from collections.abc import Iterable
from typing import Any

from app.decision.learning import FORBIDDEN_FEATURE_NAMES
from app.decision.learning.features import FEATURE_NAMES


def leakage_violations(feature_names: Iterable[str]) -> list[str]:
    names = {item.lower() for item in feature_names}
    hits = sorted(names & {item.lower() for item in FORBIDDEN_FEATURE_NAMES})
    extra = []
    for name in names:
        if "utility" in name and "importance" not in name:
            extra.append(name)
        if name in {"y", "label", "target", "selected", "accepted"}:
            extra.append(name)
    return sorted(set(hits + extra))


def assert_no_leakage(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    keys = set(rows[0].keys())
    violations = leakage_violations(keys)
    if violations:
        raise ValueError(f"Target leakage in features: {violations}")
    unknown = keys - set(FEATURE_NAMES) - {"feature_schema_version"}
    # Dataset rows may include metadata keys; those are stripped before fit.
    _ = unknown


def schema_is_primary(feature_names: Iterable[str]) -> bool:
    return leakage_violations(feature_names) == []

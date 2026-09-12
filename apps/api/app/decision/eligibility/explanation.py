"""Human-readable exclusion reasons for qualification traces."""

from typing import Any

from app.decision.eligibility.models import ConstraintEvaluation, ConstraintStatus


def describe_evaluation(evaluation: ConstraintEvaluation) -> str:
    if evaluation.status == ConstraintStatus.SATISFIED:
        return f"{evaluation.field} SATISFIED"
    if evaluation.status == ConstraintStatus.VIOLATED:
        return (
            f"{evaluation.field} VIOLATED: expected {evaluation.operator} "
            f"{_display(evaluation.expected_value)}, observed "
            f"{_display(evaluation.observed_value)}"
        )
    return f"{evaluation.field} UNKNOWN: {evaluation.reason}"


def _display(value: Any) -> str:
    if value is None:
        return "missing"
    return str(value)

"""Deterministic product eligibility. No LLM calls, no ranking."""

from app.decision.eligibility.evaluator import EligibilityEvaluator
from app.decision.eligibility.models import (
    ConstraintEvaluation,
    ConstraintStatus,
    ProductEligibilityResult,
)

__all__ = [
    "ConstraintEvaluation",
    "ConstraintStatus",
    "EligibilityEvaluator",
    "ProductEligibilityResult",
]

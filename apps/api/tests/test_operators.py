"""Safe operator engine tests. No eval()."""

import pytest

from app.decision.eligibility.operators import OperatorError, apply_operator
from app.decision.intent.models import ConstraintOperator


def test_eq_numbers_and_strings() -> None:
    assert apply_operator(ConstraintOperator.EQ, 10, 10) is True
    assert apply_operator(ConstraintOperator.EQ, "Aurora", "aurora") is True
    assert apply_operator(ConstraintOperator.NE, 10, 11) is True


def test_eq_booleans() -> None:
    assert apply_operator(ConstraintOperator.EQ, True, True) is True
    assert apply_operator(ConstraintOperator.EQ, False, True) is False
    assert apply_operator(ConstraintOperator.EQ, "true", True) is True


def test_lt_lte_boundaries() -> None:
    assert apply_operator(ConstraintOperator.LT, 34999, 35000) is True
    assert apply_operator(ConstraintOperator.LT, 35000, 35000) is False
    assert apply_operator(ConstraintOperator.LTE, 35000, 35000) is True
    assert apply_operator(ConstraintOperator.LTE, 35001, 35000) is False


def test_gt_gte_boundaries() -> None:
    assert apply_operator(ConstraintOperator.GT, 31, 30) is True
    assert apply_operator(ConstraintOperator.GT, 30, 30) is False
    assert apply_operator(ConstraintOperator.GTE, 30, 30) is True
    assert apply_operator(ConstraintOperator.GTE, 29, 30) is False


def test_in_and_not_in() -> None:
    assert apply_operator(ConstraintOperator.IN, "nimbus", ["Aurora", "Nimbus"]) is True
    assert (
        apply_operator(ConstraintOperator.NOT_IN, "Vanta", ["Aurora", "Nimbus"]) is True
    )


def test_boolean_is_not_numeric() -> None:
    with pytest.raises(OperatorError):
        apply_operator(ConstraintOperator.LT, True, 1)


def test_incomparable_raises() -> None:
    with pytest.raises(OperatorError):
        apply_operator(ConstraintOperator.LT, "anc", 30)

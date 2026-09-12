"""Explicit typed operators. Never eval() or execute generated code."""

from collections.abc import Callable
from typing import Any

from app.decision.intent.models import ConstraintOperator


class OperatorError(ValueError):
    """Raised when an operator cannot compare the given types."""


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    raise OperatorError(f"Cannot interpret {value!r} as a boolean.")


def _as_number(value: Any) -> float:
    if isinstance(value, bool):
        raise OperatorError("Boolean is not a numeric comparison operand.")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value.replace(",", ""))
    raise OperatorError(f"Cannot interpret {value!r} as a number.")


def compare_eq(observed: Any, expected: Any) -> bool:
    if isinstance(expected, bool) or isinstance(observed, bool):
        return _as_bool(observed) is _as_bool(expected)
    if isinstance(expected, int | float) or isinstance(observed, int | float):
        return _as_number(observed) == _as_number(expected)
    return str(observed).casefold() == str(expected).casefold()


def compare_ne(observed: Any, expected: Any) -> bool:
    return not compare_eq(observed, expected)


def compare_lt(observed: Any, expected: Any) -> bool:
    return _as_number(observed) < _as_number(expected)


def compare_lte(observed: Any, expected: Any) -> bool:
    return _as_number(observed) <= _as_number(expected)


def compare_gt(observed: Any, expected: Any) -> bool:
    return _as_number(observed) > _as_number(expected)


def compare_gte(observed: Any, expected: Any) -> bool:
    return _as_number(observed) >= _as_number(expected)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list | tuple | set):
        return list(value)
    return [value]


def compare_in(observed: Any, expected: Any) -> bool:
    return any(compare_eq(observed, item) for item in _as_list(expected))


def compare_not_in(observed: Any, expected: Any) -> bool:
    return not compare_in(observed, expected)


OPERATORS: dict[ConstraintOperator, Callable[[Any, Any], bool]] = {
    ConstraintOperator.EQ: compare_eq,
    ConstraintOperator.NE: compare_ne,
    ConstraintOperator.LT: compare_lt,
    ConstraintOperator.LTE: compare_lte,
    ConstraintOperator.GT: compare_gt,
    ConstraintOperator.GTE: compare_gte,
    ConstraintOperator.IN: compare_in,
    ConstraintOperator.NOT_IN: compare_not_in,
}


def apply_operator(operator: ConstraintOperator, observed: Any, expected: Any) -> bool:
    """Apply a allow-listed operator. Missing values must be handled by caller."""
    try:
        return OPERATORS[operator](observed, expected)
    except (TypeError, ValueError) as exc:
        raise OperatorError(str(exc)) from exc

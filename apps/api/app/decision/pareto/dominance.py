"""N-objective Pareto dominance with a float epsilon. Money stays exact."""

from collections.abc import Sequence

import numpy as np

DEFAULT_EPSILON = 1e-9


def dominates(
    left: Sequence[float],
    right: Sequence[float],
    *,
    maximize: Sequence[bool],
    epsilon: float = DEFAULT_EPSILON,
) -> bool:
    """True when left is at least as good on every objective and better on one."""
    if len(left) != len(right) or len(left) != len(maximize):
        raise ValueError("Objective vectors must share length.")
    at_least = True
    strictly = False
    for a, b, grow in zip(left, right, maximize, strict=True):
        if grow:
            if a + epsilon < b:
                at_least = False
                break
            if a > b + epsilon:
                strictly = True
        else:
            if a - epsilon > b:
                at_least = False
                break
            if a < b - epsilon:
                strictly = True
    return at_least and strictly


def pareto_mask(
    values: np.ndarray,
    *,
    maximize: Sequence[bool],
    epsilon: float = DEFAULT_EPSILON,
) -> np.ndarray:
    """Return a boolean mask of non-dominated rows.

    `values` has shape (n, k). Column i is maximized if maximize[i] is True.
    Integer money columns should be passed as-is; epsilon applies to all
    columns but is negligible relative to whole cents.
    """
    n, k = values.shape
    if n == 0:
        return np.zeros(0, dtype=bool)
    signs = np.array([1.0 if flag else -1.0 for flag in maximize], dtype=np.float64)
    oriented = values.astype(np.float64) * signs
    efficient = np.ones(n, dtype=bool)
    for i in range(n):
        if not efficient[i]:
            continue
        delta = oriented - oriented[i]
        at_least = np.all(delta >= -epsilon, axis=1)
        strictly = np.any(delta > epsilon, axis=1)
        at_least[i] = False
        if np.any(at_least & strictly):
            efficient[i] = False
    return efficient


def first_dominator(
    index: int,
    values: np.ndarray,
    *,
    maximize: Sequence[bool],
    epsilon: float = DEFAULT_EPSILON,
) -> int | None:
    """Return the first row index that dominates `index`, if any."""
    n = values.shape[0]
    for j in range(n):
        if j == index:
            continue
        if dominates(values[j], values[index], maximize=maximize, epsilon=epsilon):
            return j
    return None

"""Merchant selection among Pareto-efficient offers only."""

from app.decision.optimisation.models import (
    DEFAULT_ALPHA,
    SELECTION_RULE,
    ScoredOffer,
    SelectionScore,
)


def _minmax(values: list[float]) -> tuple[float, float]:
    return min(values), max(values)


def normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 1.0
    return (value - low) / (high - low)


def select_offer(
    frontier: list[ScoredOffer],
    *,
    alpha: float = DEFAULT_ALPHA,
) -> tuple[ScoredOffer | None, SelectionScore | None]:
    """Weighted sum of normalized utility and contribution. Frontier only."""
    if not frontier:
        return None, None
    utilities = [item.utility.score for item in frontier]
    contributions = [
        float(item.economics.contribution_margin_cents) for item in frontier
    ]
    u_lo, u_hi = _minmax(utilities)
    c_lo, c_hi = _minmax(contributions)
    scored: list[tuple[ScoredOffer, SelectionScore]] = []
    for item in frontier:
        nu = normalize(item.utility.score, u_lo, u_hi)
        nc = normalize(float(item.economics.contribution_margin_cents), c_lo, c_hi)
        score = alpha * nu + (1.0 - alpha) * nc
        scored.append(
            (
                item,
                SelectionScore(
                    offer_id=item.offer_id,
                    normalized_utility=round(nu, 6),
                    normalized_contribution=round(nc, 6),
                    score=round(score, 6),
                    alpha=alpha,
                    rule=SELECTION_RULE,
                ),
            )
        )
    scored.sort(
        key=lambda pair: (
            -pair[1].score,
            -pair[0].economics.contribution_margin_cents,
            -pair[0].utility.score,
            pair[0].economics.incremental_intervention_cost_cents,
            pair[0].sku,
        )
    )
    winner, meta = scored[0]
    return winner, meta

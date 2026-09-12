"""Merchant selection among Pareto-efficient offers only."""

from typing import Any, cast
from uuid import UUID

from app.decision.optimisation.models import (
    DEFAULT_ALPHA,
    SELECTION_RULE,
    ObjectiveComparison,
    ScoredOffer,
    SelectionScore,
)
from app.decision.optimisation.objective import (
    MerchantObjectiveConfig,
    ObjectiveMode,
    default_objective,
    preset,
)


def _minmax(values: list[float]) -> tuple[float, float]:
    return min(values), max(values)


def normalize(value: float, low: float, high: float) -> float:
    if high <= low:
        return 1.0
    return (value - low) / (high - low)


def _buyer_score(
    item: ScoredOffer, buyer_objective: dict[UUID, float] | None
) -> float:
    if buyer_objective is None:
        return item.utility.score
    return buyer_objective.get(item.offer_id, item.utility.score)


def select_offer(
    frontier: list[ScoredOffer],
    *,
    alpha: float | None = None,
    objective: MerchantObjectiveConfig | None = None,
    buyer_objective: dict[UUID, float] | None = None,
) -> tuple[ScoredOffer | None, SelectionScore | None]:
    """Weighted sum of normalized utility and contribution. Frontier only.

    score = w_buyer * norm(utility) + w_merchant * norm(contribution)

    Tie-break (stable, not row order):
    1. higher weighted score
    2. higher contribution
    3. higher buyer utility
    4. lower intervention cost
    5. SKU
    6. offer ID
    """
    chosen = objective or default_objective()
    weight = chosen.buyer_weight if objective is not None else (
        DEFAULT_ALPHA if alpha is None else alpha
    )
    if not frontier:
        return None, None
    utilities = [_buyer_score(item, buyer_objective) for item in frontier]
    contributions = [
        float(item.economics.contribution_margin_cents) for item in frontier
    ]
    u_lo, u_hi = _minmax(utilities)
    c_lo, c_hi = _minmax(contributions)
    scored: list[tuple[ScoredOffer, SelectionScore]] = []
    for item in frontier:
        nu = normalize(_buyer_score(item, buyer_objective), u_lo, u_hi)
        nc = normalize(float(item.economics.contribution_margin_cents), c_lo, c_hi)
        score = weight * nu + (1.0 - weight) * nc
        scored.append(
            (
                item,
                SelectionScore(
                    offer_id=item.offer_id,
                    normalized_utility=round(nu, 6),
                    normalized_contribution=round(nc, 6),
                    score=round(score, 6),
                    alpha=weight,
                    rule=SELECTION_RULE,
                    mode=chosen.mode if objective is not None else None,
                    buyer_weight=(
                        chosen.buyer_weight if objective is not None else weight
                    ),
                    merchant_weight=(
                        chosen.merchant_weight
                        if objective is not None
                        else round(1.0 - weight, 6)
                    ),
                    version=chosen.version if objective is not None else None,
                ),
            )
        )
    scored.sort(
        key=lambda pair: (
            -pair[1].score,
            -pair[0].economics.contribution_margin_cents,
            -_buyer_score(pair[0], buyer_objective),
            pair[0].economics.incremental_intervention_cost_cents,
            pair[0].sku,
            str(pair[0].offer_id),
        )
    )
    winner, meta = scored[0]
    return winner, meta


def reselect(
    frontier: list[ScoredOffer],
    objective: MerchantObjectiveConfig,
    *,
    buyer_objective: dict[UUID, float] | None = None,
) -> tuple[ScoredOffer | None, SelectionScore | None]:
    """Select again from an existing frontier. Does not rebuild Pareto."""
    return select_offer(
        frontier, objective=objective, buyer_objective=buyer_objective
    )


def reselect_public(
    points: list[dict[str, object]],
    objective: MerchantObjectiveConfig,
) -> tuple[str | None, SelectionScore | None]:
    """Reselect from persisted public Pareto rows. No rematch or economics."""
    if not points:
        return None, None
    utilities = [float(item["buyer_utility"]) for item in points]  # type: ignore[arg-type]
    contributions = [
        float(item["contribution_margin_cents"]) for item in points  # type: ignore[arg-type]
    ]
    u_lo, u_hi = _minmax(utilities)
    c_lo, c_hi = _minmax(contributions)
    scored: list[tuple[str, SelectionScore, tuple[object, ...]]] = []
    for item in points:
        offer_id = str(item["offer_id"])
        utility = float(cast(Any, item["buyer_utility"]))
        contribution = int(cast(Any, item["contribution_margin_cents"]))
        intervention = int(
            cast(Any, item.get("incremental_intervention_cost_cents") or 0)
        )
        nu = normalize(utility, u_lo, u_hi)
        nc = normalize(float(contribution), c_lo, c_hi)
        score = objective.buyer_weight * nu + objective.merchant_weight * nc
        meta = SelectionScore(
            offer_id=cast(Any, item["offer_id"]),
            normalized_utility=round(nu, 6),
            normalized_contribution=round(nc, 6),
            score=round(score, 6),
            alpha=objective.buyer_weight,
            rule=SELECTION_RULE,
            mode=objective.mode,
            buyer_weight=objective.buyer_weight,
            merchant_weight=objective.merchant_weight,
            version=objective.version,
        )
        scored.append(
            (
                offer_id,
                meta,
                (
                    -score,
                    -contribution,
                    -utility,
                    intervention,
                    str(item.get("sku") or ""),
                    offer_id,
                ),
            )
        )
    scored.sort(key=lambda row: row[2])
    winner_id, meta, _key = scored[0]
    return winner_id, meta


def compare_objectives(frontier: list[ScoredOffer]) -> list[ObjectiveComparison]:
    rows: list[ObjectiveComparison] = []
    for mode in ("GROWTH", "BALANCED", "MARGIN"):
        winner, meta = reselect(frontier, preset(cast(ObjectiveMode, mode)))
        rows.append(
            ObjectiveComparison(
                mode=mode,
                offer_id=winner.offer_id if winner else None,
                product_name=winner.product_name if winner else None,
                sku=winner.sku if winner else None,
                buyer_utility=winner.utility.score if winner else None,
                contribution_margin_cents=(
                    winner.economics.contribution_margin_cents if winner else None
                ),
                intervention_cost_cents=(
                    winner.economics.incremental_intervention_cost_cents
                    if winner
                    else None
                ),
                score=meta.score if meta else None,
            )
        )
    return rows

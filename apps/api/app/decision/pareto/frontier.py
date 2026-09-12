"""Build a 2-objective buyer-utility × contribution frontier."""

from datetime import UTC, datetime
from uuid import UUID

import numpy as np

from app.decision.pareto.dominance import (
    DEFAULT_EPSILON,
    first_dominator,
    pareto_mask,
)
from app.decision.pareto.models import ObjectiveSpec, ParetoResult

HERO_OBJECTIVES = (
    ObjectiveSpec(name="simulated_buyer_utility", sense="maximize", unit="score"),
    ObjectiveSpec(name="contribution_margin_cents", sense="maximize", unit="AUD_CENTS"),
)


def build_frontier(
    offer_ids: list[UUID],
    utilities: list[float],
    contributions: list[int],
    *,
    epsilon: float = DEFAULT_EPSILON,
) -> ParetoResult:
    if not offer_ids:
        return ParetoResult(
            total_policy_safe_offers=0,
            efficient_offer_ids=[],
            dominated_offer_ids=[],
            dominated_by={},
            objective_metadata=list(HERO_OBJECTIVES),
            epsilon=epsilon,
            generated_at=datetime.now(UTC),
        )
    values = np.column_stack(
        [
            np.asarray(utilities, dtype=np.float64),
            np.asarray(contributions, dtype=np.float64),
        ]
    )
    maximize = (True, True)
    mask = pareto_mask(values, maximize=maximize, epsilon=epsilon)
    efficient: list[UUID] = []
    dominated: list[UUID] = []
    mapping: dict[str, UUID | None] = {}
    for i, offer_id in enumerate(offer_ids):
        if mask[i]:
            efficient.append(offer_id)
            mapping[str(offer_id)] = None
            continue
        source = first_dominator(i, values, maximize=maximize, epsilon=epsilon)
        dominated.append(offer_id)
        mapping[str(offer_id)] = offer_ids[source] if source is not None else None
    return ParetoResult(
        total_policy_safe_offers=len(offer_ids),
        efficient_offer_ids=efficient,
        dominated_offer_ids=dominated,
        dominated_by=mapping,
        objective_metadata=list(HERO_OBJECTIVES),
        epsilon=epsilon,
        generated_at=datetime.now(UTC),
    )

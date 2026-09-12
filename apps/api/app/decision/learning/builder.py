"""Turn Arena / negotiation artefacts into CommerceInteraction payloads."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.decision.arena.models import ArenaContext, ArenaMissionResult
from app.decision.learning.enums import OutcomeSource, OutcomeType
from app.decision.learning.features import extract_features
from app.decision.offers.models import OfferCandidate
from app.decision.optimisation.models import ScoredOffer
from app.decision.retrieval.models import RankedProductMatch


def _match_for(
    context: ArenaContext, variant_id: UUID
) -> RankedProductMatch | None:
    return next(
        (item for item in context.matches if item.variant_id == variant_id),
        None,
    )


def _offer_for(context: ArenaContext, offer_id: UUID) -> OfferCandidate | None:
    return next((item for item in context.offers if item.id == offer_id), None)


def _scored_for(context: ArenaContext, offer_id: UUID) -> ScoredOffer | None:
    return next((item for item in context.scored if item.offer_id == offer_id), None)


def _payload(
    *,
    context: ArenaContext,
    offer_id: UUID,
    selected: bool,
    no_purchase: bool,
    source: OutcomeSource,
    extra: dict[str, Any],
) -> dict[str, Any] | None:
    scored = _scored_for(context, offer_id)
    offer = _offer_for(context, offer_id)
    if scored is None or offer is None:
        return None
    if not scored.policy.policy_safe:
        return None
    features = extract_features(
        intent=context.intent,
        weights=context.weights,
        scored=scored,
        offer=offer,
        match=_match_for(context, scored.variant_id),
        buyer_profile=context.buyer_profile,
    )
    outcome = OutcomeType.NO_PURCHASE if no_purchase else (
        OutcomeType.SELECTED if selected else OutcomeType.NOT_SELECTED
    )
    return {
        "id": str(uuid4()),
        "group_id": context.mission.id,
        "mission_id": context.mission.id,
        "offer_id": str(offer_id),
        "buyer_profile": context.buyer_profile,
        "structured_intent": context.intent.model_dump(mode="json"),
        "offer_snapshot": {
            "sku": scored.sku,
            "product_name": scored.product_name,
            "total_price_cents": scored.total_customer_price_cents,
            "delivery": scored.delivery_code,
            "delivery_days": scored.delivery_days,
            "warranty": scored.warranty_code,
            "warranty_months": scored.warranty_months,
            "bundle": scored.bundle_code,
            "returns": scored.return_policy_code,
            "merchant_contribution_cents": scored.economics.contribution_margin_cents,
            "intervention_cost_cents": (
                scored.economics.incremental_intervention_cost_cents
            ),
        },
        "product_fit": scored.product_fit,
        "total_price_cents": scored.total_customer_price_cents,
        "delivery": scored.delivery_code,
        "warranty": scored.warranty_code,
        "bundle": scored.bundle_code,
        "returns": scored.return_policy_code,
        "merchant_contribution_cents": scored.economics.contribution_margin_cents,
        "intervention_cost_cents": scored.economics.incremental_intervention_cost_cents,
        "outcome_type": outcome.value,
        "selected": selected and not no_purchase,
        "accepted": None,
        "transacted": None,
        "outcome_source": source.value,
        "policy_safe": True,
        "hard_constraints_satisfied": True,
        "buyer_utility": scored.utility.score,
        "features": features,
        "observed_at": datetime.now(UTC).isoformat(),
        **extra,
    }


def interactions_from_arena(
    result: ArenaMissionResult,
    context: ArenaContext,
    *,
    extra_negatives: int = 16,
) -> list[dict[str, Any]]:
    """Valid competing offers only. Invalid configs are not rejection labels."""
    selected_id = result.selection.selected_offer_id
    no_purchase = result.selection.no_purchase
    rows: list[dict[str, Any]] = []
    seen: set[UUID] = set()
    extra = {
        "arena_run_id": None,
        "scenario_tags": list(result.mission.scenario_tags),
        "seed": result.mission.seed,
    }
    for response in result.responses:
        if (
            response.offer_id is None
            or not response.policy_safe
            or not response.hard_constraints_satisfied
        ):
            continue
        row = _payload(
            context=context,
            offer_id=response.offer_id,
            selected=response.offer_id == selected_id,
            no_purchase=no_purchase,
            source=OutcomeSource.SIMULATED_ARENA,
            extra=extra,
        )
        if row is None:
            continue
        rows.append(row)
        seen.add(response.offer_id)
    extras = [
        item
        for item in context.scored
        if item.policy.policy_safe and item.offer_id not in seen
    ]
    extras.sort(
        key=lambda item: (
            item.total_customer_price_cents,
            item.sku,
            str(item.offer_id),
        )
    )
    step = max(1, len(extras) // max(extra_negatives, 1))
    for item in extras[::step][:extra_negatives]:
        row = _payload(
            context=context,
            offer_id=item.offer_id,
            selected=item.offer_id == selected_id,
            no_purchase=no_purchase,
            source=OutcomeSource.SIMULATED_ARENA,
            extra=extra,
        )
        if row is not None:
            rows.append(row)
    return rows


def interactions_from_negotiation(
    *,
    session_id: UUID,
    proposal_id: UUID,
    offer_id: UUID,
    accepted: bool,
    rejected: bool,
    countered: bool,
    context: ArenaContext,
) -> dict[str, Any] | None:
    if accepted:
        outcome = OutcomeType.ACCEPTED
        selected = True
    elif rejected:
        outcome = OutcomeType.REJECTED
        selected = False
    elif countered:
        outcome = OutcomeType.COUNTERED
        selected = False
    else:
        return None
    row = _payload(
        context=context,
        offer_id=offer_id,
        selected=selected,
        no_purchase=False,
        source=OutcomeSource.SIMULATED_NEGOTIATION,
        extra={
            "negotiation_session_id": str(session_id),
            "proposal_id": str(proposal_id),
        },
    )
    if row is None:
        return None
    row["outcome_type"] = outcome.value
    row["accepted"] = accepted
    return row

"""Merchant objective validation, persistence, and Pareto selection."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.economics.calculator import compute_economics
from app.decision.optimisation.models import ScoredOffer
from app.decision.optimisation.objective import (
    OBJECTIVE_VERSION,
    MerchantObjectiveConfig,
    default_objective,
    preset,
    resolve_objective,
)
from app.decision.optimisation.selection import (
    normalize,
    reselect,
    reselect_public,
    select_offer,
)
from app.decision.policies.offer_policy_evaluator import OfferPolicyEvaluation
from app.decision.utility.models import (
    FitComponents,
    SimulatedBuyerUtility,
    UtilityTrace,
)
from app.decision.utility.profiles import PROFILES
from app.models import MerchantObjective
from app.schemas.objective import MerchantObjectiveUpdate
from tests.test_economics import _offer

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)


def _restore(client: TestClient) -> None:
    client.patch("/api/v1/merchant/objective", json={"mode": "BALANCED"})


def _scored(
    *,
    utility: float,
    contribution: int,
    sku: str,
    intervention: int = 0,
    offer_id=None,
) -> ScoredOffer:
    offer = _offer(
        sku=sku,
        product_name=sku,
        total_customer_price_cents=30000,
        direct_intervention_cost_cents=intervention,
    )
    eco = compute_economics(offer, cogs_cents=18000)
    eco.contribution_margin_cents = contribution
    eco.incremental_intervention_cost_cents = intervention
    return ScoredOffer(
        offer_id=offer_id or uuid4(),
        variant_id=offer.variant_id,
        sku=sku,
        product_name=sku,
        brand="Astra",
        product_price_cents=30000,
        total_customer_price_cents=30000,
        delivery_code="STANDARD",
        delivery_name="Standard",
        delivery_days=2,
        warranty_code="STANDARD_12",
        warranty_name="12 months",
        warranty_months=12,
        bundle_code=None,
        bundle_name=None,
        return_policy_code=None,
        return_window_days=30,
        economics=eco,
        policy=OfferPolicyEvaluation(
            policy_safe=True, checks=[], rejection_codes=[]
        ),
        utility=SimulatedBuyerUtility(
            score=utility,
            fits=FitComponents(
                product=utility,
                price=0.7,
                delivery=0.7,
                warranty=0.5,
                bundle=0.5,
                returns=0.5,
            ),
            weights=PROFILES["BALANCED"],
            trace=UtilityTrace(components=[], total=utility),
            profile_id="BALANCED",
            disclaimer="sim",
        ),
        is_pareto_efficient=True,
    )


def test_presets_are_valid() -> None:
    growth = preset("GROWTH")
    balanced = preset("BALANCED")
    margin = preset("MARGIN")
    assert growth.buyer_weight == 0.70
    assert growth.merchant_weight == 0.30
    assert balanced.buyer_weight == 0.50
    assert balanced.merchant_weight == 0.50
    assert margin.buyer_weight == 0.30
    assert margin.merchant_weight == 0.70
    assert default_objective().mode == "BALANCED"
    assert default_objective().version == OBJECTIVE_VERSION


def test_custom_weights_normalized() -> None:
    custom = resolve_objective(
        mode="CUSTOM", buyer_weight=0.4, merchant_weight=0.6
    )
    assert custom.mode == "CUSTOM"
    assert custom.buyer_weight == 0.4
    assert custom.merchant_weight == 0.6
    scaled = resolve_objective(
        mode="CUSTOM", buyer_weight=0.2, merchant_weight=0.3
    )
    assert scaled.buyer_weight == 0.4
    assert scaled.merchant_weight == 0.6


def test_invalid_weights_rejected() -> None:
    with pytest.raises(ValidationError):
        MerchantObjectiveConfig(mode="CUSTOM", buyer_weight=-0.1, merchant_weight=1.1)
    with pytest.raises(ValueError):
        resolve_objective(mode="CUSTOM", buyer_weight=0, merchant_weight=0)
    with pytest.raises(ValueError):
        resolve_objective(mode="CUSTOM")
    with pytest.raises(ValueError):
        resolve_objective(mode="UNKNOWN")
    with pytest.raises(ValidationError):
        MerchantObjectiveConfig(
            mode="CUSTOM", buyer_weight=float("nan"), merchant_weight=1
        )


def test_normalize_zero_range() -> None:
    assert normalize(0.8, 0.8, 0.8) == 1.0
    assert normalize(12, 12, 12) == 1.0


def test_single_point_frontier() -> None:
    only = _scored(utility=0.8, contribution=10000, sku="ONLY")
    for mode in ("GROWTH", "BALANCED", "MARGIN"):
        winner, meta = reselect([only], preset(mode))
        assert winner is only
        assert meta is not None
        assert meta.normalized_utility == 1.0
        assert meta.normalized_contribution == 1.0


def test_selection_changes_when_tradeoff_exists() -> None:
    high_fit = _scored(utility=0.91, contribution=8000, sku="FIT-01")
    high_margin = _scored(utility=0.60, contribution=14000, sku="MRG-01")
    frontier = [high_fit, high_margin]
    growth, _ = reselect(frontier, preset("GROWTH"))
    margin, _ = reselect(frontier, preset("MARGIN"))
    balanced, _ = reselect(frontier, preset("BALANCED"))
    assert growth is high_fit
    assert margin is high_margin
    assert balanced is high_margin


def test_selection_stays_same_when_one_point_best() -> None:
    dominant = _scored(utility=0.95, contribution=15000, sku="WIN-01")
    weaker = _scored(utility=0.40, contribution=4000, sku="LOW-01")
    frontier = [dominant, weaker]
    picked = {
        reselect(frontier, preset(mode))[0].offer_id
        for mode in ("GROWTH", "BALANCED", "MARGIN")
    }
    assert picked == {dominant.offer_id}


def test_stable_tie_break_uses_sku_then_offer_id() -> None:
    left_id = uuid4()
    right_id = uuid4()
    left = _scored(
        utility=0.8, contribution=10000, sku="AAA-01", offer_id=left_id
    )
    right = _scored(
        utility=0.8, contribution=10000, sku="ZZZ-01", offer_id=right_id
    )
    first, _ = select_offer([right, left], objective=preset("BALANCED"))
    second, _ = select_offer([left, right], objective=preset("BALANCED"))
    assert first is not None and second is not None
    assert first.sku == "AAA-01"
    assert first.offer_id == second.offer_id


def test_reselect_public_matches_scored() -> None:
    high_fit = _scored(utility=0.91, contribution=8000, sku="FIT-01")
    high_margin = _scored(utility=0.60, contribution=14000, sku="MRG-01")
    points = [
        {
            "offer_id": str(high_fit.offer_id),
            "buyer_utility": 0.91,
            "contribution_margin_cents": 8000,
            "incremental_intervention_cost_cents": 0,
            "sku": "FIT-01",
        },
        {
            "offer_id": str(high_margin.offer_id),
            "buyer_utility": 0.60,
            "contribution_margin_cents": 14000,
            "incremental_intervention_cost_cents": 0,
            "sku": "MRG-01",
        },
    ]
    winner_id, _ = reselect_public(points, preset("GROWTH"))
    assert winner_id == str(high_fit.offer_id)


@pytest.mark.asyncio
async def test_default_objective_exists(db_session: AsyncSession) -> None:
    count = await db_session.scalar(
        select(func.count()).select_from(MerchantObjective)
    )
    assert count and count >= 1
    row = (
        await db_session.execute(
            select(MerchantObjective).where(MerchantObjective.is_active.is_(True))
        )
    ).scalars().first()
    assert row is not None
    assert row.mode == "BALANCED"


def test_objective_api_and_snapshot(client: TestClient) -> None:
    current = client.get("/api/v1/merchant/objective")
    assert current.status_code == 200
    body = current.json()
    assert body["mode"] == "BALANCED"
    assert body["buyer_weight"] == 0.5
    assert body["merchant_weight"] == 0.5
    try:
        updated = client.patch(
            "/api/v1/merchant/objective", json={"mode": "MARGIN"}
        )
        assert updated.status_code == 200
        assert updated.json()["mode"] == "MARGIN"
        assert updated.json()["buyer_weight"] == 0.3
        decided = client.post(
            "/api/v1/decision/run",
            json={
                "intent": HERO,
                "parser_mode": "rule_based",
                "buyer_profile": "INTENT_ADAPTED",
            },
        )
        assert decided.status_code == 200
        opt = decided.json()["optimisation"]
        assert opt["merchant_objective"]["mode"] == "MARGIN"
        assert opt["merchant_objective"]["version"] == OBJECTIVE_VERSION
        assert opt["selection"]["mode"] == "MARGIN"
        stored = client.get(
            f"/api/v1/optimisation/runs/{opt['optimisation_run_id']}"
        )
        assert stored.json()["merchant_objective"]["mode"] == "MARGIN"
        invalid = client.patch(
            "/api/v1/merchant/objective",
            json={"mode": "CUSTOM", "buyer_weight": -1, "merchant_weight": 2},
        )
        assert invalid.status_code == 422
    finally:
        _restore(client)


def test_frontier_invariant_across_objectives(client: TestClient) -> None:
    _restore(client)
    decided = client.post(
        "/api/v1/decision/run",
        json={
            "intent": HERO,
            "parser_mode": "rule_based",
            "buyer_profile": "URGENT_TRAVELLER",
        },
    )
    assert decided.status_code == 200
    run_id = decided.json()["optimisation"]["optimisation_run_id"]
    frontiers: list[set[str]] = []
    try:
        for mode in ("GROWTH", "BALANCED", "MARGIN"):
            client.patch("/api/v1/merchant/objective", json={"mode": mode})
            body = client.post(f"/api/v1/optimisation/runs/{run_id}/reselect")
            assert body.status_code == 200
            payload = body.json()
            frontiers.append(
                {item["offer_id"] for item in payload["pareto_offers"]}
            )
            assert payload["merchant_objective"]["mode"] == mode
            assert payload["summary"]["pareto_efficient"] == len(
                payload["pareto_offers"]
            )
        assert frontiers[0] == frontiers[1] == frontiers[2]
    finally:
        _restore(client)


def test_negative_custom_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        MerchantObjectiveUpdate.model_validate(
            {"mode": "CUSTOM", "buyer_weight": -0.2, "merchant_weight": 1.2}
        )

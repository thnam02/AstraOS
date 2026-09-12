"""Optimise a constructed offer space. Does not negotiate or transact."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.decision.intent.models import ShoppingIntent
from app.decision.offers.models import OfferCandidate
from app.decision.optimisation.engine import (
    apply_experimental_buyer_objective,
    score_space,
)
from app.decision.optimisation.models import (
    ALGORITHM_VERSION,
    SELECTION_RULE,
    EngineResult,
    MerchantObjectiveSnapshot,
)
from app.decision.optimisation.objective import (
    MerchantObjectiveConfig,
    default_objective,
    explain_objective,
)
from app.decision.optimisation.selection import reselect_public
from app.decision.pareto.frontier import HERO_OBJECTIVES
from app.decision.utility.models import UTILITY_DISCLAIMER
from app.models.optimisation import OptimisationRun
from app.repositories.offer import OfferRepository
from app.repositories.optimisation import OptimisationRepository
from app.repositories.policy import MerchantPolicyRepository
from app.repositories.product import ProductRepository
from app.schemas.optimisation import (
    BuyerModelBlock,
    OptimisationResponse,
    OptimisationSummary,
    OptimisationTiming,
    PlotPoint,
    PublicScoredOffer,
    to_plot_point,
    to_public_scored,
)
from app.services.matching import SemanticMatchingService

logger = logging.getLogger("astraos.optimisation")

MAX_PLOT_DOMINATED = 400
MAX_ALTERNATIVES = 5


class OptimisationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.offers = OfferRepository(session)
        self.runs = OptimisationRepository(session)
        self.policy = MerchantPolicyRepository(session)
        self.products = ProductRepository(session)
        self.matching = SemanticMatchingService(session)

    async def run(
        self,
        offer_run_id: uuid.UUID,
        *,
        buyer_profile: str = "INTENT_ADAPTED",
        alpha: float | None = None,
        objective: MerchantObjectiveConfig | None = None,
    ) -> OptimisationResponse:
        response, _engine = await self.evaluate(
            offer_run_id,
            buyer_profile=buyer_profile,
            alpha=alpha,
            objective=objective,
        )
        return response

    async def evaluate(
        self,
        offer_run_id: uuid.UUID,
        *,
        buyer_profile: str = "INTENT_ADAPTED",
        alpha: float | None = None,
        objective: MerchantObjectiveConfig | None = None,
    ) -> tuple[OptimisationResponse, object]:
        started = time.perf_counter()
        construction = await self.offers.get_run(offer_run_id)
        if construction is None:
            raise ValueError("Offer run not found.")
        rows = await self.offers.list_all(offer_run_id)
        candidates = [OfferCandidate.model_validate(row.payload) for row in rows]
        for candidate, row in zip(candidates, rows, strict=True):
            candidate.offer_run_id = row.run_id
            candidate.id = row.id

        intent = ShoppingIntent.model_validate(construction.parsed_intent)
        policy = await self.policy.get_active()
        if policy is None:
            raise RuntimeError("No active merchant policy.")
        from app.services.objective import MerchantObjectiveService

        chosen = (
            objective
            or await MerchantObjectiveService(self.session).active_config()
        )

        variant_ids = list({item.variant_id for item in candidates})
        variants = {
            item.id: item
            for item in await self.products.list_variants_by_ids(variant_ids)
        }
        product_fits: dict[uuid.UUID, float] = {}
        if construction.match_run_id is not None:
            match = await self.matching.get_run(construction.match_run_id)
            if match is not None:
                for item in match.semantic_matching.matches:
                    product_fits[item.variant_id] = item.overall_semantic_fit

        result = score_space(
            candidates,
            intent=intent,
            policy=policy,
            variants=variants,
            product_fits=product_fits,
            profile_id=buyer_profile,
            alpha=alpha,
            objective=chosen,
        )
        result = await self._maybe_apply_learned_objective(
            result,
            candidates=candidates,
            intent=intent,
            buyer_profile=buyer_profile,
            alpha=alpha,
            objective=chosen,
        )
        persist_started = time.perf_counter()
        response = await self._persist(
            construction_id=construction.id,
            match_run_id=construction.match_run_id,
            raw_intent=construction.raw_intent,
            buyer_profile=buyer_profile,
            alpha=chosen.alpha,
            policy=policy,
            result=result,
            objective=chosen,
            started=started,
        )
        persist_ms = (time.perf_counter() - persist_started) * 1000
        response.timing.persistence_ms = round(persist_ms, 2)
        response.timing.total_optimisation_ms = round(
            (time.perf_counter() - started) * 1000, 2
        )
        await self._attach_shadow_score(
            response,
            result=result,
            candidates=candidates,
            intent=intent,
            buyer_profile=buyer_profile,
        )
        return response, result

    async def _attach_shadow_score(
        self,
        response: OptimisationResponse,
        *,
        result: object,
        candidates: list[OfferCandidate],
        intent: ShoppingIntent,
        buyer_profile: str,
    ) -> None:
        """Experimental only. Never changes the cold-start recommendation."""
        if response.recommended_offer is None:
            return
        try:
            from app.decision.learning import LEARNING_DISCLAIMER, SCORE_LABEL
            from app.decision.optimisation.models import EngineResult
            from app.decision.utility.scorer import weights_for
            from app.services.learning import LearningService

            assert isinstance(result, EngineResult)
            weights = weights_for(intent, buyer_profile)
            scores = await LearningService(self.session).shadow_scores_for_public(
                result.scored,
                offers=candidates,
                intent=intent,
                weights=weights,
                matches=[],
                buyer_profile=buyer_profile,
            )
            key = str(response.recommended_offer.offer_id)
            if key in scores:
                response.recommended_offer.learned_synthetic_score = scores[key]
                response.recommended_offer.learned_score_label = SCORE_LABEL
                response.buyer_model.disclaimer = (
                    f"{response.buyer_model.disclaimer} {LEARNING_DISCLAIMER}"
                )
        except Exception:
            logger.exception("shadow_score_failed")
            return

    async def _maybe_apply_learned_objective(
        self,
        result: EngineResult,
        *,
        candidates: list[OfferCandidate],
        intent: ShoppingIntent,
        buyer_profile: str,
        alpha: float | None,
        objective: MerchantObjectiveConfig | None = None,
    ) -> EngineResult:
        """LEARNED_EXPERIMENTAL only. Default COLD_START is unchanged."""
        from app.decision.utility.scorer import weights_for
        from app.services.learning import LearningService

        if settings.response_model_mode != "LEARNED_EXPERIMENTAL":
            return result
        scores = await LearningService(self.session).shadow_scores_for_public(
            result.scored,
            offers=candidates,
            intent=intent,
            weights=weights_for(intent, buyer_profile),
            matches=[],
            buyer_profile=buyer_profile,
        )
        if not scores:
            return result
        learned = {uuid.UUID(key): value for key, value in scores.items()}
        updated = apply_experimental_buyer_objective(
            result, learned, alpha=alpha, objective=objective
        )
        updated.explanation = [
            "EXPERIMENTAL: Pareto buyer objective used the active learned "
            "synthetic response model. Cold-start utility traces are unchanged.",
            *updated.explanation,
        ]
        return updated

    async def get_run(self, run_id: uuid.UUID) -> OptimisationResponse | None:
        row = await self.runs.get(run_id)
        if row is None:
            return None
        return _row_to_response(row)

    async def reselect(
        self,
        run_id: uuid.UUID,
        *,
        objective: MerchantObjectiveConfig | None = None,
    ) -> OptimisationResponse:
        started = time.perf_counter()
        row = await self.runs.get(run_id)
        if row is None:
            raise ValueError("Optimisation run not found.")
        from app.services.objective import MerchantObjectiveService

        chosen = (
            objective
            or await MerchantObjectiveService(self.session).active_config()
        )
        pareto = list(row.pareto_offers or [])
        winner_id, meta = reselect_public(pareto, chosen)
        response = _row_to_response(row)
        response.merchant_objective = MerchantObjectiveSnapshot.model_validate(
            chosen.snapshot()
        )
        response.selection = meta
        if winner_id:
            for offer in response.pareto_offers:
                offer.is_recommended = str(offer.offer_id) == winner_id
            for point in response.plot_points:
                point.is_recommended = str(point.offer_id) == winner_id
            response.recommended_offer = next(
                (
                    item
                    for item in response.pareto_offers
                    if str(item.offer_id) == winner_id
                ),
                response.recommended_offer,
            )
            response.alternative_pareto_offers = [
                item
                for item in response.pareto_offers
                if str(item.offer_id) != winner_id
            ][:MAX_ALTERNATIVES]
        response.explanation = [
            explain_objective(chosen),
            (
                "Merchant strategy changed the selected efficient offer, "
                "not the feasible offer space."
            ),
            *[
                line
                for line in response.explanation
                if "Selected from the" not in line
            ],
        ]
        response.objective_comparisons = _public_comparisons(pareto)
        response.timing.selection_ms = round(
            (time.perf_counter() - started) * 1000, 2
        )
        return response

    async def _persist(
        self,
        *,
        construction_id: uuid.UUID,
        match_run_id: uuid.UUID | None,
        raw_intent: str,
        buyer_profile: str,
        alpha: float,
        policy: object,
        result: object,
        started: float,
        objective: MerchantObjectiveConfig | None = None,
    ) -> OptimisationResponse:
        from app.models import MerchantPolicy

        assert isinstance(result, EngineResult)
        assert isinstance(policy, MerchantPolicy)
        safe = [item for item in result.scored if item.policy.policy_safe]
        recommended_public = (
            to_public_scored(result.recommended) if result.recommended else None
        )
        pareto_public = [to_public_scored(item) for item in result.frontier]
        alternatives = [
            item
            for item in pareto_public
            if (
                recommended_public is None
                or item.offer_id != recommended_public.offer_id
            )
        ][:MAX_ALTERNATIVES]
        plot = _plot_points(safe)
        weights = (
            result.recommended.utility.weights.as_dict()
            if result.recommended is not None
            else (
                result.scored[0].utility.weights.as_dict() if result.scored else {}
            )
        )
        summary = OptimisationSummary(
            offers_considered=len(result.scored),
            policy_safe=len(safe),
            policy_rejected=len(result.scored) - len(safe),
            pareto_efficient=len(result.frontier),
        )
        buyer_model = BuyerModelBlock(
            profile_id=buyer_profile,
            weights=weights,
            disclaimer=UTILITY_DISCLAIMER,
        )
        timing = OptimisationTiming(
            economics_ms=result.timing.get("economics_ms", 0),
            policy_filter_ms=result.timing.get("policy_filter_ms", 0),
            utility_ms=result.timing.get("utility_ms", 0),
            pareto_ms=result.timing.get("pareto_ms", 0),
            selection_ms=result.timing.get("selection_ms", 0),
            counterfactual_ms=result.timing.get("counterfactual_ms", 0),
            persistence_ms=0,
            total_optimisation_ms=0,
        )
        now = datetime.now(UTC)
        row = OptimisationRun(
            offer_run_id=construction_id,
            match_run_id=match_run_id,
            buyer_profile=buyer_profile,
            weight_configuration=weights,
            merchant_policy_id=policy.id,
            merchant_policy_snapshot={
                "minimum_margin_rate": float(policy.minimum_margin_rate),
                "maximum_discount_rate": float(policy.maximum_discount_rate),
                "delivery_subsidy_enabled": policy.delivery_subsidy_enabled,
                "warranty_upgrade_enabled": policy.warranty_upgrade_enabled,
                "bundle_enabled": policy.bundle_enabled,
                "flexible_returns_enabled": policy.flexible_returns_enabled,
                "maximum_delivery_subsidy_cents": policy.maximum_delivery_subsidy_cents,
                "maximum_warranty_subsidy_cents": policy.maximum_warranty_subsidy_cents,
                "maximum_bundle_subsidy_cents": policy.maximum_bundle_subsidy_cents,
            },
            total_offers=summary.offers_considered,
            policy_safe_offers=summary.policy_safe,
            policy_rejected_offers=summary.policy_rejected,
            pareto_count=summary.pareto_efficient,
            recommended_offer_id=(
                result.recommended.offer_id if result.recommended else None
            ),
            algorithm_version=ALGORITHM_VERSION,
            selection_rule=SELECTION_RULE,
            selection_alpha=str(alpha),
            merchant_objective=(
                objective.snapshot()
                if objective is not None
                else (
                    result.merchant_objective.model_dump()
                    if result.merchant_objective
                    else default_objective().snapshot()
                )
            ),
            raw_intent=raw_intent,
            timing=timing.model_dump(),
            summary=summary.model_dump(),
            buyer_model=buyer_model.model_dump(),
            recommended=(
                recommended_public.model_dump(mode="json")
                if recommended_public
                else None
            ),
            pareto_offers=[item.model_dump(mode="json") for item in pareto_public],
            plot_points=[item.model_dump(mode="json") for item in plot],
            counterfactuals=[
                item.model_dump(mode="json") for item in result.counterfactuals
            ],
            comparisons=[item.model_dump(mode="json") for item in result.comparisons],
            explanation=result.explanation,
            failure=result.failure.model_dump(mode="json") if result.failure else None,
            run_metadata={"algorithm": ALGORITHM_VERSION},
            completed_at=now,
        )
        await self.runs.add(row)
        await self.session.commit()
        logger.info(
            "optimisation_complete run_id=%s safe=%s pareto=%s recommended=%s",
            row.id,
            summary.policy_safe,
            summary.pareto_efficient,
            row.recommended_offer_id,
        )
        return OptimisationResponse(
            optimisation_run_id=row.id,
            offer_run_id=construction_id,
            match_run_id=match_run_id,
            summary=summary,
            buyer_model=buyer_model,
            timing=timing,
            recommended_offer=recommended_public,
            selection=result.selection,
            pareto_offers=pareto_public,
            alternative_pareto_offers=alternatives,
            plot_points=plot,
            counterfactuals=result.counterfactuals,
            comparisons=result.comparisons,
            explanation=result.explanation,
            failure=result.failure,
            objectives=list(HERO_OBJECTIVES),
            created_at=row.created_at,
            merchant_objective=result.merchant_objective,
            objective_comparisons=result.objective_comparisons,
        )


def _plot_points(safe: list) -> list[PlotPoint]:
    from app.decision.optimisation.models import ScoredOffer

    points: list[PlotPoint] = []
    dominated = [
        item
        for item in safe
        if isinstance(item, ScoredOffer) and not item.is_pareto_efficient
    ]
    efficient = [
        item
        for item in safe
        if isinstance(item, ScoredOffer) and item.is_pareto_efficient
    ]
    if len(dominated) > MAX_PLOT_DOMINATED:
        step = max(1, len(dominated) // MAX_PLOT_DOMINATED)
        dominated = dominated[::step][:MAX_PLOT_DOMINATED]
    for item in [*dominated, *efficient]:
        points.append(to_plot_point(item))
    return points


def _row_to_response(row: OptimisationRun) -> OptimisationResponse:
    recommended = (
        PublicScoredOffer.model_validate(row.recommended)
        if row.recommended
        else None
    )
    pareto = [PublicScoredOffer.model_validate(item) for item in row.pareto_offers]
    alternatives = [
        item
        for item in pareto
        if recommended is None or item.offer_id != recommended.offer_id
    ][:MAX_ALTERNATIVES]
    from app.decision.optimisation.models import (
        CounterfactualRow,
        NamedComparison,
        OptimisationFailure,
    )

    return OptimisationResponse(
        optimisation_run_id=row.id,
        offer_run_id=row.offer_run_id,
        match_run_id=row.match_run_id,
        summary=OptimisationSummary.model_validate(row.summary),
        buyer_model=BuyerModelBlock.model_validate(row.buyer_model),
        timing=OptimisationTiming.model_validate(row.timing),
        recommended_offer=recommended,
        selection=None,
        pareto_offers=pareto,
        alternative_pareto_offers=alternatives,
        plot_points=[PlotPoint.model_validate(item) for item in row.plot_points],
        counterfactuals=[
            CounterfactualRow.model_validate(item) for item in row.counterfactuals
        ],
        comparisons=[NamedComparison.model_validate(item) for item in row.comparisons],
        explanation=list(row.explanation),
        failure=(
            OptimisationFailure.model_validate(row.failure) if row.failure else None
        ),
        objectives=list(HERO_OBJECTIVES),
        created_at=row.created_at,
        merchant_objective=(
            MerchantObjectiveSnapshot.model_validate(row.merchant_objective)
            if row.merchant_objective
            else None
        ),
        objective_comparisons=_public_comparisons(list(row.pareto_offers or [])),
    )


def _public_comparisons(pareto: list[object]) -> list:
    from typing import cast

    from app.decision.optimisation.models import ObjectiveComparison
    from app.decision.optimisation.objective import ObjectiveMode, preset

    rows = []
    points = [item if isinstance(item, dict) else {} for item in pareto]
    for mode in ("GROWTH", "BALANCED", "MARGIN"):
        winner_id, meta = reselect_public(
            points, preset(cast(ObjectiveMode, mode))
        )
        match = next(
            (item for item in points if str(item.get("offer_id")) == winner_id),
            None,
        )
        rows.append(
            ObjectiveComparison(
                mode=mode,
                offer_id=meta.offer_id if meta else None,
                product_name=match.get("product_name") if match else None,
                sku=match.get("sku") if match else None,
                buyer_utility=match.get("buyer_utility") if match else None,
                contribution_margin_cents=(
                    match.get("contribution_margin_cents") if match else None
                ),
                intervention_cost_cents=(
                    match.get("incremental_intervention_cost_cents") if match else None
                ),
                score=meta.score if meta else None,
            )
        )
    return rows

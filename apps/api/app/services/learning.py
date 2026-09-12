"""Synthetic dataset generation, training, and shadow scoring."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.arena.context import ArenaCatalogueCache
from app.decision.arena.missions import generate_missions
from app.decision.arena.runner import run_mission
from app.decision.intent.models import ShoppingIntent
from app.decision.learning import (
    DATASET_VERSION_NAME,
    FEATURE_SCHEMA_VERSION,
    LEARNING_DISCLAIMER,
    SCORE_LABEL,
    TARGET_DEFINITION,
    TARGET_NAME,
)
from app.decision.learning.artifacts import load_artifact, save_artifact
from app.decision.learning.builder import interactions_from_arena
from app.decision.learning.dataset import build_dataset, grouped_split
from app.decision.learning.enums import OutcomeSource
from app.decision.learning.evaluation import (
    calibration_bins,
    classification_metrics,
    ranking_metrics,
)
from app.decision.learning.features import (
    FEATURE_NAMES,
    NUMERIC_FEATURES,
    extract_features,
)
from app.decision.learning.leakage import leakage_violations
from app.decision.learning.models import (
    BoostingResponseModel,
    ColdStartUtilityBaseline,
    LogisticResponseModel,
    PriceHeuristic,
    select_logistic_c,
)
from app.decision.offers.models import OfferCandidate
from app.decision.optimisation.models import ScoredOffer
from app.decision.retrieval.models import RankedProductMatch
from app.decision.utility.models import UtilityWeights
from app.models import (
    CommerceInteraction,
    LearningDatasetVersion,
    ModelTrainingRun,
    ResponseModelVersion,
)
from app.repositories.learning import LearningRepository

ABLATIONS = {
    "offer_only": {
        "total_price_cents",
        "budget_headroom",
        "delivery_days",
        "is_same_day",
        "warranty_months",
        "bundle_present",
        "return_window_days",
        "discount_rate",
        "delivery_code",
    },
    "intent_offer": {
        "w_product",
        "w_price",
        "w_delivery",
        "w_warranty",
        "w_bundle",
        "w_returns",
        "comfort_importance",
        "reliability_importance",
        "warranty_importance",
        "price_importance",
        "has_long_haul",
        "buyer_profile",
        "total_price_cents",
        "budget_headroom",
        "delivery_days",
        "is_same_day",
        "warranty_months",
        "bundle_present",
        "return_window_days",
        "discount_rate",
        "delivery_code",
    },
    "intent_offer_fit": {
        "w_product",
        "w_price",
        "w_delivery",
        "w_warranty",
        "buyer_profile",
        "product_fit",
        "context_fit",
        "preference_fit",
        "evidence_coverage",
        "total_price_cents",
        "budget_headroom",
        "delivery_days",
        "is_same_day",
        "warranty_months",
        "bundle_present",
        "discount_rate",
        "delivery_code",
    },
    "full": set(FEATURE_NAMES),
}


def _mask(rows: list[dict[str, Any]], keep: set[str]) -> list[dict[str, Any]]:
    masked: list[dict[str, Any]] = []
    for row in rows:
        copy = dict(row)
        for key in FEATURE_NAMES:
            if key in keep:
                continue
            copy[key] = 0.0 if key in NUMERIC_FEATURES else "NA"
        masked.append(copy)
    return masked


def _orm_from_payload(payload: dict[str, Any]) -> CommerceInteraction:
    meta = {
        "scenario_tags": payload.get("scenario_tags") or [],
        "seed": payload.get("seed"),
        "target": TARGET_NAME,
    }
    return CommerceInteraction(
        id=UUID(payload["id"]) if "id" in payload else uuid4(),
        offer_id=UUID(payload["offer_id"]) if payload.get("offer_id") else None,
        group_id=payload["group_id"],
        buyer_profile=payload.get("buyer_profile"),
        structured_intent=payload["structured_intent"],
        offer_snapshot=payload["offer_snapshot"],
        features=payload["features"],
        product_fit=str(payload.get("product_fit") or 0),
        total_price_cents=int(payload["total_price_cents"]),
        delivery=payload.get("delivery"),
        warranty=payload.get("warranty"),
        bundle=payload.get("bundle"),
        returns=payload.get("returns"),
        merchant_contribution_cents=int(payload["merchant_contribution_cents"]),
        intervention_cost_cents=int(payload["intervention_cost_cents"]),
        outcome_type=payload["outcome_type"],
        selected=payload.get("selected"),
        accepted=payload.get("accepted"),
        transacted=payload.get("transacted"),
        outcome_source=payload["outcome_source"],
        policy_safe=bool(payload["policy_safe"]),
        hard_constraints_satisfied=bool(payload["hard_constraints_satisfied"]),
        buyer_utility=(
            None
            if payload.get("buyer_utility") is None
            else str(payload["buyer_utility"])
        ),
        observed_at=datetime.fromisoformat(payload["observed_at"]),
        interaction_metadata=meta,
    )


def _as_dict(row: CommerceInteraction) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "group_id": row.group_id,
        "mission_id": row.group_id,
        "offer_id": str(row.offer_id) if row.offer_id else None,
        "buyer_profile": row.buyer_profile,
        "features": row.features,
        "selected": row.selected,
        "policy_safe": row.policy_safe,
        "hard_constraints_satisfied": row.hard_constraints_satisfied,
        "outcome_source": row.outcome_source,
        "outcome_type": row.outcome_type,
        "buyer_utility": float(row.buyer_utility) if row.buyer_utility else 0.0,
        "total_price_cents": row.total_price_cents,
        "offer_snapshot": row.offer_snapshot,
        "structured_intent": row.structured_intent,
        "scenario_tags": row.interaction_metadata.get("scenario_tags") or [],
    }


def _report(
    name: str,
    y: np.ndarray,
    scores: np.ndarray,
    groups: list[str],
) -> dict[str, Any]:
    clf = classification_metrics(y, np.clip(scores, 0.0, 1.0))
    rank = ranking_metrics(y, scores, groups)
    return {
        "name": name,
        "classification": clf,
        "ranking": rank,
        "calibration": calibration_bins(y, np.clip(scores, 0.0, 1.0)),
    }


def _select_candidate(logistic: dict[str, Any], boosting: dict[str, Any]) -> str:
    log_brier = logistic["classification"]["brier"]
    boost_brier = boosting["classification"]["brier"]
    log_top1 = logistic["ranking"]["top1"]
    boost_top1 = boosting["ranking"]["top1"]
    if abs(log_brier - boost_brier) <= 0.01 and abs(log_top1 - boost_top1) <= 0.03:
        return "LOGISTIC_REGRESSION"
    if boost_brier + 0.005 < log_brier and boost_top1 >= log_top1:
        return "GRADIENT_BOOSTING"
    return "LOGISTIC_REGRESSION"


class LearningService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LearningRepository(session)

    async def generate_dataset(
        self,
        *,
        interaction_count_target: int = 5000,
        seed: int = 2026,
        extra_negatives: int = 16,
    ) -> LearningDatasetVersion:
        started = time.perf_counter()
        mission_count = max(16, int(np.ceil(interaction_count_target / 16)))
        missions = generate_missions(mission_count, seed=seed)
        cache = ArenaCatalogueCache()
        payloads: list[dict[str, Any]] = []
        for mission in missions:
            result, extra = await run_mission(
                self.session,
                mission,
                strategies=[
                    "DEFAULT",
                    "ALWAYS_DISCOUNT",
                    "CHEAPEST_ELIGIBLE",
                    "ASTRAOS",
                ],
                outside_option_utility=0.42,
                max_products=8,
                cache=cache,
            )
            rows = interactions_from_arena(
                result, extra["context"], extra_negatives=extra_negatives
            )
            payloads.extend(rows)
        payloads = _diverse_trim(payloads, interaction_count_target)
        violations = leakage_violations(
            payloads[0]["features"].keys() if payloads else []
        )
        if violations:
            raise ValueError(f"Leakage in generated features: {violations}")
        orms = [_orm_from_payload(item) for item in payloads]
        await self.repo.add_interactions(orms)
        positives = sum(1 for item in payloads if item.get("selected"))
        audit = _audit(payloads)
        dataset = LearningDatasetVersion(
            source_types=[OutcomeSource.SIMULATED_ARENA.value],
            seed=seed,
            interaction_count=len(payloads),
            positive_count=positives,
            negative_count=len(payloads) - positives,
            feature_schema_version=FEATURE_SCHEMA_VERSION,
            dataset_metadata={
                "name": DATASET_VERSION_NAME,
                "target": TARGET_NAME,
                "target_definition": TARGET_DEFINITION,
                "disclaimer": LEARNING_DISCLAIMER,
                "interaction_ids": [item["id"] for item in payloads],
                "mission_count": len({item["group_id"] for item in payloads}),
                "audit": audit,
                "leakage_violations": violations,
                "build_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        await self.repo.add_dataset(dataset)
        await self.session.commit()
        await self.session.refresh(dataset)
        return dataset

    async def train(
        self,
        dataset_id: UUID,
        *,
        algorithms: list[str] | None = None,
        seed: int = 2026,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        dataset_row = await self.repo.get_dataset(dataset_id)
        if dataset_row is None:
            raise ValueError("Dataset not found.")
        interactions = await self.repo.interactions_for_dataset(dataset_row)
        built = build_dataset([_as_dict(item) for item in interactions], seed=seed)
        split = grouped_split(built, seed=seed)
        run = ModelTrainingRun(
            dataset_id=dataset_id,
            algorithms=algorithms
            or ["LOGISTIC_REGRESSION", "GRADIENT_BOOSTING"],
            status="RUNNING",
            started_at=datetime.now(UTC),
            completed_at=None,
            error=None,
            results={},
        )
        await self.repo.add_run(run)
        await self.session.flush()

        logistic, best_c = select_logistic_c(
            split.train.X,
            split.train.y,
            split.validation.X,
            split.validation.y,
            random_state=seed,
        )
        boosting = BoostingResponseModel(random_state=seed)
        boosting.fit(split.train.X, split.train.y)

        log_scores = logistic.predict_proba(split.test.X)
        boost_scores = boosting.predict_proba(split.test.X)
        price_scores = PriceHeuristic().predict_score(split.test.X)
        utility_scores = ColdStartUtilityBaseline(
            split.test.utility_scores
        ).predict_score(split.test.X)

        reports = {
            "LOGISTIC_REGRESSION": _report(
                "LOGISTIC_REGRESSION", split.test.y, log_scores, split.test.groups
            ),
            "GRADIENT_BOOSTING": _report(
                "GRADIENT_BOOSTING", split.test.y, boost_scores, split.test.groups
            ),
            "PRICE_HEURISTIC": _report(
                "PRICE_HEURISTIC", split.test.y, price_scores, split.test.groups
            ),
            "COLD_START_UTILITY": _report(
                "COLD_START_UTILITY",
                split.test.y,
                utility_scores,
                split.test.groups,
            ),
        }
        ablations: dict[str, Any] = {}
        for name, keep in ABLATIONS.items():
            ablation_model = LogisticResponseModel(C=best_c, random_state=seed)
            ablation_model.fit(_mask(split.train.X, keep), split.train.y)
            scores = ablation_model.predict_proba(_mask(split.test.X, keep))
            ablations[name] = _report(name, split.test.y, scores, split.test.groups)

        chosen = _select_candidate(
            reports["LOGISTIC_REGRESSION"], reports["GRADIENT_BOOSTING"]
        )
        versions: list[ResponseModelVersion] = []
        fitted: list[tuple[str, LogisticResponseModel | BoostingResponseModel]] = [
            ("LOGISTIC_REGRESSION", logistic),
            ("GRADIENT_BOOSTING", boosting),
        ]
        for algo, trained in fitted:
            if algorithms and algo not in algorithms:
                continue
            model_id = uuid4()
            path, digest = save_artifact(
                model_id,
                {
                    "algorithm": algo,
                    "pipeline": trained.pipeline,
                    "metadata": trained.metadata(),
                    "random_state": seed,
                },
            )
            status = (
                "ACTIVE_EXPERIMENTAL" if algo == chosen else "CANDIDATE"
            )
            extra: dict[str, Any] = {
                "disclaimer": LEARNING_DISCLAIMER,
                "score_label": SCORE_LABEL,
                "selection_reason": (
                    "Preferred when Brier/top-1 are essentially tied; "
                    "logistic wins ties for interpretability."
                    if algo == chosen
                    else "Retained as a candidate."
                ),
            }
            if isinstance(trained, LogisticResponseModel):
                extra["associations"] = trained.coefficient_associations()
            row = ResponseModelVersion(
                id=model_id,
                name=trained.name,
                algorithm=algo,
                version="v1",
                training_data_source="SIMULATED_ARENA",
                training_dataset_version=DATASET_VERSION_NAME,
                feature_schema_version=FEATURE_SCHEMA_VERSION,
                train_size=split.train.size,
                validation_size=split.validation.size,
                test_size=split.test.size,
                parameters=trained.metadata(),
                metrics=reports[algo],
                artifact_path=path,
                artifact_hash=digest,
                status=status,
                training_run_id=run.id,
                dataset_id=dataset_id,
                model_metadata=extra,
            )
            await self.repo.add_model(row)
            versions.append(row)

        hero = _hero_comparison(split, log_scores, utility_scores)
        run.status = "COMPLETED"
        run.completed_at = datetime.now(UTC)
        run.results = {
            "disclaimer": LEARNING_DISCLAIMER,
            "selected_algorithm": chosen,
            "reports": reports,
            "ablations": ablations,
            "hero_mission": hero,
            "timing": {
                "training_ms": round((time.perf_counter() - started) * 1000, 2)
            },
            "split": {
                "train": split.train.size,
                "validation": split.validation.size,
                "test": split.test.size,
                "train_groups": len(set(split.train.groups)),
                "test_groups": len(set(split.test.groups)),
            },
        }
        await self.session.commit()
        return {
            "training_run_id": str(run.id),
            "dataset_id": str(dataset_id),
            "selected_algorithm": chosen,
            "models": [
                {
                    "id": str(item.id),
                    "algorithm": item.algorithm,
                    "status": item.status,
                    "metrics": item.metrics,
                }
                for item in versions
            ],
            "reports": reports,
            "ablations": ablations,
            "hero_mission": hero,
            "disclaimer": LEARNING_DISCLAIMER,
            "results": run.results,
        }

    async def score_offers(
        self,
        model_id: UUID,
        *,
        offers: list[OfferCandidate],
        scored: list[ScoredOffer],
        intent: ShoppingIntent,
        weights: UtilityWeights,
        matches: list[RankedProductMatch],
        buyer_profile: str,
    ) -> list[dict[str, Any]]:
        row = await self.repo.get_model(model_id)
        if row is None:
            raise ValueError("Model not found.")
        artifact = load_artifact(model_id)
        pipeline = artifact["pipeline"]
        match_by = {item.variant_id: item for item in matches}
        offer_by = {item.id: item for item in offers}
        features: list[dict[str, Any]] = []
        keep: list[ScoredOffer] = []
        for item in scored:
            offer = offer_by.get(item.offer_id)
            if offer is None or not item.policy.policy_safe:
                continue
            features.append(
                extract_features(
                    intent=intent,
                    weights=weights,
                    scored=item,
                    offer=offer,
                    match=match_by.get(item.variant_id),
                    buyer_profile=buyer_profile,
                )
            )
            keep.append(item)
        started = time.perf_counter()
        proba = (
            pipeline.predict_proba(features)[:, 1]
            if features
            else np.asarray([], dtype=float)
        )
        _ = (time.perf_counter() - started) * 1000
        return [
            {
                "offer_id": str(item.offer_id),
                "sku": item.sku,
                "synthetic_response_score": float(score),
                "score_label": SCORE_LABEL,
                "disclaimer": LEARNING_DISCLAIMER,
            }
            for item, score in zip(keep, proba, strict=True)
        ]

    async def shadow_scores_for_public(
        self,
        scored: list[ScoredOffer],
        *,
        offers: list[OfferCandidate],
        intent: ShoppingIntent,
        weights: UtilityWeights,
        matches: list[RankedProductMatch],
        buyer_profile: str,
    ) -> dict[str, float]:
        experimental = await self.repo.experimental_model()
        if experimental is None:
            return {}
        rows = await self.score_offers(
            experimental.id,
            offers=offers,
            scored=scored,
            intent=intent,
            weights=weights,
            matches=matches,
            buyer_profile=buyer_profile,
        )
        return {
            item["offer_id"]: float(item["synthetic_response_score"])
            for item in rows
            if "offer_id" in item
        }


def _diverse_trim(
    payloads: list[dict[str, Any]], target: int
) -> list[dict[str, Any]]:
    """Keep mission diversity when truncating to the requested row count."""
    if len(payloads) <= target:
        return payloads
    by_group: dict[str, list[dict[str, Any]]] = {}
    for item in payloads:
        by_group.setdefault(str(item["group_id"]), []).append(item)
    chosen: list[dict[str, Any]] = []
    index = 0
    while len(chosen) < target:
        progressed = False
        for rows in by_group.values():
            if index < len(rows):
                chosen.append(rows[index])
                progressed = True
                if len(chosen) >= target:
                    break
        if not progressed:
            break
        index += 1
    return chosen


def _audit(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    profiles: dict[str, int] = {}
    tags: dict[str, int] = {}
    products: dict[str, int] = {}
    deliveries: dict[str, int] = {}
    for item in payloads:
        profile = item.get("buyer_profile") or "unknown"
        profiles[profile] = profiles.get(profile, 0) + 1
        for tag in item.get("scenario_tags") or []:
            tags[tag] = tags.get(tag, 0) + 1
        snap = item.get("offer_snapshot") or {}
        sku = str(snap.get("sku") or "unknown")
        products[sku] = products.get(sku, 0) + 1
        delivery = str(item.get("delivery") or "unknown")
        deliveries[delivery] = deliveries.get(delivery, 0) + 1
    return {
        "buyer_profiles": profiles,
        "scenario_tags": tags,
        "products": products,
        "deliveries": deliveries,
        "positive_rate": (
            sum(1 for item in payloads if item.get("selected")) / len(payloads)
            if payloads
            else 0.0
        ),
    }


def _hero_comparison(
    split: Any,
    learned: np.ndarray,
    utility: np.ndarray,
) -> dict[str, Any]:
    """Pick one held-out group and show ranks. Actual numbers only."""
    groups = split.test.groups
    if not groups:
        return {}
    target = groups[0]
    idxs = [i for i, group in enumerate(groups) if group == target]
    rows = []
    for i in idxs:
        feat = split.test.X[i]
        rows.append(
            {
                "price_cents": feat.get("total_price_cents"),
                "delivery_days": feat.get("delivery_days"),
                "warranty_months": feat.get("warranty_months"),
                "same_day": feat.get("is_same_day"),
                "cold_start_utility": float(utility[i]),
                "learned_score": float(learned[i]),
                "selected": bool(split.test.y[i]),
            }
        )
    rows.sort(key=lambda item: item["learned_score"], reverse=True)
    return {
        "group_id": target,
        "offers": rows[:6],
        "note": (
            "Held-out synthetic mission. Cold-start utility generated the "
            "labels, so it may rank the selected offer first."
        ),
    }

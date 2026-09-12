"""Synthetic learning APIs. Not a conversion-prediction service."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.decision.intent.models import ShoppingIntent
from app.decision.learning import LEARNING_DISCLAIMER, SCORE_LABEL
from app.decision.offers.models import OfferCandidate
from app.decision.utility.scorer import weights_for
from app.models import LearningDatasetVersion, ResponseModelVersion
from app.schemas.learning import (
    DatasetGenerateRequest,
    DatasetSummary,
    LearningOverview,
    ModelDetail,
    ModelSummary,
    ScoreRequest,
    ScoreResponse,
    TrainRequest,
)
from app.services.learning import LearningService
from app.services.optimisation import OptimisationService

router = APIRouter(prefix="/learning", tags=["learning"])


def _service(db: AsyncSession = Depends(get_db)) -> LearningService:
    return LearningService(db)


def _dataset_summary(row: LearningDatasetVersion) -> DatasetSummary:
    return DatasetSummary(
        dataset_id=row.id,
        seed=row.seed,
        interaction_count=row.interaction_count,
        positive_count=row.positive_count,
        negative_count=row.negative_count,
        feature_schema_version=row.feature_schema_version,
        source_types=list(row.source_types),
        metadata=row.dataset_metadata,
        created_at=row.created_at,
    )


def _model_summary(row: ResponseModelVersion) -> ModelSummary:
    return ModelSummary(
        model_id=row.id,
        name=row.name,
        algorithm=row.algorithm,
        status=row.status,
        training_data_source=row.training_data_source,
        train_size=row.train_size,
        validation_size=row.validation_size,
        test_size=row.test_size,
        metrics=row.metrics,
        created_at=row.created_at,
    )


@router.post("/datasets/generate", response_model=DatasetSummary)
async def generate_dataset(
    payload: DatasetGenerateRequest,
    service: LearningService = Depends(_service),
) -> DatasetSummary:
    row = await service.generate_dataset(
        interaction_count_target=payload.interaction_count_target,
        seed=payload.seed,
    )
    return _dataset_summary(row)


@router.get("/datasets", response_model=list[DatasetSummary])
async def list_datasets(
    service: LearningService = Depends(_service),
) -> list[DatasetSummary]:
    return [_dataset_summary(item) for item in await service.repo.list_datasets()]


@router.get("/datasets/{dataset_id}", response_model=DatasetSummary)
async def get_dataset(
    dataset_id: UUID,
    service: LearningService = Depends(_service),
) -> DatasetSummary:
    row = await service.repo.get_dataset(dataset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return _dataset_summary(row)


@router.post("/train")
async def train_models(
    payload: TrainRequest,
    service: LearningService = Depends(_service),
) -> dict[str, Any]:
    try:
        return await service.train(
            payload.dataset_id, algorithms=payload.algorithms, seed=payload.seed
        )
    except ValueError as exc:
        detail = str(exc)
        status = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status, detail=detail) from exc


@router.get("/models", response_model=list[ModelSummary])
async def list_models(
    service: LearningService = Depends(_service),
) -> list[ModelSummary]:
    return [_model_summary(item) for item in await service.repo.list_models()]


@router.get("/models/{model_id}", response_model=ModelDetail)
async def get_model(
    model_id: UUID,
    service: LearningService = Depends(_service),
) -> ModelDetail:
    row = await service.repo.get_model(model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Model not found.")
    return ModelDetail(
        **_model_summary(row).model_dump(),
        version=row.version,
        feature_schema_version=row.feature_schema_version,
        parameters=row.parameters,
        model_metadata=row.model_metadata,
        artifact_hash=row.artifact_hash,
    )


@router.post("/models/{model_id}/score", response_model=ScoreResponse)
async def score_model(
    model_id: UUID,
    payload: ScoreRequest,
    db: AsyncSession = Depends(get_db),
) -> ScoreResponse:
    optimisation = OptimisationService(db)
    run = await optimisation.get_run(payload.optimisation_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Optimisation run not found.")
    construction = await optimisation.offers.get_run(run.offer_run_id)
    if construction is None:
        raise HTTPException(status_code=404, detail="Offer run not found.")
    rows = await optimisation.offers.list_all(run.offer_run_id)
    offers = [OfferCandidate.model_validate(item.payload) for item in rows]
    for offer, row in zip(offers, rows, strict=True):
        offer.id = row.id
    intent = ShoppingIntent.model_validate(construction.parsed_intent)
    from app.decision.optimisation.engine import score_space
    from app.repositories.policy import MerchantPolicyRepository

    policy = await MerchantPolicyRepository(db).get_active()
    if policy is None:
        raise HTTPException(status_code=400, detail="No merchant policy.")
    variants = {
        item.id: item
        for item in await optimisation.products.list_variants_by_ids(
            list({item.variant_id for item in offers})
        )
    }
    engine = score_space(
        offers,
        intent=intent,
        policy=policy,
        variants=variants,
        product_fits={},
        profile_id=run.buyer_model.profile_id,
    )
    service = LearningService(db)
    try:
        scores = await service.score_offers(
            model_id,
            offers=offers,
            scored=engine.scored,
            intent=intent,
            weights=weights_for(intent, run.buyer_model.profile_id),
            matches=[],
            buyer_profile=run.buyer_model.profile_id,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ScoreResponse(
        model_id=model_id,
        scores=scores,
        disclaimer=LEARNING_DISCLAIMER,
        score_label=SCORE_LABEL,
    )


@router.get("/overview", response_model=LearningOverview)
async def overview(
    service: LearningService = Depends(_service),
) -> LearningOverview:
    dataset = await service.repo.latest_dataset()
    models = await service.repo.list_models()
    samples = await service.repo.sample_interactions(10)
    latest = await service.repo.latest_run()
    associations: list[dict[str, Any]] = []
    for model in models:
        extra = model.model_metadata or {}
        if extra.get("associations"):
            associations = list(extra["associations"])
            break
    latest_train: dict[str, Any] | None = None
    if latest is not None:
        latest_train = {
            "selected": latest.results.get("selected_algorithm"),
            "reports": latest.results.get("reports"),
            "ablations": latest.results.get("ablations"),
            "hero_mission": latest.results.get("hero_mission"),
            "timing": latest.results.get("timing"),
        }
    elif models:
        latest_train = {
            "selected": next(
                (
                    item.algorithm
                    for item in models
                    if item.status == "ACTIVE_EXPERIMENTAL"
                ),
                None,
            )
        }
    return LearningOverview(
        maturity=[
            {"id": "eligibility", "label": "Rule-based eligibility", "state": "ACTIVE"},
            {"id": "semantic", "label": "Semantic matching", "state": "ACTIVE"},
            {
                "id": "utility",
                "label": "Transparent buyer utility",
                "state": "ACTIVE / PRIMARY",
            },
            {
                "id": "learned",
                "label": "Learned response model",
                "state": "EXPERIMENTAL / SYNTHETIC",
            },
            {
                "id": "real",
                "label": "Real observed outcome model",
                "state": "FUTURE",
            },
        ],
        dataset=_dataset_summary(dataset) if dataset else None,
        models=[_model_summary(item) for item in models],
        sample_interactions=[
            {
                "intent": (row.structured_intent or {}).get("raw_text"),
                "profile": row.buyer_profile,
                "price_cents": row.total_price_cents,
                "delivery": row.delivery,
                "warranty": row.warranty,
                "outcome": row.outcome_type,
                "source": row.outcome_source,
            }
            for row in samples
        ],
        latest_training=latest_train,
        associations=associations,
    )

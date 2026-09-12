"""Persistence for interactions, datasets, and model versions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CommerceInteraction,
    LearningDatasetVersion,
    ModelTrainingRun,
    ResponseModelVersion,
)


class LearningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_interactions(
        self, rows: list[CommerceInteraction]
    ) -> None:
        self.session.add_all(rows)
        await self.session.flush()

    async def add_dataset(
        self, row: LearningDatasetVersion
    ) -> LearningDatasetVersion:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_run(self, row: ModelTrainingRun) -> ModelTrainingRun:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_model(self, row: ResponseModelVersion) -> ResponseModelVersion:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_dataset(self, dataset_id: UUID) -> LearningDatasetVersion | None:
        result = await self.session.scalars(
            select(LearningDatasetVersion).where(
                LearningDatasetVersion.id == dataset_id
            )
        )
        return result.one_or_none()

    async def get_model(self, model_id: UUID) -> ResponseModelVersion | None:
        result = await self.session.scalars(
            select(ResponseModelVersion).where(ResponseModelVersion.id == model_id)
        )
        return result.one_or_none()

    async def list_models(self) -> list[ResponseModelVersion]:
        result = await self.session.scalars(
            select(ResponseModelVersion).order_by(ResponseModelVersion.created_at.desc())
        )
        return list(result.all())

    async def list_datasets(self) -> list[LearningDatasetVersion]:
        result = await self.session.scalars(
            select(LearningDatasetVersion).order_by(
                LearningDatasetVersion.created_at.desc()
            )
        )
        return list(result.all())

    async def latest_dataset(self) -> LearningDatasetVersion | None:
        result = await self.session.scalars(
            select(LearningDatasetVersion)
            .order_by(LearningDatasetVersion.created_at.desc())
            .limit(1)
        )
        return result.one_or_none()

    async def experimental_model(self) -> ResponseModelVersion | None:
        result = await self.session.scalars(
            select(ResponseModelVersion)
            .where(ResponseModelVersion.status == "ACTIVE_EXPERIMENTAL")
            .order_by(ResponseModelVersion.created_at.desc())
            .limit(1)
        )
        return result.one_or_none()

    async def interactions_for_dataset(
        self, dataset: LearningDatasetVersion
    ) -> list[CommerceInteraction]:
        raw_ids = list(dataset.dataset_metadata.get("interaction_ids") or [])
        if not raw_ids:
            return []
        ids = [UUID(str(item)) for item in raw_ids]
        result = await self.session.scalars(
            select(CommerceInteraction).where(CommerceInteraction.id.in_(ids))
        )
        return list(result.all())

    async def latest_run(self) -> ModelTrainingRun | None:
        result = await self.session.scalars(
            select(ModelTrainingRun)
            .order_by(ModelTrainingRun.created_at.desc())
            .limit(1)
        )
        return result.one_or_none()

    async def sample_interactions(self, limit: int = 12) -> list[CommerceInteraction]:
        result = await self.session.scalars(
            select(CommerceInteraction)
            .where(CommerceInteraction.policy_safe.is_(True))
            .order_by(CommerceInteraction.created_at.desc())
            .limit(limit)
        )
        return list(result.all())

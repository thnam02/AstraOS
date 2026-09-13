"""Persistence for cached variant embeddings."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VariantEmbedding


class EmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, variant_id: uuid.UUID) -> VariantEmbedding | None:
        result = await self.session.execute(
            select(VariantEmbedding).where(VariantEmbedding.variant_id == variant_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        variant_id: uuid.UUID,
        embedding: list[float],
        embedding_model: str,
        semantic_document_version: str,
        document_hash: str,
    ) -> VariantEmbedding:
        row = await self.get(variant_id)
        if row is None:
            row = VariantEmbedding(
                variant_id=variant_id,
                embedding=embedding,
                embedding_model=embedding_model,
                semantic_document_version=semantic_document_version,
                document_hash=document_hash,
                generated_at=datetime.now(UTC),
            )
            self.session.add(row)
        else:
            row.embedding = embedding
            row.embedding_model = embedding_model
            row.semantic_document_version = semantic_document_version
            row.document_hash = document_hash
            row.generated_at = datetime.now(UTC)
        await self.session.flush()
        return row

    async def list_for_variants(
        self, variant_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, VariantEmbedding]:
        if not variant_ids:
            return {}
        result = await self.session.scalars(
            select(VariantEmbedding).where(VariantEmbedding.variant_id.in_(variant_ids))
        )
        return {row.variant_id: row for row in result.all()}


def is_current(
    row: VariantEmbedding | None,
    *,
    model: str,
    version: str,
    document_hash: str,
    dimensions: int | None = None,
) -> bool:
    if row is None:
        return False
    payload: Any = row.embedding
    if not (
        row.embedding_model == model
        and row.semantic_document_version == version
        and row.document_hash == document_hash
        and isinstance(payload, list)
    ):
        return False
    return not (dimensions is not None and len(payload) != dimensions)

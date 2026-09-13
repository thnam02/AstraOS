"""Selective semantic refresh after catalogue ingestion."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.retrieval.documents import (
    DOCUMENT_VERSION,
    build_product_document,
    document_hash,
)
from app.decision.retrieval.embeddings import resolve_embedding_provider
from app.repositories.embedding import EmbeddingRepository, is_current
from app.repositories.product import ProductRepository


async def refresh_semantic_index(
    session: AsyncSession,
    variant_ids: list[uuid.UUID],
) -> tuple[int, int]:
    """Refresh embeddings only for the supplied variants.

    Inventory-only and price-only callers should pass an empty list.
    """
    if not variant_ids:
        return 0, 0
    resolution = resolve_embedding_provider()
    provider = resolution.provider
    products = ProductRepository(session)
    embeddings = EmbeddingRepository(session)
    loaded = {
        row.id: row for row in await products.list_variants_by_ids(list(variant_ids))
    }
    pending: list[tuple[uuid.UUID, str, str]] = []
    reused = 0
    for variant_id in variant_ids:
        variant = loaded.get(variant_id)
        if variant is None or not variant.is_active:
            continue
        snapshot = variant_to_snapshot(variant)
        document = build_product_document(snapshot)
        digest = document_hash(document)
        existing = await embeddings.get(variant_id)
        if is_current(
            existing,
            model=provider.model_name,
            version=DOCUMENT_VERSION,
            document_hash=digest,
            dimensions=provider.dimensions,
        ):
            reused += 1
            continue
        pending.append((variant_id, document.text, digest))
    if not pending:
        return 0, reused
    encode = getattr(provider, "embed_documents", None)
    texts = [item[1] for item in pending]
    encoded = (
        encode(texts) if callable(encode) else [provider.embed(text) for text in texts]
    )
    refreshed = 0
    for (variant_id, _text, digest), vector in zip(pending, encoded, strict=False):
        await embeddings.upsert(
            variant_id=variant_id,
            embedding=list(vector),
            embedding_model=provider.model_name,
            semantic_document_version=DOCUMENT_VERSION,
            document_hash=digest,
        )
        refreshed += 1
    return refreshed, reused

"""Build or refresh cached product embeddings."""

from __future__ import annotations

import argparse
import asyncio
import time
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.retrieval.documents import (
    DOCUMENT_VERSION,
    build_product_document,
    document_hash,
)
from app.decision.retrieval.embeddings import resolve_embedding_provider
from app.repositories.embedding import EmbeddingRepository, is_current
from app.repositories.product import ProductRepository


async def build_index() -> dict[str, object]:
    resolution = resolve_embedding_provider()
    provider = resolution.provider
    created = 0
    reused = 0
    skipped = 0
    started = time.perf_counter()
    async with AsyncSessionLocal() as session:
        variants = await ProductRepository(session).list_active_variants()
        repo = EmbeddingRepository(session)
        pending: list[tuple[UUID, str, str]] = []
        for variant in variants:
            snapshot = variant_to_snapshot(variant)
            document = build_product_document(snapshot)
            digest = document_hash(document)
            existing = await repo.get(snapshot.variant_id)
            if is_current(
                existing,
                model=provider.model_name,
                version=DOCUMENT_VERSION,
                document_hash=digest,
                dimensions=provider.dimensions,
            ):
                reused += 1
                continue
            pending.append((snapshot.variant_id, document.text, digest))
        encode = getattr(provider, "embed_documents", None)
        texts = [item[1] for item in pending]
        if texts:
            try:
                encoded = (
                    encode(texts)
                    if callable(encode)
                    else [provider.embed(text) for text in texts]
                )
            except Exception:
                skipped = len(pending)
                encoded = []
            for (variant_id, _text, digest), vector in zip(
                pending[: len(encoded)], encoded, strict=False
            ):
                await repo.upsert(
                    variant_id=variant_id,
                    embedding=vector,
                    embedding_model=provider.model_name,
                    semantic_document_version=DOCUMENT_VERSION,
                    document_hash=digest,
                )
                created += 1
        await session.commit()
    duration = time.perf_counter() - started
    total = created + reused
    return {
        "provider_requested": resolution.requested,
        "provider_used": resolution.used,
        "fallback_used": resolution.fallback_used,
        "fallback_reason": resolution.fallback_reason,
        "model": provider.model_name,
        "document_version": DOCUMENT_VERSION,
        "created": created,
        "reused": reused,
        "skipped": skipped,
        "total": total,
        "documents": created + reused + skipped,
        "dimensions": provider.dimensions,
        "duration_s": round(duration, 3),
        "vectors_per_s": round(created / duration, 2) if duration and created else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build product embedding index")
    parser.parse_args()
    summary = asyncio.run(build_index())
    print(f"Embedding provider: {summary['provider_used']}")
    print(f"Requested: {summary['provider_requested']}")
    print(f"Model: {summary['model']}")
    print(f"Dimension: {summary['dimensions']}")
    print(f"Documents: {summary['total']}")
    print(f"Indexed: {summary['created']}")
    print(f"Reused: {summary['reused']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Duration: {summary['duration_s']}s")
    if summary["fallback_used"]:
        print(f"Fallback: {summary['fallback_reason']}")


if __name__ == "__main__":
    main()

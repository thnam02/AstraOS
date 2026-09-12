"""Build or refresh cached product embeddings."""

from __future__ import annotations

import argparse
import asyncio
import hashlib

from app.db.session import AsyncSessionLocal
from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.retrieval.documents import DOCUMENT_VERSION, build_product_document
from app.decision.retrieval.embeddings import default_embedding_provider
from app.repositories.embedding import EmbeddingRepository, is_current
from app.repositories.product import ProductRepository


async def build_index() -> dict[str, int]:
    provider = default_embedding_provider()
    created = 0
    reused = 0
    async with AsyncSessionLocal() as session:
        variants = await ProductRepository(session).list_active_variants()
        repo = EmbeddingRepository(session)
        for variant in variants:
            snapshot = variant_to_snapshot(variant)
            document = build_product_document(snapshot)
            digest = hashlib.sha256(document.text.encode("utf-8")).hexdigest()
            existing = await repo.get(snapshot.variant_id)
            if is_current(
                existing,
                model=provider.model_name,
                version=DOCUMENT_VERSION,
                document_hash=digest,
            ):
                reused += 1
                continue
            await repo.upsert(
                variant_id=snapshot.variant_id,
                embedding=provider.embed(document.text),
                embedding_model=provider.model_name,
                semantic_document_version=DOCUMENT_VERSION,
                document_hash=digest,
            )
            created += 1
        await session.commit()
    return {
        "created": created,
        "reused": reused,
        "total": created + reused,
        "dimensions": provider.dimensions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build product embedding index")
    parser.parse_args()
    summary = asyncio.run(build_index())
    print(
        "Indexed {total} variants ({created} new, {reused} cached), "
        "dim={dimensions}".format(**summary)
    )


if __name__ == "__main__":
    main()

"""Ingestion persistence: idempotency, deactivation, selective reindex."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.retrieval.documents import build_product_document, document_hash
from app.ingestion.service import MerchantIngestionService
from app.models import Product, VariantEmbedding
from app.repositories.product import ProductRepository

EXAMPLE = (
    Path(__file__).resolve().parents[3] / "examples/merchant-data/harbor-sound.json"
)


async def _run(
    session: AsyncSession, payload: bytes, *, dry_run: bool = False
) -> object:
    service = MerchantIngestionService(session)
    return await service.run(
        payload,
        source_type="json",
        source_name="harbor-sound.json",
        dry_run=dry_run,
        initiated_by="test",
        commit=False,
        skip_upload_check=True,
    )


@pytest.mark.asyncio
async def test_dry_run_does_not_persist_products(db_session: AsyncSession) -> None:
    before = await db_session.scalar(
        select(Product).where(Product.external_id == "HS-P-CABIN")
    )
    assert before is None
    result = await _run(db_session, EXAMPLE.read_bytes(), dry_run=True)
    assert result.status == "DRY_RUN"
    assert result.products.created == 14
    after = await db_session.scalar(
        select(Product).where(Product.external_id == "HS-P-CABIN")
    )
    assert after is None


@pytest.mark.asyncio
async def test_apply_then_duplicate_is_idempotent(db_session: AsyncSession) -> None:
    payload = EXAMPLE.read_bytes()
    first = await _run(db_session, payload)
    assert first.status in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
    assert first.products.created == 14
    assert first.variants.created == 15
    second = await _run(db_session, payload)
    assert second.products.created == 0
    assert second.products.updated == 0
    assert second.products.unchanged == 14
    assert second.variants.created == 0
    assert second.variants.updated == 0
    assert second.variants.unchanged == 15


@pytest.mark.asyncio
async def test_changed_record_updates_exactly_one_product(
    db_session: AsyncSession,
) -> None:
    payload = EXAMPLE.read_bytes()
    await _run(db_session, payload)
    raw = json.loads(payload)
    raw["products"][0]["name"] = "Harbor Cabin 12 Revised"
    changed = await _run(db_session, json.dumps(raw).encode())
    assert changed.products.updated == 1
    assert changed.products.created == 0
    assert changed.products.unchanged == 13
    product = (
        await db_session.scalars(
            select(Product).where(Product.external_id == "HS-P-CABIN")
        )
    ).first()
    assert product is not None
    assert product.name == "Harbor Cabin 12 Revised"


@pytest.mark.asyncio
async def test_full_snapshot_deactivates_missing_imported_product(
    db_session: AsyncSession,
) -> None:
    payload = EXAMPLE.read_bytes()
    await _run(db_session, payload)
    raw = json.loads(payload)
    raw["products"] = [
        row for row in raw["products"] if row["external_id"] != "HS-P-DECK"
    ]
    raw["variants"] = [row for row in raw["variants"] if row["sku"] != "HS-DCK-05-SLV"]
    raw["inventory"] = [
        row for row in raw["inventory"] if row["sku"] != "HS-DCK-05-SLV"
    ]
    raw["variant_delivery"] = [
        row for row in raw["variant_delivery"] if row["sku"] != "HS-DCK-05-SLV"
    ]
    raw["variant_warranty"] = [
        row for row in raw["variant_warranty"] if row["sku"] != "HS-DCK-05-SLV"
    ]
    raw["variant_returns"] = [
        row for row in raw["variant_returns"] if row["sku"] != "HS-DCK-05-SLV"
    ]
    raw["variant_bundle"] = [
        row for row in raw.get("variant_bundle", []) if row["sku"] != "HS-DCK-05-SLV"
    ]
    raw["evidence"] = [
        row for row in raw.get("evidence", []) if row["sku"] != "HS-DCK-05-SLV"
    ]
    result = await _run(db_session, json.dumps(raw).encode())
    assert result.products.deactivated >= 1
    deck = (
        await db_session.scalars(
            select(Product).where(Product.external_id == "HS-P-DECK")
        )
    ).first()
    assert deck is not None
    assert deck.is_active is False
    seed = (
        await db_session.scalars(
            select(Product).where(Product.source_system.is_(None)).limit(1)
        )
    ).first()
    assert seed is not None
    assert seed.is_active is True


@pytest.mark.asyncio
async def test_inventory_change_does_not_refresh_embedding(
    db_session: AsyncSession,
) -> None:
    payload = EXAMPLE.read_bytes()
    first = await _run(db_session, payload)
    products = ProductRepository(db_session)
    variant = await products.get_variant_by_sku("HS-CAB-12-BLK")
    assert variant is not None
    digest_before = document_hash(build_product_document(variant_to_snapshot(variant)))
    embedding = (
        await db_session.scalars(
            select(VariantEmbedding).where(VariantEmbedding.variant_id == variant.id)
        )
    ).first()
    assert embedding is not None
    raw = json.loads(payload)
    raw["inventory"][0]["units_available"] = 3
    second = await _run(db_session, json.dumps(raw).encode())
    assert second.inventory.updated == 1
    variant = await products.get_variant_by_sku("HS-CAB-12-BLK")
    assert variant is not None
    digest_after = document_hash(build_product_document(variant_to_snapshot(variant)))
    assert digest_before == digest_after
    assert second.semantic_documents_changed == 0
    assert first.embeddings_refreshed >= 1


@pytest.mark.asyncio
async def test_semantic_name_change_marks_embedding_stale(
    db_session: AsyncSession,
) -> None:
    payload = EXAMPLE.read_bytes()
    await _run(db_session, payload)
    raw = json.loads(payload)
    raw["products"][0]["name"] = "Harbor Cabin Long-Haul"
    result = await _run(db_session, json.dumps(raw).encode())
    assert result.semantic_documents_changed >= 1
    assert result.embeddings_refreshed >= 1


@pytest.mark.asyncio
async def test_price_change_does_not_require_reembed(
    db_session: AsyncSession,
) -> None:
    payload = EXAMPLE.read_bytes()
    await _run(db_session, payload)
    raw = json.loads(payload)
    raw["variants"][0]["price"] = 269
    result = await _run(db_session, json.dumps(raw).encode())
    assert result.variants.updated == 1
    assert result.semantic_documents_changed == 0

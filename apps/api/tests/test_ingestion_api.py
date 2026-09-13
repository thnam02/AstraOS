"""Merchant ingestion API and buyer-agent boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.decision.eligibility.snapshot import variant_to_snapshot
from app.decision.intent.models import IntentStatus, ShoppingIntent
from app.decision.offers.constructor import construct_variant
from app.decision.offers.models import ConstructionLimits
from app.decision.retrieval.documents import build_product_document
from app.ingestion.service import MerchantIngestionService
from app.models import (
    AttributeEvidence,
    MerchantPolicy,
    ProductVariant,
    VariantBundleOption,
    VariantDeliveryOption,
    VariantReturnPolicy,
    VariantWarrantyOption,
)

EXAMPLE = (
    Path(__file__).resolve().parents[3] / "examples/merchant-data/harbor-sound.json"
)


def test_validate_example_json(client: TestClient) -> None:
    raw = json.loads(EXAMPLE.read_text())
    response = client.post(
        "/api/v1/merchant/ingestion/validate",
        json={
            "source_type": "json",
            "source_name": "harbor-sound.json",
            "snapshot": raw,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["status"] == "DRY_RUN"
    assert body["counts"]["products"]["created"] == 14
    assert body["errors"] == []


def test_list_runs_after_validate(client: TestClient) -> None:
    response = client.get("/api/v1/merchant/ingestion/runs")
    assert response.status_code == 200
    assert "items" in response.json()


def test_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/merchant/ingestion/status")
    assert response.status_code == 200
    body = response.json()
    assert body["data_mode"] in {"DEMO_SEED", "IMPORTED", "MIXED"}
    assert body["active_products"] > 0


def test_buyer_agent_cannot_ingest(client: TestClient) -> None:
    raw = json.loads(EXAMPLE.read_text())
    for path in (
        "/api/v1/agent/ingestion/import",
        "/api/v1/agent/merchant/ingestion/import",
        "/api/v1/agent/catalogue/import",
    ):
        response = client.post(path, json={"snapshot": raw})
        assert response.status_code in {404, 405}


def test_ready_accepts_imported_or_seeded_catalogue(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()["checks"]}
    assert "merchant_catalogue" in names
    assert "economics_ready" in names


@pytest.mark.asyncio
async def test_imported_variant_uses_canonical_decision_path(
    db_session: AsyncSession,
) -> None:
    service = MerchantIngestionService(db_session)
    result = await service.run(
        EXAMPLE.read_bytes(),
        source_type="json",
        source_name="harbor-sound.json",
        dry_run=False,
        initiated_by="test",
        commit=False,
        skip_upload_check=True,
    )
    assert result.errors == []
    variant = (
        await db_session.scalars(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product),
                selectinload(ProductVariant.inventory),
                selectinload(ProductVariant.delivery_options).selectinload(
                    VariantDeliveryOption.delivery_option
                ),
                selectinload(ProductVariant.warranty_options).selectinload(
                    VariantWarrantyOption.warranty_option
                ),
                selectinload(ProductVariant.bundle_options).selectinload(
                    VariantBundleOption.bundle_option
                ),
                selectinload(ProductVariant.return_policies).selectinload(
                    VariantReturnPolicy.return_policy
                ),
                selectinload(ProductVariant.evidence).selectinload(
                    AttributeEvidence.source
                ),
            )
            .where(ProductVariant.sku == "HS-CAB-12-BLK")
        )
    ).first()
    assert variant is not None
    snapshot = variant_to_snapshot(variant)
    document = build_product_document(snapshot)
    assert snapshot.sku == "HS-CAB-12-BLK"
    assert snapshot.inventory is not None
    assert snapshot.inventory.sellable_units > 0
    assert "Harbor Cabin 12" in document.text
    policy = (await db_session.scalars(select(MerchantPolicy).limit(1))).first()
    assert policy is not None
    intent = ShoppingIntent(
        raw_text="wireless noise-cancelling headphones under A$350 delivered today",
        parser_type="rule_based",
        parser_version="rule_based.v2",
        status=IntentStatus.READY,
    )
    offers, _counts = construct_variant(
        variant=variant,
        intent=intent,
        policy=policy,
        relevant_bundles=set(),
        limits=ConstructionLimits(),
        expires_at=datetime.now(UTC),
    )
    assert offers

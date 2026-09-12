"""Provenance metadata."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttributeEvidence
from tests.factories import make_product, make_source, make_variant


@pytest.mark.asyncio
async def test_evidence_links_to_variant_and_source(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    source = make_source(source_type="MANUFACTURER")
    evidence = AttributeEvidence(
        variant_id=variant.id,
        attribute_name="anc",
        value=True,
        source_id=source.id,
        verification_status="VERIFIED",
        observed_at=datetime.now(UTC),
    )
    db_session.add_all([product, variant, source, evidence])
    await db_session.flush()
    loaded = await db_session.get(AttributeEvidence, evidence.id)
    assert loaded is not None
    assert loaded.variant_id == variant.id
    assert loaded.source_id == source.id


@pytest.mark.asyncio
async def test_stale_evidence_representable(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    source = make_source()
    expired = datetime.now(UTC) - timedelta(days=10)
    evidence = AttributeEvidence(
        variant_id=variant.id,
        attribute_name="battery_hours",
        value=40,
        source_id=source.id,
        verification_status="UNVERIFIED",
        observed_at=expired,
        expires_at=expired,
    )
    db_session.add_all([product, variant, source, evidence])
    await db_session.flush()
    loaded = await db_session.get(AttributeEvidence, evidence.id)
    assert loaded is not None
    assert loaded.expires_at is not None
    assert loaded.expires_at < datetime.now(UTC)


@pytest.mark.asyncio
async def test_evidence_value_json_types(db_session: AsyncSession) -> None:
    product = make_product()
    variant = make_variant(product.id)
    source = make_source()
    rows = [
        AttributeEvidence(
            variant_id=variant.id,
            attribute_name="anc",
            value=True,
            source_id=source.id,
            verification_status="VERIFIED",
            observed_at=datetime.now(UTC),
        ),
        AttributeEvidence(
            variant_id=variant.id,
            attribute_name="units_available",
            value=14,
            source_id=source.id,
            verification_status="MERCHANT_DECLARED",
            observed_at=datetime.now(UTC),
        ),
        AttributeEvidence(
            variant_id=variant.id,
            attribute_name="notes",
            value={"lab": "SYD", "checked": True},
            source_id=source.id,
            verification_status="SYNTHETIC",
            observed_at=datetime.now(UTC),
        ),
    ]
    db_session.add_all([product, variant, source, *rows])
    await db_session.flush()
    loaded = await db_session.get(AttributeEvidence, rows[2].id)
    assert loaded is not None
    assert loaded.value["lab"] == "SYD"

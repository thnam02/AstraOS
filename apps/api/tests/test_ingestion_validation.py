"""Merchant feed validation and normalisation. No database."""

from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.adapters.csv_adapter import CsvMerchantAdapter, pack_csv_directory
from app.ingestion.adapters.json_adapter import JsonMerchantAdapter
from app.ingestion.constants import SCHEMA_VERSION
from app.ingestion.normalizer import (
    parse_delivery_code,
    parse_money_cents,
    parse_months,
)
from app.ingestion.pipeline import (
    IngestionPayloadError,
    assert_upload_safe,
    prepare_snapshot,
)
from app.ingestion.result import IngestionIssue

EXAMPLE = (
    Path(__file__).resolve().parents[3] / "examples/merchant-data/harbor-sound.json"
)
CSV_DIR = Path(__file__).resolve().parents[3] / "examples/merchant-data/csv"


def _issues(payload: bytes, source: str = "json") -> list[IngestionIssue]:
    _ext, _can, issues, _digest = prepare_snapshot(
        payload, source_type=source, source_name="test.json"
    )
    return issues


def test_valid_json_example() -> None:
    payload = EXAMPLE.read_bytes()
    external, canonical, issues, digest = prepare_snapshot(
        payload, source_type="json", source_name="harbor-sound.json"
    )
    errors = [item for item in issues if item.severity == "ERROR"]
    assert not errors
    assert canonical is not None
    assert canonical.schema_version == SCHEMA_VERSION
    assert len(canonical.products) == 14
    assert len(canonical.variants) == 15
    assert digest


def test_valid_csv_example() -> None:
    payload = pack_csv_directory(CSV_DIR)
    _external, canonical, issues, _digest = prepare_snapshot(
        payload, source_type="csv", source_name="harbor.zip"
    )
    errors = [item for item in issues if item.severity == "ERROR"]
    assert not errors
    assert canonical is not None
    assert len(canonical.products) == 14


def test_invalid_json() -> None:
    try:
        JsonMerchantAdapter().load(b"{not-json", source_name="x.json")
    except ValueError as exc:
        assert "Invalid JSON" in str(exc)
    else:
        raise AssertionError("expected invalid JSON")


def test_unsupported_schema_version() -> None:
    issues = _issues(
        b'{"schema_version":"9.9","merchant":{"currency":"AUD"},"products":[]}'
    )
    assert any(item.code == "unsupported_schema_version" for item in issues)


def test_missing_product_id() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"name": "X", "brand": "Y"}],
        "variants": [],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "missing_product_id" for item in issues)


def test_duplicate_product_id() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [
            {"external_id": "P1", "name": "A", "brand": "B"},
            {"external_id": "P1", "name": "C", "brand": "D"},
        ],
        "variants": [],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "duplicate_external_id" for item in issues)


def test_conflicting_duplicate_rejected() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [
            {
                "sku": "S1",
                "product_external_id": "P1",
                "price": 10,
                "cogs": 4,
                "currency": "AUD",
            },
            {
                "sku": "S1",
                "product_external_id": "P1",
                "price": 20,
                "cogs": 4,
                "currency": "AUD",
            },
        ],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(
        item.code in {"duplicate_external_id", "conflicting_record"} for item in issues
    )


def test_missing_variant_sku() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [{"product_external_id": "P1", "price": 10, "cogs": 4}],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "missing_variant_sku" for item in issues)


def test_orphan_variant() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [
            {
                "sku": "S1",
                "product_external_id": "MISSING",
                "price": 10,
                "cogs": 4,
                "currency": "AUD",
            }
        ],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "orphan_variant" for item in issues)


def test_negative_price() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [
            {
                "sku": "S1",
                "product_external_id": "P1",
                "price": -10,
                "cogs": 4,
                "currency": "AUD",
            }
        ],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code in {"negative_money", "non_positive_price"} for item in issues)


def test_negative_cogs() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [
            {
                "sku": "S1",
                "product_external_id": "P1",
                "price": 10,
                "cogs": -1,
                "currency": "AUD",
            }
        ],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "negative_money" for item in issues)


def test_missing_cogs_is_error() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [
            {"sku": "S1", "product_external_id": "P1", "price": 10, "currency": "AUD"}
        ],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "missing_cogs" for item in issues)


def test_negative_inventory() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "AUD"},
        "products": [{"external_id": "P1", "name": "A", "brand": "B"}],
        "variants": [
            {
                "sku": "S1",
                "product_external_id": "P1",
                "price": 10,
                "cogs": 4,
                "currency": "AUD",
            }
        ],
        "inventory": [{"sku": "S1", "units_available": -2, "warehouse_code": "X"}],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "negative_inventory" for item in issues)


def test_invalid_currency() -> None:
    raw = {
        "schema_version": "1.0",
        "merchant": {"currency": "USD"},
        "products": [],
        "variants": [],
    }
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "invalid_currency" for item in issues)


def test_invalid_bundle_reference() -> None:
    payload = EXAMPLE.read_bytes()
    raw = json.loads(payload)
    raw["variant_bundle"] = [{"sku": "HS-CAB-12-BLK", "code": "NO_SUCH_BUNDLE"}]
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "invalid_bundle_reference" for item in issues)


def test_invalid_evidence_reference() -> None:
    payload = EXAMPLE.read_bytes()
    raw = json.loads(payload)
    raw["evidence"].append(
        {
            "sku": "UNKNOWN-SKU",
            "attribute_name": "anc",
            "value": True,
            "source_type": "MERCHANT_PRODUCT_FEED",
            "verification_status": "MERCHANT_DECLARED",
        }
    )
    issues = _issues(json.dumps(raw).encode())
    assert any(item.code == "orphan_evidence" for item in issues)


def test_stale_evidence_is_allowed() -> None:
    payload = EXAMPLE.read_bytes()
    _external, canonical, issues, _digest = prepare_snapshot(
        payload, source_type="json", source_name="harbor-sound.json"
    )
    assert canonical is not None
    stale = [row for row in canonical.evidence if row.expires_at is not None]
    assert stale
    assert not any(
        item.code == "orphan_evidence" and item.severity == "ERROR" for item in issues
    )


def test_missing_optional_attribute_is_warning_not_invented() -> None:
    payload = EXAMPLE.read_bytes()
    _external, canonical, issues, _digest = prepare_snapshot(
        payload, source_type="json", source_name="harbor-sound.json"
    )
    assert canonical is not None
    mini = next(row for row in canonical.variants if row.sku == "HS-MIN-03-BLK")
    assert "battery_hours" not in mini.attributes
    night = next(row for row in canonical.variants if row.sku == "HS-NGT-14-BLK")
    assert "weight_g" not in night.attributes
    assert any(item.code == "missing_optional_attribute" for item in issues)


def test_normalises_money_weight_warranty_delivery() -> None:
    issues: list[IngestionIssue] = []
    assert (
        parse_money_cents("A$279", field="price", location="x", issues=issues) == 27900
    )
    assert parse_money_cents(229, field="price", location="x", issues=issues) == 22900
    assert parse_months("2 years", location="x", issues=issues) == 24
    assert parse_delivery_code("same-day") == "SAME_DAY"
    assert parse_delivery_code("SAME DAY") == "SAME_DAY"


def test_rejects_pickle_and_oversize() -> None:
    try:
        assert_upload_safe("feed.pkl", b"abc")
    except IngestionPayloadError:
        pass
    else:
        raise AssertionError("pickle should be rejected")
    try:
        assert_upload_safe("feed.json", b"x" * (2 * 1024 * 1024 + 1))
    except IngestionPayloadError:
        pass
    else:
        raise AssertionError("oversize should be rejected")


def test_csv_adapter_rejects_unsafe_zip_name() -> None:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../escape.csv", "a,b\n1,2\n")
    try:
        CsvMerchantAdapter().load(buffer.getvalue(), source_name="bad.zip")
    except ValueError as exc:
        assert "unsafe" in str(exc).lower()
    else:
        raise AssertionError("unsafe zip path should fail")

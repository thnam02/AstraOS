"""JSON merchant-feed adapter."""

from __future__ import annotations

import json
from typing import Any

from app.ingestion.constants import SCHEMA_VERSION, SOURCE_JSON
from app.ingestion.schemas import ExternalMerchantSnapshot


class JsonMerchantAdapter:
    source_type = SOURCE_JSON

    def load(self, payload: bytes, *, source_name: str) -> ExternalMerchantSnapshot:
        try:
            raw = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid JSON merchant feed: {exc}") from exc
        if not isinstance(raw, dict):
            raise ValueError("JSON merchant feed must be an object.")
        return snapshot_from_mapping(
            raw, source_type=SOURCE_JSON, source_name=source_name
        )


def snapshot_from_mapping(
    raw: dict[str, Any],
    *,
    source_type: str,
    source_name: str,
) -> ExternalMerchantSnapshot:
    return ExternalMerchantSnapshot(
        schema_version=str(raw.get("schema_version") or SCHEMA_VERSION),
        source_type=source_type,
        source_name=source_name,
        merchant=dict(raw.get("merchant") or {}),
        products=_rows(raw.get("products")),
        variants=_rows(raw.get("variants")),
        inventory=_rows(raw.get("inventory")),
        delivery_options=_rows(raw.get("delivery_options") or raw.get("delivery")),
        warranties=_rows(raw.get("warranties") or raw.get("warranty_options")),
        bundles=_rows(raw.get("bundles") or raw.get("bundle_options")),
        return_policies=_rows(raw.get("return_policies") or raw.get("returns")),
        variant_delivery=_rows(raw.get("variant_delivery")),
        variant_warranty=_rows(raw.get("variant_warranty")),
        variant_bundle=_rows(raw.get("variant_bundle")),
        variant_returns=_rows(raw.get("variant_returns")),
        evidence=_rows(raw.get("evidence")),
        raw_bytes=b"",
    )


def _rows(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ValueError("Feed collections must be arrays.")
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Feed collection items must be objects.")
        rows.append(item)
    return rows

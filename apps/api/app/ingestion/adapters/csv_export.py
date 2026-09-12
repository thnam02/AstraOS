"""Write a canonical/external snapshot as a CSV bundle."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from app.ingestion.adapters.json_adapter import snapshot_from_mapping
from app.ingestion.schemas import ExternalMerchantSnapshot


def write_csv_bundle(directory: Path, snapshot: ExternalMerchantSnapshot) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if snapshot.merchant:
        _write(directory / "merchant.csv", [snapshot.merchant])
    _write(directory / "products.csv", snapshot.products)
    _write(directory / "variants.csv", snapshot.variants)
    _write(directory / "inventory.csv", snapshot.inventory)
    _write(directory / "delivery.csv", snapshot.delivery_options)
    _write(directory / "warranties.csv", snapshot.warranties)
    _write(directory / "bundles.csv", snapshot.bundles)
    _write(directory / "returns.csv", snapshot.return_policies)
    _write(directory / "variant_delivery.csv", snapshot.variant_delivery)
    _write(directory / "variant_warranty.csv", snapshot.variant_warranty)
    _write(directory / "variant_bundle.csv", snapshot.variant_bundle)
    _write(directory / "variant_returns.csv", snapshot.variant_returns)
    _write(directory / "evidence.csv", snapshot.evidence)


def mapping_to_csv_bundle(directory: Path, raw: dict[str, Any]) -> None:
    snapshot = snapshot_from_mapping(
        raw, source_type="merchant_csv", source_name="export"
    )
    write_csv_bundle(directory, snapshot)


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _cell(row.get(key)) for key in fieldnames})
    path.write_text(buffer.getvalue(), encoding="utf-8")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict | list):
        import json

        return json.dumps(value)
    return str(value)

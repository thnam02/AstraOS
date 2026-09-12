"""CSV / ZIP merchant-feed adapter."""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from typing import Any

from app.ingestion.adapters.json_adapter import snapshot_from_mapping
from app.ingestion.constants import SCHEMA_VERSION, SOURCE_CSV
from app.ingestion.schemas import ExternalMerchantSnapshot

FILE_MAP = {
    "products.csv": "products",
    "variants.csv": "variants",
    "inventory.csv": "inventory",
    "delivery.csv": "delivery_options",
    "warranties.csv": "warranties",
    "bundles.csv": "bundles",
    "returns.csv": "return_policies",
    "variant_delivery.csv": "variant_delivery",
    "variant_warranty.csv": "variant_warranty",
    "variant_bundle.csv": "variant_bundle",
    "variant_returns.csv": "variant_returns",
    "evidence.csv": "evidence",
    "merchant.csv": "merchant_rows",
}


class CsvMerchantAdapter:
    source_type = SOURCE_CSV

    def load(self, payload: bytes, *, source_name: str) -> ExternalMerchantSnapshot:
        files = _split_csv_payload(payload)
        raw: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "merchant": {}}
        merchant_rows = _parse_csv(files.get("merchant.csv", b""))
        if merchant_rows:
            raw["merchant"] = merchant_rows[0]
        for filename, key in FILE_MAP.items():
            if key == "merchant_rows":
                continue
            if filename in files:
                raw[key] = _parse_csv(files[filename])
        snapshot = snapshot_from_mapping(
            raw, source_type=SOURCE_CSV, source_name=source_name
        )
        snapshot.raw_bytes = payload
        return snapshot


def load_csv_directory(
    directory: Path, *, source_name: str
) -> ExternalMerchantSnapshot:
    payload = pack_csv_directory(directory)
    return CsvMerchantAdapter().load(payload, source_name=source_name)


def pack_csv_directory(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in FILE_MAP:
            path = directory / filename
            if path.is_file():
                archive.writestr(filename, path.read_bytes())
    return buffer.getvalue()


def _split_csv_payload(payload: bytes) -> dict[str, bytes]:
    if payload.startswith(b"PK"):
        files: dict[str, bytes] = {}
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for info in archive.infolist():
                name = Path(info.filename).name
                if ".." in info.filename or info.filename.startswith("/"):
                    raise ValueError("CSV archive contains an unsafe path.")
                if info.is_dir():
                    continue
                if not name.endswith(".csv"):
                    raise ValueError(
                        f"CSV archive may only contain .csv files, not {name}."
                    )
                files[name] = archive.read(info)
        return files
    return {"products.csv": payload}


def _parse_csv(payload: bytes) -> list[dict[str, Any]]:
    if not payload.strip():
        return []
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, Any]] = []
    for row in reader:
        cleaned: dict[str, Any] = {}
        for key, value in row.items():
            if key is None:
                continue
            text_value = (value or "").strip()
            cleaned[key.strip()] = _coerce(text_value)
        if any(value not in (None, "") for value in cleaned.values()):
            rows.append(cleaned)
    return rows


def _coerce(value: str) -> Any:
    if value == "":
        return ""
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value

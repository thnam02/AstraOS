"""Adapter contract: read an external merchant snapshot only."""

from __future__ import annotations

from typing import Protocol

from app.ingestion.constants import SOURCE_CSV, SOURCE_JSON
from app.ingestion.schemas import ExternalMerchantSnapshot


class MerchantDataAdapter(Protocol):
    source_type: str

    def load(self, payload: bytes, *, source_name: str) -> ExternalMerchantSnapshot: ...


def load_adapter(source_type: str) -> MerchantDataAdapter:
    from app.ingestion.adapters.csv_adapter import CsvMerchantAdapter
    from app.ingestion.adapters.json_adapter import JsonMerchantAdapter

    key = source_type.strip().lower()
    if key in {SOURCE_JSON, "json"}:
        return JsonMerchantAdapter()
    if key in {SOURCE_CSV, "csv", "zip"}:
        return CsvMerchantAdapter()
    raise ValueError(f"Unsupported merchant source type: {source_type}")

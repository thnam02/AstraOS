"""Merchant feed adapters. Read-only; they do not write SQLAlchemy models."""

from app.ingestion.adapters.csv_adapter import CsvMerchantAdapter
from app.ingestion.adapters.json_adapter import JsonMerchantAdapter
from app.ingestion.adapters.protocol import MerchantDataAdapter, load_adapter

__all__ = [
    "CsvMerchantAdapter",
    "JsonMerchantAdapter",
    "MerchantDataAdapter",
    "load_adapter",
]

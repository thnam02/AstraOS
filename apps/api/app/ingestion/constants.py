"""Ingestion constants. Not commercial policy."""

from __future__ import annotations

import uuid

SCHEMA_VERSION = "1.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})

INGEST_NAMESPACE = uuid.UUID("6b1e0c2a-2026-4f11-8a07-a57a0516feed")

SOURCE_JSON = "merchant_json"
SOURCE_CSV = "merchant_csv"

SOURCE_TYPES = frozenset({SOURCE_JSON, SOURCE_CSV})

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".json", ".csv", ".zip"})

STATUS_PENDING = "PENDING"
STATUS_VALIDATING = "VALIDATING"
STATUS_APPLYING = "APPLYING"
STATUS_REINDEXING = "REINDEXING"
STATUS_DRY_RUN = "DRY_RUN"
STATUS_COMPLETED = "COMPLETED"
STATUS_COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
STATUS_FAILED = "FAILED"

SNAPSHOT_FULL = "FULL"
SNAPSHOT_DELTA = "DELTA"

SCOPE_SOURCE = "source"
SCOPE_MERCHANT = "merchant"

MODE_DEMO_SEED = "DEMO_SEED"
MODE_IMPORTED = "IMPORTED"
MODE_MIXED = "MIXED"

CURRENCY_AUD = "AUD"

DELIVERY_ALIASES = {
    "same_day": "SAME_DAY",
    "sameday": "SAME_DAY",
    "same-day": "SAME_DAY",
    "same day": "SAME_DAY",
    "express": "EXPRESS",
    "next_day": "EXPRESS",
    "next-day": "EXPRESS",
    "next day": "EXPRESS",
    "standard": "STANDARD",
    "std": "STANDARD",
}

VERIFICATION_STATUSES = frozenset(
    {
        "VERIFIED",
        "MERCHANT_DECLARED",
        "UNVERIFIED",
        "UNKNOWN",
        "EXAMPLE_MERCHANT_IMPORT",
    }
)

PROVENANCE_SOURCE_TYPES = {
    "MERCHANT_PRODUCT_FEED",
    "MERCHANT_INVENTORY",
    "FULFILMENT_CONFIGURATION",
    "PRICING_FEED",
    "WARRANTY_POLICY",
    "RETURN_POLICY",
    "EXAMPLE_MERCHANT_IMPORT",
}

SEMANTIC_ATTRIBUTE_KEYS = (
    "anc",
    "battery_hours",
    "weight_g",
    "foldable",
    "wireless",
    "comfort_score",
    "travel_score",
    "microphone",
    "water_resistance",
)

OPTIONAL_VARIANT_WARNINGS = (
    "battery_hours",
    "weight_g",
    "comfort_score",
    "travel_score",
)


def ingest_uuid(*parts: str) -> uuid.UUID:
    return uuid.uuid5(INGEST_NAMESPACE, ":".join(parts))

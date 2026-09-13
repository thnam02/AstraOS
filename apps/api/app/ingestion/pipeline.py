"""Read → validate → normalise. No persistence."""

from __future__ import annotations

from app.ingestion.adapters.protocol import load_adapter
from app.ingestion.constants import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    SCHEMA_VERSION,
)
from app.ingestion.fingerprint import sha256_bytes
from app.ingestion.normalizer import normalize_snapshot
from app.ingestion.result import IngestionIssue
from app.ingestion.schemas import CanonicalMerchantSnapshot, ExternalMerchantSnapshot
from app.ingestion.validator import validate_canonical, validate_external


class IngestionPayloadError(ValueError):
    """Rejected before domain validation."""


def assert_upload_safe(filename: str, payload: bytes) -> None:
    if len(payload) > MAX_UPLOAD_BYTES:
        raise IngestionPayloadError(f"Upload exceeds {MAX_UPLOAD_BYTES} bytes.")
    suffix = ""
    if "." in filename:
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise IngestionPayloadError(
            f"Unsupported file type {suffix or filename}. Use .json, .csv, or .zip."
        )
    pickle_name = filename.lower().endswith((".pkl", ".pickle"))
    if payload.startswith(b"\x80\x04") or pickle_name:
        raise IngestionPayloadError("Python pickle feeds are not supported.")


def prepare_snapshot(
    payload: bytes,
    *,
    source_type: str,
    source_name: str,
) -> tuple[
    ExternalMerchantSnapshot,
    CanonicalMerchantSnapshot | None,
    list[IngestionIssue],
    str,
]:
    digest = sha256_bytes(payload)
    adapter = load_adapter(source_type)
    external = adapter.load(payload, source_name=source_name)
    external.raw_bytes = payload
    issues = validate_external(external)
    if any(
        item.severity == "ERROR" and item.code == "unsupported_schema_version"
        for item in issues
    ):
        return external, None, issues, digest
    canonical, norm_issues = normalize_snapshot(external)
    issues.extend(norm_issues)
    issues.extend(validate_canonical(canonical))
    canonical.schema_version = canonical.schema_version or SCHEMA_VERSION
    return external, canonical, issues, digest

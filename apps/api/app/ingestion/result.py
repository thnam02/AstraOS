"""Ingestion run result DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["ERROR", "WARNING"]


@dataclass(frozen=True)
class IngestionIssue:
    severity: Severity
    code: str
    message: str
    location: str | None = None
    record_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "location": self.location,
            "record_id": self.record_id,
        }


@dataclass
class EntityCounts:
    received: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    rejected: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "received": self.received,
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "deactivated": self.deactivated,
            "rejected": self.rejected,
        }


@dataclass
class IngestionResult:
    status: str
    schema_version: str
    source_type: str
    source_name: str
    file_hash: str | None
    snapshot_mode: str
    dry_run: bool
    merchant_data_mode: str | None = None
    issues: list[IngestionIssue] = field(default_factory=list)
    products: EntityCounts = field(default_factory=EntityCounts)
    variants: EntityCounts = field(default_factory=EntityCounts)
    inventory: EntityCounts = field(default_factory=EntityCounts)
    delivery_options: EntityCounts = field(default_factory=EntityCounts)
    warranty_options: EntityCounts = field(default_factory=EntityCounts)
    bundles: EntityCounts = field(default_factory=EntityCounts)
    return_policies: EntityCounts = field(default_factory=EntityCounts)
    evidence: EntityCounts = field(default_factory=EntityCounts)
    records_received: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_rejected: int = 0
    records_deactivated: int = 0
    semantic_documents_changed: int = 0
    embeddings_refreshed: int = 0
    embeddings_reused: int = 0
    validation_ms: float = 0.0
    apply_ms: float = 0.0
    reindex_ms: float = 0.0
    total_ms: float = 0.0
    economics_ready: bool = True
    economics_reason: str | None = None
    run_id: str | None = None

    @property
    def errors(self) -> list[IngestionIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def warnings(self) -> list[IngestionIssue]:
        return [item for item in self.issues if item.severity == "WARNING"]

    def rollup(self) -> None:
        groups = (
            self.products,
            self.variants,
            self.inventory,
            self.delivery_options,
            self.warranty_options,
            self.bundles,
            self.return_policies,
            self.evidence,
        )
        self.records_received = sum(item.received for item in groups)
        self.records_created = sum(item.created for item in groups)
        self.records_updated = sum(item.updated for item in groups)
        self.records_unchanged = sum(item.unchanged for item in groups)
        self.records_rejected = sum(item.rejected for item in groups)
        self.records_deactivated = sum(item.deactivated for item in groups)

    def as_dict(self) -> dict[str, Any]:
        self.rollup()
        return {
            "status": self.status,
            "schema_version": self.schema_version,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "file_hash": self.file_hash,
            "snapshot_mode": self.snapshot_mode,
            "dry_run": self.dry_run,
            "merchant_data_mode": self.merchant_data_mode,
            "run_id": self.run_id,
            "counts": {
                "products": self.products.as_dict(),
                "variants": self.variants.as_dict(),
                "inventory": self.inventory.as_dict(),
                "delivery_options": self.delivery_options.as_dict(),
                "warranty_options": self.warranty_options.as_dict(),
                "bundles": self.bundles.as_dict(),
                "return_policies": self.return_policies.as_dict(),
                "evidence": self.evidence.as_dict(),
            },
            "records_received": self.records_received,
            "records_created": self.records_created,
            "records_updated": self.records_updated,
            "records_unchanged": self.records_unchanged,
            "records_rejected": self.records_rejected,
            "records_deactivated": self.records_deactivated,
            "warnings": [item.as_dict() for item in self.warnings],
            "errors": [item.as_dict() for item in self.errors],
            "semantic_documents_changed": self.semantic_documents_changed,
            "embeddings_refreshed": self.embeddings_refreshed,
            "embeddings_reused": self.embeddings_reused,
            "timing_ms": {
                "validation": round(self.validation_ms, 3),
                "apply": round(self.apply_ms, 3),
                "reindex": round(self.reindex_ms, 3),
                "total": round(self.total_ms, 3),
            },
            "economics_ready": self.economics_ready,
            "economics_reason": self.economics_reason,
        }

"""Merchant ingestion API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["json", "csv", "merchant_json", "merchant_csv"]
SnapshotMode = Literal["FULL", "DELTA"]
DeactivateScope = Literal["source", "merchant"]


class IngestionRequest(BaseModel):
    source_type: SourceType = "json"
    source_name: str = "merchant-feed.json"
    snapshot_mode: SnapshotMode = "FULL"
    deactivate_scope: DeactivateScope = "source"
    snapshot: dict[str, Any] | None = None
    content_base64: str | None = None
    initiated_by: str = "merchant_api"


class IngestionIssueResponse(BaseModel):
    severity: Literal["ERROR", "WARNING"]
    code: str
    message: str
    location: str | None = None
    record_id: str | None = None


class IngestionCounts(BaseModel):
    received: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deactivated: int = 0
    rejected: int = 0


class IngestionResultResponse(BaseModel):
    status: str
    schema_version: str
    source_type: str
    source_name: str
    file_hash: str | None
    snapshot_mode: str
    dry_run: bool
    merchant_data_mode: str | None = None
    run_id: uuid.UUID | None = None
    counts: dict[str, IngestionCounts]
    records_received: int
    records_created: int
    records_updated: int
    records_unchanged: int
    records_rejected: int
    records_deactivated: int
    warnings: list[IngestionIssueResponse]
    errors: list[IngestionIssueResponse]
    semantic_documents_changed: int
    embeddings_refreshed: int
    embeddings_reused: int
    timing_ms: dict[str, float]
    economics_ready: bool
    economics_reason: str | None = None


class IngestionRunSummary(BaseModel):
    id: uuid.UUID
    source_type: str
    source_name: str
    status: str
    snapshot_mode: str
    file_hash: str | None
    records_created: int
    records_updated: int
    records_unchanged: int
    records_deactivated: int
    warning_count: int
    error_count: int
    index_status: str | None
    started_at: datetime
    completed_at: datetime | None


class IngestionRunDetail(IngestionRunSummary):
    schema_version: str
    initiated_by: str | None
    records_received: int
    records_rejected: int
    semantic_documents_changed: int
    embeddings_refreshed: int
    warnings: list[Any] = Field(default_factory=list)
    errors: list[Any] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class IngestionRunListResponse(BaseModel):
    items: list[IngestionRunSummary]


class MerchantDataStatusResponse(BaseModel):
    data_mode: str
    active_products: int
    active_variants: int
    last_run: IngestionRunSummary | None = None

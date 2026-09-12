"""HTTP schemas for synthetic response-model learning."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.decision.learning import LEARNING_DISCLAIMER


class DatasetGenerateRequest(BaseModel):
    interaction_count_target: int = Field(default=5000, ge=20, le=20000)
    seed: int = 2026


class DatasetSummary(BaseModel):
    dataset_id: UUID
    seed: int
    interaction_count: int
    positive_count: int
    negative_count: int
    feature_schema_version: str
    source_types: list[str]
    metadata: dict[str, Any]
    disclaimer: str = LEARNING_DISCLAIMER
    created_at: datetime


class TrainRequest(BaseModel):
    dataset_id: UUID
    algorithms: list[str] = Field(
        default_factory=lambda: ["LOGISTIC_REGRESSION", "GRADIENT_BOOSTING"]
    )
    seed: int = 2026


class ModelSummary(BaseModel):
    model_id: UUID
    name: str
    algorithm: str
    status: str
    training_data_source: str
    train_size: int
    validation_size: int
    test_size: int
    metrics: dict[str, Any]
    disclaimer: str = LEARNING_DISCLAIMER
    created_at: datetime


class ModelDetail(ModelSummary):
    version: str
    feature_schema_version: str
    parameters: dict[str, Any]
    model_metadata: dict[str, Any]
    artifact_hash: str


class ScoreRequest(BaseModel):
    optimisation_run_id: UUID


class ScoreResponse(BaseModel):
    model_id: UUID
    scores: list[dict[str, Any]]
    disclaimer: str = LEARNING_DISCLAIMER
    score_label: str


class LearningOverview(BaseModel):
    disclaimer: str = LEARNING_DISCLAIMER
    maturity: list[dict[str, str]]
    dataset: DatasetSummary | None
    models: list[ModelSummary]
    sample_interactions: list[dict[str, Any]]
    latest_training: dict[str, Any] | None
    associations: list[dict[str, Any]] = Field(default_factory=list)

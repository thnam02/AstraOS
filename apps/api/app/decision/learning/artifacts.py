"""Local model artifacts. Never unpickle user-supplied bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID

import joblib

from app.config import settings


def artifacts_dir() -> Path:
    root = Path(__file__).resolve().parents[3] / settings.learning_artifacts_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def artifact_path(model_id: UUID) -> Path:
    return artifacts_dir() / f"{model_id}.joblib"


def save_artifact(model_id: UUID, payload: dict[str, Any]) -> tuple[str, str]:
    path = artifact_path(model_id)
    joblib.dump(payload, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path), digest


def load_artifact(model_id: UUID) -> dict[str, Any]:
    path = artifact_path(model_id)
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact missing: {path}")
    loaded = joblib.load(path)
    if not isinstance(loaded, dict):
        raise ValueError("Invalid model artifact.")
    return loaded

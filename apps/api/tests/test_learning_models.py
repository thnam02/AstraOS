"""Logistic and boosting train, bound, and reload."""

from pathlib import Path

import numpy as np

from app.decision.learning.artifacts import load_artifact, save_artifact
from app.decision.learning.models import BoostingResponseModel, LogisticResponseModel
from tests.test_learning_dataset import _row


def _xy(n: int = 40) -> tuple[list[dict], np.ndarray]:
    rows = []
    labels = []
    for idx in range(n):
        selected = idx % 3 == 0
        payload = _row(f"g{idx}", selected, 18000 + idx * 100)
        rows.append(payload["features"])
        labels.append(1 if selected else 0)
    return rows, np.asarray(labels)


def test_logistic_and_boosting_train() -> None:
    X, y = _xy()
    logistic = LogisticResponseModel(C=1.0, random_state=2026)
    logistic.fit(X, y)
    boosting = BoostingResponseModel(random_state=2026, max_iter=40)
    boosting.fit(X, y)
    lp = logistic.predict_proba(X)
    bp = boosting.predict_proba(X)
    assert lp.min() >= 0 and lp.max() <= 1
    assert bp.min() >= 0 and bp.max() <= 1


def test_reload_matches_predictions(tmp_path: Path, monkeypatch) -> None:
    from app.decision.learning import artifacts as artifacts_mod

    monkeypatch.setattr(artifacts_mod, "artifacts_dir", lambda: tmp_path)
    X, y = _xy(24)
    model = LogisticResponseModel(C=0.1, random_state=2026)
    model.fit(X, y)
    first = model.predict_proba(X)
    from uuid import uuid4

    model_id = uuid4()
    save_artifact(model_id, {"pipeline": model.pipeline, "metadata": model.metadata()})
    loaded = load_artifact(model_id)
    second = loaded["pipeline"].predict_proba(X)[:, 1]
    np.testing.assert_allclose(first, second)

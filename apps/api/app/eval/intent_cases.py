"""Load the frozen Phase 2 intent evaluation fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "intent_eval_v1.json"


def load_intent_eval_cases(path: Path | None = None) -> dict[str, Any]:
    payload = json.loads((path or FIXTURE_PATH).read_text())
    if not isinstance(payload, dict) or not payload.get("cases"):
        raise ValueError("Intent evaluation fixture is empty.")
    return payload

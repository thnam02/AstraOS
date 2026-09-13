"""Buyer Agent source must not import AstraOS merchant internals."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN = (
    "app.services",
    "app.decision",
    "app.repositories",
    "app.models",
    "app.db",
    "sqlalchemy",
)

ROOT = Path(__file__).resolve().parents[1] / "buyer_agent"


def test_no_forbidden_imports() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if any(
                    name == item or name.startswith(f"{item}.") for item in FORBIDDEN
                ):
                    offenders.append(f"{path.name}:{name}")
    assert offenders == []

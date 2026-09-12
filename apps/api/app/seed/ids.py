"""Stable identifiers so reseeding upserts instead of duplicating."""

import uuid

ASTRAOS_NAMESPACE = uuid.UUID("a5e7a05e-2026-4000-8000-000000000001")


def stable_uuid(*parts: str) -> uuid.UUID:
    """Return a deterministic UUID5 for a seed entity."""
    return uuid.uuid5(ASTRAOS_NAMESPACE, ":".join(parts))

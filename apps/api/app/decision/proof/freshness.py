"""Central freshness. Not used by React."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.decision.eligibility.snapshot import EvidenceSnapshot
from app.decision.proof.models import FreshnessStatus

# Domain expectations. Product facts are long-lived unless expires_at says otherwise.
_TTL = {
    "units_available": timedelta(hours=48),
    "base_price_cents": timedelta(days=7),
    "same_day": timedelta(hours=24),
}


def freshness_of(
    evidence: EvidenceSnapshot | None,
    *,
    attribute: str | None = None,
    now: datetime | None = None,
) -> FreshnessStatus:
    moment = now or datetime.now(UTC)
    if evidence is None:
        return "UNKNOWN"
    if evidence.expires_at is not None:
        return "STALE" if evidence.is_stale else "CURRENT"
    observed = evidence.observed_at
    if observed is None:
        return "UNKNOWN"
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    ttl = _TTL.get(attribute or evidence.attribute_name)
    if ttl is None:
        return "CURRENT"
    return "CURRENT" if moment - observed <= ttl else "STALE"


def operational_freshness(
    *,
    updated_at: datetime | None,
    attribute: str,
    now: datetime | None = None,
) -> FreshnessStatus:
    moment = now or datetime.now(UTC)
    if updated_at is None:
        return "UNKNOWN"
    stamp = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=UTC)
    ttl = _TTL.get(attribute, timedelta(hours=24))
    return "CURRENT" if moment - stamp <= ttl else "STALE"

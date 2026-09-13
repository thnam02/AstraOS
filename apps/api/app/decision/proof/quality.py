"""Catalogue evidence quality. Operational summary only."""

from __future__ import annotations

from collections import Counter

from app.decision.eligibility.snapshot import EvidenceSnapshot
from app.decision.proof.freshness import freshness_of
from app.decision.proof.models import source_family
from app.models import Product


def catalogue_evidence_quality(products: list[Product]) -> dict[str, object]:
    families: Counter[str] = Counter()
    fresh: Counter[str] = Counter()
    total = 0
    stale = 0
    synthetic = 0
    variant_count = 0
    warranty_configured = 0
    for product in products:
        for variant in product.variants:
            variant_count += 1
            if getattr(variant, "warranty_options", None):
                warranty_configured += 1
            for row in variant.evidence:
                source = row.source
                snap = EvidenceSnapshot(
                    id=str(row.id),
                    attribute_name=row.attribute_name,
                    value=row.value,
                    source_name=source.name if source else "unknown",
                    source_type=source.source_type if source else "unknown",
                    source_reference=row.source_reference,
                    verification_status=row.verification_status,
                    observed_at=row.observed_at,
                    expires_at=row.expires_at,
                )
                family = source_family(snap.source_type, snap.source_name)
                families[family] += 1
                total += 1
                if freshness_of(snap) == "STALE":
                    stale += 1
                else:
                    fresh[family] += 1
                if family == "SYNTHETIC":
                    synthetic += 1
    def pct(part: int, whole: int) -> float:
        return round((part / whole) * 100, 1) if whole else 0.0

    return {
        "evidence_records": total,
        "product_facts_pct": pct(
            families["PRODUCT_FEED"] + families["EXAMPLE_IMPORT"], total
        ),
        "pricing_current_pct": pct(fresh["PRICING"], families["PRICING"] or 1),
        "inventory_current_pct": pct(fresh["INVENTORY"], families["INVENTORY"] or 1),
        "fulfilment_current_pct": pct(fresh["FULFILMENT"], families["FULFILMENT"] or 1),
        "warranty_configured_pct": pct(warranty_configured, variant_count),
        "synthetic_pct": pct(synthetic, total),
        "stale_pct": pct(stale, total),
    }

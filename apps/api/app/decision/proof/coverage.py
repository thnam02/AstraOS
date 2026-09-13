"""Displayed-claim coverage. Separate from ranking evidence_coverage."""

from __future__ import annotations

from app.decision.proof.models import ProofCoverage, ProofItem, source_family


def coverage_of(
    items: list[ProofItem],
    *,
    hard_satisfied: int = 0,
    hard_with_proof: int = 0,
    commercial_terms: int = 0,
    commercial_with_proof: int = 0,
) -> ProofCoverage:
    displayed = [item for item in items if not item.incomplete]
    backed = [
        item
        for item in displayed
        if item.evidence_id or item.derived
    ]
    unsupported = len(displayed) - len(backed)
    rate = (unsupported / len(displayed)) if displayed else 0.0
    return ProofCoverage(
        displayed_claim_count=len(displayed),
        claims_with_evidence=len(backed),
        verified_count=sum(
            1 for item in displayed if item.verification_status == "VERIFIED"
        ),
        unverified_count=sum(
            1 for item in displayed if item.verification_status == "UNVERIFIED"
        ),
        stale_count=sum(
            1 for item in displayed if item.freshness_status == "STALE"
        ),
        conflicted_count=sum(
            1 for item in displayed if item.verification_status == "CONFLICTED"
        ),
        unknown_count=sum(
            1 for item in displayed if item.verification_status == "UNKNOWN"
        ),
        synthetic_count=sum(
            1
            for item in displayed
            if source_family(item.source_type, item.source_name) == "SYNTHETIC"
        ),
        example_import_count=sum(
            1
            for item in displayed
            if source_family(item.source_type, item.source_name) == "EXAMPLE_IMPORT"
        ),
        unsupported_displayed_count=unsupported,
        unsupported_displayed_claim_rate=round(rate, 4),
        hard_constraint_proof_rate=(
            round(hard_with_proof / hard_satisfied, 4) if hard_satisfied else 1.0
        ),
        commercial_term_proof_rate=(
            round(commercial_with_proof / commercial_terms, 4)
            if commercial_terms
            else 1.0
        ),
        match_rationale_proof_rate=round(1.0 - rate, 4) if displayed else 1.0,
    )

"""Attach provenance to match facts after ranking. Scores stay unchanged."""

from __future__ import annotations

from app.decision.eligibility.snapshot import VariantSnapshot
from app.decision.proof.compiler import compile_match_proof
from app.decision.proof.freshness import freshness_of
from app.decision.proof.resolver import resolve_attribute
from app.decision.retrieval.models import MatchFact, RankedProductMatch


def enrich_match(
    snapshot: VariantSnapshot, match: RankedProductMatch
) -> RankedProductMatch:
    bundle = compile_match_proof(snapshot, match)
    by_key = {item.claim_key: item for item in bundle.items}

    def enrich_fact(fact: MatchFact) -> MatchFact:
        item = by_key.get(fact.attribute)
        evidence, verification = resolve_attribute(snapshot, fact.attribute)
        if item is None and evidence is None:
            return fact
        source = item or None
        return fact.model_copy(
            update={
                "evidence_id": (
                    source.evidence_id
                    if source
                    else (evidence.id if evidence else fact.evidence_id)
                ),
                "source_name": (
                    source.source_name
                    if source
                    else (evidence.source_name if evidence else fact.source_name)
                ),
                "source_type": source.source_type if source else (
                    evidence.source_type if evidence else None
                ),
                "source_record_id": (
                    source.source_record_id
                    if source
                    else (evidence.source_reference if evidence else None)
                ),
                "verification_status": (
                    source.verification_status
                    if source
                    else verification
                ),
                "freshness": (
                    source.freshness_status
                    if source
                    else freshness_of(evidence, attribute=fact.attribute)
                ),
                "derived": source.derived if source else False,
                "derivation_rule": source.derivation_rule if source else None,
                "observed_at": source.observed_at if source else (
                    evidence.observed_at if evidence else None
                ),
            }
        )

    reasons = []
    for reason in match.reasons:
        facts = [enrich_fact(fact) for fact in reason.facts]
        reasons.append(reason.model_copy(update={"facts": facts}))
    evidence = [enrich_fact(fact) for fact in match.evidence]
    return match.model_copy(
        update={
            "reasons": reasons,
            "evidence": evidence,
            "proof": [item.model_dump(mode="json") for item in bundle.items],
            "proof_coverage": bundle.coverage.model_dump(),
        }
    )

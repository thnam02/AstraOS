"""Deterministic merchant proof. Does not score, rank, or price."""

from app.decision.proof.compiler import (
    compile_match_proof,
    compile_offer_proof,
)
from app.decision.proof.enrich import enrich_match
from app.decision.proof.models import ProofBundle, ProofCoverage, ProofItem

__all__ = [
    "ProofBundle",
    "ProofCoverage",
    "ProofItem",
    "compile_match_proof",
    "compile_offer_proof",
    "enrich_match",
]

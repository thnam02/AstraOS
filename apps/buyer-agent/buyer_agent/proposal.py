"""Parse public AstraOS proposal payloads. Merchant internals are ignored."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from buyer_agent.models import PublicProposal

PRIVATE_KEYS = {
    "contribution_margin_cents",
    "contribution_margin_rate",
    "cogs",
    "cogs_cents",
    "minimum_margin_rate",
    "alpha",
    "incremental_intervention_cost_cents",
    "utility_trace",
    "merchant_objective",
    "buyer_weight",
    "merchant_weight",
    "objective_comparisons",
}


def contains_private_keys(payload: Any) -> list[str]:
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in PRIVATE_KEYS:
                    found.append(str(key))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def parse_proposal(body: dict[str, Any]) -> PublicProposal:
    proposal = body.get("proposal") or {}
    product = proposal.get("product") or {}
    pricing = proposal.get("pricing") or {}
    total = proposal.get("total") or {}
    delivery = proposal.get("delivery") or {}
    warranty = proposal.get("warranty") or {}
    bundle = proposal.get("bundle") or {}
    amount = total.get("amount_cents")
    if amount is None:
        amount = pricing.get("total_price_cents")
    return PublicProposal(
        proposal_id=_as_str(proposal.get("proposal_id")),
        session_id=_as_str(body.get("negotiation_session_id")),
        status=str(body.get("status") or ""),
        product_name=_as_str(product.get("name")),
        sku=_as_str(product.get("sku")),
        brand=_as_str(product.get("brand")),
        total_cents=int(amount) if isinstance(amount, int) else None,
        currency=str(total.get("currency") or pricing.get("currency") or "AUD"),
        delivery_days=_as_int(delivery.get("days")),
        delivery_name=_as_str(delivery.get("name")),
        warranty_months=_as_int(warranty.get("months")),
        bundle_name=_as_str(bundle.get("name")),
        expiry=_as_str(proposal.get("expiry")),
        allowed_actions=list(body.get("allowed_actions") or []),
        proof=list(body.get("proof") or []),
        raw=body,
    )


def proposal_expired(proposal: PublicProposal, *, now: datetime | None = None) -> bool:
    if not proposal.expiry:
        return False
    stamp = proposal.expiry.replace("Z", "+00:00")
    try:
        expires = datetime.fromisoformat(stamp)
    except ValueError:
        return False
    current = now or datetime.now(UTC)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return current >= expires


def proof_values(proposal: PublicProposal) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in proposal.proof:
        claim = item.get("claim")
        if claim:
            values[str(claim)] = item.get("value")
    return values


def has_claim(proposal: PublicProposal, claim: str, expected: Any = True) -> bool:
    values = proof_values(proposal)
    if claim not in values:
        return False
    return bool(values[claim] == expected)


def _as_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    return None

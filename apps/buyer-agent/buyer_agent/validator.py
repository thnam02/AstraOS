"""Deterministic buyer-side policy. Operates only on mission + public proposal."""

from __future__ import annotations

from buyer_agent.models import (
    BuyerDecision,
    BuyerMission,
    PublicCounter,
    PublicProposal,
)
from buyer_agent.proposal import has_claim, proof_values, proposal_expired


class BuyerPolicyValidator:
    def violations(
        self, mission: BuyerMission, proposal: PublicProposal
    ) -> list[str]:
        notes: list[str] = []
        if proposal_expired(proposal):
            notes.append("expired")
        hard = mission.hard
        if (
            hard.max_total_cents is not None
            and proposal.total_cents is not None
            and proposal.total_cents > hard.max_total_cents
        ):
            notes.append("over_budget")
        if hard.same_day_required:
            days = proposal.delivery_days
            same_day_claim = proof_values(proposal).get("same_day_delivery")
            if same_day_claim is False or (days is not None and days > 0):
                notes.append("same_day_missing")
        if (
            hard.max_delivery_days is not None
            and proposal.delivery_days is not None
            and proposal.delivery_days > hard.max_delivery_days
        ):
            notes.append("delivery_too_slow")
        if hard.require_anc and not (
            has_claim(proposal, "anc", True) or _text_has(proposal, "anc")
        ):
            notes.append("anc_missing")
        if hard.require_wireless and not _text_has(proposal, "wireless"):
            notes.append("wireless_missing")
        brand = (proposal.brand or "").lower()
        if brand and any(item.lower() == brand for item in hard.excluded_brands):
            notes.append("excluded_brand")
        return notes

    def gate(
        self,
        decision: BuyerDecision,
        mission: BuyerMission,
        proposal: PublicProposal,
    ) -> tuple[BuyerDecision, list[str]]:
        notes = self.violations(mission, proposal)
        if decision.action != "ACCEPT":
            return decision, notes
        if not notes:
            return decision, notes
        if "expired" in notes:
            return (
                BuyerDecision(
                    action="REJECT",
                    reason_summary="Proposal expired before acceptance.",
                ),
                notes,
            )
        if mission.max_turns <= 0:
            return (
                BuyerDecision(
                    action="REJECT",
                    reason_summary="Hard buyer requirements are not met.",
                ),
                notes,
            )
        return (
            BuyerDecision(
                action="COUNTER",
                reason_summary="Accept blocked: hard buyer requirements unmet.",
                counter=self.repair_counter(mission, proposal, notes),
            ),
            notes,
        )

    def repair_counter(
        self,
        mission: BuyerMission,
        proposal: PublicProposal,
        notes: list[str],
    ) -> PublicCounter:
        message_parts: list[str] = []
        max_total = None
        delivery_days = None
        if "over_budget" in notes and mission.hard.max_total_cents is not None:
            max_total = mission.hard.max_total_cents
            dollars = mission.hard.max_total_cents / 100
            message_parts.append(f"I need the total at or below A${dollars:.0f}.")
        if "same_day_missing" in notes or "delivery_too_slow" in notes:
            delivery_days = 0 if mission.hard.same_day_required else (
                mission.hard.max_delivery_days
            )
            message_parts.append("I still need the delivery deadline I asked for.")
        if "anc_missing" in notes:
            message_parts.append("Active noise cancellation is still required.")
        if "wireless_missing" in notes:
            message_parts.append("They still need to be wireless.")
        if "excluded_brand" in notes:
            message_parts.append("Please propose a different brand.")
        if not message_parts:
            message_parts.append("The current proposal does not meet my requirements.")
        return PublicCounter(
            max_total_price_cents=max_total,
            requested_delivery_days=delivery_days,
            message=" ".join(message_parts),
        )


_FEATURE_ALIASES = {
    "anc": ("anc", "noise-cancell", "noise cancell", "noise_cancell"),
    "wireless": ("wireless", "bluetooth"),
}


def _text_has(proposal: PublicProposal, needle: str) -> bool:
    blob = " ".join(
        str(item)
        for item in (
            proposal.product_name,
            proposal.sku,
            proposal.raw.get("merchant_reasoning"),
            proposal.raw.get("understood_intent"),
            proposal.proof,
        )
    ).lower()
    aliases = _FEATURE_ALIASES.get(needle.lower(), (needle.lower(),))
    return any(alias in blob for alias in aliases)

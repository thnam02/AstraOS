"""Reproducible buyer. Does not copy AstraOS merchant optimisation."""

from __future__ import annotations

from buyer_agent.models import (
    BuyerDecision,
    BuyerMission,
    PublicCounter,
    PublicProposal,
)
from buyer_agent.proposal import proposal_expired
from buyer_agent.validator import BuyerPolicyValidator


class DeterministicBuyer:
    def __init__(self, validator: BuyerPolicyValidator | None = None) -> None:
        self.validator = validator or BuyerPolicyValidator()

    def decide(
        self,
        mission: BuyerMission,
        proposal: PublicProposal,
        *,
        turns_used: int,
        inspected: bool,
    ) -> BuyerDecision:
        if proposal.status in {"NO_ELIGIBLE_PRODUCT", "NO_POLICY_SAFE_OFFER"}:
            return BuyerDecision(
                action="REJECT",
                reason_summary="Merchant has no safe offer for this mission.",
            )
        if proposal_expired(proposal):
            return BuyerDecision(
                action="REJECT",
                reason_summary="The proposal expired.",
            )
        violations = self.validator.violations(mission, proposal)
        remaining = mission.max_turns - turns_used
        if violations:
            if remaining <= 0:
                return BuyerDecision(
                    action="REJECT",
                    reason_summary="Hard requirements still unmet at max turns.",
                )
            return BuyerDecision(
                action="COUNTER",
                reason_summary="Proposal violates hard buyer requirements.",
                counter=self.validator.repair_counter(mission, proposal, violations),
            )
        score = self.score(mission, proposal)
        if score >= mission.acceptance_threshold:
            return BuyerDecision(
                action="ACCEPT",
                reason_summary=f"Public proposal meets buyer threshold ({score:.2f}).",
            )
        if remaining <= 0:
            return BuyerDecision(
                action="REJECT",
                reason_summary="Threshold not reached and no turns remain.",
            )
        if not inspected:
            return BuyerDecision(
                action="INSPECT",
                reason_summary="Need public proof before conceding or accepting.",
                requested_proof=["delivery", "warranty", "product"],
            )
        return BuyerDecision(
            action="COUNTER",
            reason_summary="Highest-priority preference is still unmet.",
            counter=self._preference_counter(mission, proposal),
        )

    def score(self, mission: BuyerMission, proposal: PublicProposal) -> float:
        score = 0.35
        hard = mission.hard
        if (
            hard.max_total_cents
            and proposal.total_cents is not None
            and proposal.total_cents <= hard.max_total_cents
        ):
            score += 0.25
            room = 1.0 - (proposal.total_cents / hard.max_total_cents)
            if mission.profile.price_sensitivity == "high":
                score += min(0.12, room)
            else:
                score += min(0.06, room / 2)
        if proposal.delivery_days == 0:
            score += 0.18 if mission.profile.urgency == "high" else 0.08
        if (proposal.warranty_months or 0) >= 24:
            score += 0.10 if mission.profile.reliability == "high" else 0.04
        if proposal.bundle_name:
            score += 0.03
        return max(0.0, min(1.0, score))

    def _preference_counter(
        self, mission: BuyerMission, proposal: PublicProposal
    ) -> PublicCounter:
        if (
            mission.profile.price_sensitivity == "high"
            and mission.hard.max_total_cents
            and proposal.total_cents
            and proposal.total_cents > int(mission.hard.max_total_cents * 0.85)
        ):
            target = int(mission.hard.max_total_cents * 0.85)
            return PublicCounter(
                max_total_price_cents=target,
                message=f"Can you get the total closer to A${target / 100:.0f}?",
            )
        months = proposal.warranty_months or 0
        if mission.profile.reliability == "high" and months < 36:
            return PublicCounter(
                requested_warranty_months=36,
                message="I can keep this product if the warranty is extended.",
            )
        if mission.profile.urgency == "high" and proposal.delivery_days != 0:
            return PublicCounter(
                requested_delivery_days=0,
                message="I still need them today.",
            )
        if mission.hard.max_total_cents and proposal.total_cents:
            step = max(500, int(proposal.total_cents * 0.05))
            target = max(
                proposal.total_cents - step,
                int(mission.hard.max_total_cents * 0.7),
            )
            return PublicCounter(
                max_total_price_cents=target,
                message=f"Is a total around A${target / 100:.0f} possible?",
            )
        return PublicCounter(message="Can you improve the commercial terms slightly?")

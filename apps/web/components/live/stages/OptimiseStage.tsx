"use client";

import { useState } from "react";

import { DecisionBridge } from "@/components/live/DecisionBridge";
import { OptimisationPanel } from "@/components/live/OptimisationPanel";
import { WhyDifferentDrawer } from "@/components/live/RecommendedOffer";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { commercialLevers } from "@/lib/decisionNarrative";
import { formatAudCents } from "@/lib/money";
import type {
  BuyerProfile,
  OptimisationResponse,
  PublicScoredOffer,
  RankedProductMatch,
} from "@/types";

export function OptimiseStage({
  optimisation,
  offer,
  topMatch,
  profile,
  busy,
  selectedOfferId,
  onProfile,
  onSelectOffer,
  onContinue,
}: {
  optimisation: OptimisationResponse;
  offer: PublicScoredOffer | null;
  topMatch: RankedProductMatch | null;
  profile: BuyerProfile;
  busy: boolean;
  selectedOfferId: string | null;
  onProfile: (profile: BuyerProfile) => void;
  onSelectOffer: (offerId: string) => void;
  onContinue?: () => void;
}) {
  const [compareOpen, setCompareOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const items = (offer?.proof_bundle?.items ?? []).filter((item) => !item.incomplete);

  if (!offer) {
    return (
      <p className="text-sm text-muted">
        No policy-safe offer was selected for this request.
      </p>
    );
  }

  const levers = commercialLevers(offer);

  return (
    <>
      <StageResult
        label="Recommended commercial response"
        title={offer.product_name}
        value={formatAudCents(offer.pricing.total_price_cents)}
        explanation={
          <ul className="space-y-1">
            {levers.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        }
        metrics={[
          { label: "Buyer utility", value: offer.buyer_utility.toFixed(2) },
          {
            label: "Merchant contribution",
            value: formatAudCents(offer.contribution_margin_cents),
          },
          {
            label: "Product match",
            value: (
              <>
                {Math.round(offer.product_fit * 100)}
                <span className="ml-1 text-sm font-medium text-muted">/ 100</span>
              </>
            ),
          },
        ]}
        emphasis
        actions={
          <>
            <StagePrimaryAction
              label="Continue to negotiation"
              onClick={onContinue}
            />
            <button
              type="button"
              className="btn-quiet"
              onClick={() => setCompareOpen(true)}
            >
              Compare decisions
            </button>
            <button
              type="button"
              className="btn-quiet"
              aria-expanded={detailOpen}
              onClick={() => setDetailOpen((current) => !current)}
            >
              {detailOpen ? "Hide optimisation" : "Inspect optimisation"}
            </button>
          </>
        }
      >
        <ul className="space-y-1.5 text-sm">
          <li className="flex gap-2">
            <span aria-hidden className={offer.policy_safe ? "text-mark" : "text-danger"}>
              {offer.policy_safe ? "✓" : "!"}
            </span>
            <span>
              {offer.policy_safe
                ? "All mandatory requirements satisfied"
                : "Mandatory requirements not fully satisfied"}
            </span>
          </li>
          <li className="flex gap-2">
            <span
              aria-hidden
              className={offer.is_pareto_efficient ? "text-mark" : "text-muted"}
            >
              {offer.is_pareto_efficient ? "✓" : "○"}
            </span>
            <span>
              {offer.is_pareto_efficient
                ? "Pareto-efficient"
                : "Not on the efficient frontier"}
            </span>
          </li>
        </ul>
      </StageResult>

      <StageSection title="Why this response?">
        <DecisionBridge
          topMatch={topMatch}
          optimisation={optimisation}
          offer={offer}
        />
      </StageSection>

      {detailOpen ? (
        <OptimisationPanel
          optimisation={optimisation}
          profile={profile}
          onProfile={onProfile}
          busy={busy}
          showRecommendation={false}
          selectedOfferId={selectedOfferId}
          onSelectOffer={onSelectOffer}
        />
      ) : null}

      <WhyDifferentDrawer
        open={compareOpen}
        offer={offer}
        topMatch={topMatch}
        items={items}
        onClose={() => setCompareOpen(false)}
      />
    </>
  );
}

"use client";

import { useState } from "react";

import { DecisionBridge } from "@/components/live/DecisionBridge";
import { DecisionSummary } from "@/components/live/DecisionSummary";
import { MatchList } from "@/components/live/MatchList";
import { OfferOptimisationSummary } from "@/components/live/OfferOptimisationSummary";
import { WhyDifferentDrawer } from "@/components/live/RecommendedOffer";
import { SelectedOfferSummary } from "@/components/live/SelectedOfferSummary";
import type {
  GenerateOffersResponse,
  MatchResponse,
  OptimisationResponse,
  PublicScoredOffer,
} from "@/types";

export function DecisionHome({
  result,
  offers,
  optimisation,
  offer,
  onInspect,
  onNegotiate,
  onViewConstruct,
  onViewOptimise,
}: {
  result: MatchResponse;
  offers: GenerateOffersResponse | null;
  optimisation: OptimisationResponse | null;
  offer: PublicScoredOffer | null;
  onInspect: () => void;
  onNegotiate?: () => void;
  onViewConstruct?: () => void;
  onViewOptimise?: () => void;
}) {
  const [compareOpen, setCompareOpen] = useState(false);
  const topMatch = result.semantic_matching.matches[0] ?? null;
  const items = (offer?.proof_bundle?.items ?? []).filter((item) => !item.incomplete);

  return (
    <div className="space-y-10">
      {offer ? <DecisionSummary offer={offer} /> : null}
      <div className="lg:hidden">
        {offer ? (
          <div className="border-t border-line pt-6">
            <SelectedOfferSummary
              offer={offer}
              onNegotiate={onNegotiate}
              onInspect={onInspect}
            />
          </div>
        ) : null}
      </div>
      {offer ? (
        <DecisionBridge
          topMatch={topMatch}
          optimisation={optimisation}
          offer={offer}
          construction={offers}
        />
      ) : null}
      <section>
        <p className="eyebrow">Product candidates</p>
        <p className="mt-1 text-sm text-muted">
          Standalone product ranking — not yet a commercial offer.
        </p>
        <div className="mt-3">
          <MatchList matches={result.semantic_matching.matches} />
        </div>
      </section>
      {offers ? (
        <OfferOptimisationSummary
          construction={offers}
          optimisation={optimisation}
          onViewConstruct={onViewConstruct}
          onViewOptimise={onViewOptimise}
        />
      ) : null}
      {offer ? (
        <WhyDifferentDrawer
          open={compareOpen}
          offer={offer}
          topMatch={topMatch}
          items={items}
          onClose={() => setCompareOpen(false)}
        />
      ) : null}
    </div>
  );
}

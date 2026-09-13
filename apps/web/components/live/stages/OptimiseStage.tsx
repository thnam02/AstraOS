"use client";

import { useState } from "react";

import { DecisionBridge } from "@/components/live/DecisionBridge";
import { MetricHint } from "@/components/live/MetricHint";
import { OptimisationPanel } from "@/components/live/OptimisationPanel";
import { WhyDifferentDrawer } from "@/components/live/RecommendedOffer";
import {
  StagePrimaryAction,
  StageResult,
} from "@/components/live/StageShell";
import { METRIC_HELP, commercialLevers } from "@/lib/decisionNarrative";
import { formatAudCents } from "@/lib/money";
import type {
  BuyerProfile,
  GenerateOffersResponse,
  OptimisationResponse,
  PublicScoredOffer,
  RankedProductMatch,
} from "@/types";

export function OptimiseStage({
  optimisation,
  offer,
  topMatch,
  construction,
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
  construction?: GenerateOffersResponse | null;
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
        label="Selected complete offer"
        title={offer.product_name}
        value={formatAudCents(offer.pricing.total_price_cents)}
        explanation={
          <ul className="space-y-1">
            {levers.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        }
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
        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <p className="eyebrow">Complete offer</p>
            <dl className="mt-3 space-y-3">
              <div>
                <dt className="type-small text-muted">
                  <MetricHint
                    label="Simulated buyer utility"
                    hint={METRIC_HELP.buyerUtility}
                  />
                </dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
                  {offer.buyer_utility.toFixed(2)}
                </dd>
              </div>
              <div>
                <dt className="type-small text-muted">
                  <MetricHint
                    label="Merchant contribution"
                    hint={METRIC_HELP.contribution}
                  />
                </dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
                  {formatAudCents(offer.contribution_margin_cents)}
                </dd>
              </div>
            </dl>
          </div>
          <div>
            <p className="eyebrow">Underlying product</p>
            <dl className="mt-3 space-y-3">
              <div>
                <dt className="type-small text-muted">
                  <MetricHint
                    label="Product match"
                    hint={METRIC_HELP.productMatch}
                  />
                </dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
                  {Math.round(offer.product_fit * 100)}
                  <span className="ml-1 text-sm font-medium text-muted">/ 100</span>
                </dd>
              </div>
            </dl>
          </div>
        </div>
        <ul className="mt-5 space-y-1.5 text-sm">
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
              <MetricHint
                label={
                  offer.is_pareto_efficient
                    ? "Pareto-efficient"
                    : "Not on the efficient frontier"
                }
                hint={METRIC_HELP.pareto}
              />
            </span>
          </li>
        </ul>
      </StageResult>

      <DecisionBridge
        topMatch={topMatch}
        optimisation={optimisation}
        offer={offer}
        construction={construction}
      />

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

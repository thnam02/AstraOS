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
import {
  METRIC_HELP,
  commercialLevers,
  completeOfferMandatorySatisfied,
  expansionSteps,
  mandatoryRequirementsCopy,
  noCompliantOfferCopy,
  selectableCompleteOffer,
} from "@/lib/decisionNarrative";
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

  const selected = selectableCompleteOffer(
    offer,
    optimisation,
    construction?.intent,
  );
  if (!selected) {
    const empty = noCompliantOfferCopy(optimisation);
    return (
      <StageResult
        label="No compliant offer"
        title={empty.title}
        explanation={
          <p>
            AstraOS will not select, recommend, or propose a complete offer
            that violates a mandatory buyer constraint.
          </p>
        }
        actions={
          onContinue ? (
            <StagePrimaryAction
              label="Continue to negotiation"
              onClick={onContinue}
            />
          ) : null
        }
      >
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="type-small text-muted">Buyer maximum</dt>
            <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {empty.budget ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="type-small text-muted">Closest safe configuration</dt>
            <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {empty.closest ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="type-small text-muted">Gap</dt>
            <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {empty.gap ?? "—"}
            </dd>
          </div>
        </dl>
        <p className="mt-5 text-sm text-muted">
          Requires buyer relaxation before proposal. The closest configuration
          is a near-miss, not a selected or Pareto-efficient offer.
        </p>
        {construction ? (
          <ol className="mt-5 grid gap-3 sm:grid-cols-2">
            {expansionSteps(construction, optimisation).map((step) => (
              <li key={step.label} className="text-sm">
                <span className="text-muted">{step.label}</span>
                <span className="ml-2 font-mono tabular-nums">{step.value}</span>
              </li>
            ))}
          </ol>
        ) : null}
      </StageResult>
    );
  }

  const items = (selected.proof_bundle?.items ?? []).filter((item) => !item.incomplete);
  const levers = commercialLevers(selected);
  const mandatoryOk = completeOfferMandatorySatisfied(
    selected,
    construction?.intent,
  );

  return (
    <>
      <StageResult
        label="Selected complete offer"
        title={selected.product_name}
        value={formatAudCents(selected.pricing.total_price_cents)}
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
                  {selected.buyer_utility.toFixed(2)}
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
                  {formatAudCents(selected.contribution_margin_cents)}
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
                  {Math.round(selected.product_fit * 100)}
                  <span className="ml-1 text-sm font-medium text-muted">/ 100</span>
                </dd>
              </div>
            </dl>
          </div>
        </div>
        <ul className="mt-5 space-y-1.5 text-sm">
          <li className="flex gap-2">
            <span aria-hidden className={mandatoryOk ? "text-mark" : "text-danger"}>
              {mandatoryOk ? "✓" : "!"}
            </span>
            <span>{mandatoryRequirementsCopy(mandatoryOk)}</span>
          </li>
          <li className="flex gap-2">
            <span
              aria-hidden
              className={selected.is_pareto_efficient ? "text-mark" : "text-muted"}
            >
              {selected.is_pareto_efficient ? "✓" : "○"}
            </span>
            <span>
              <MetricHint
                label={
                  selected.is_pareto_efficient
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
        offer={selected}
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
        offer={selected}
        topMatch={topMatch}
        items={items}
        onClose={() => setCompareOpen(false)}
      />
    </>
  );
}

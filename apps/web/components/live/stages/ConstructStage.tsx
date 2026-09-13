"use client";

import { OfferExplorer } from "@/components/live/OfferExplorer";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { constructStory, expansionSteps } from "@/lib/decisionNarrative";
import type { GenerateOffersResponse, OptimisationResponse } from "@/types";

export function ConstructStage({
  construction,
  optimisation,
  heroProduct,
  onContinue,
}: {
  construction: GenerateOffersResponse;
  optimisation: OptimisationResponse | null;
  heroProduct?: string;
  onContinue?: () => void;
}) {
  const story = constructStory(construction);
  const steps = expansionSteps(construction, optimisation).filter((step) =>
    [
      "Matched products",
      "Candidate offers",
      "Feasible",
      "Buyer-compliant",
      "Policy-safe",
    ].includes(step.label),
  );

  return (
    <>
      <StageResult
        label="Offer space summary"
        title={`${story.products} matched products generated`}
        value={story.generated.toLocaleString()}
        explanation={
          <p>
            AstraOS expanded {story.products} matched products into{" "}
            {story.generated.toLocaleString()} possible commercial configurations.
          </p>
        }
        actions={
          <StagePrimaryAction
            label="Continue to optimisation"
            onClick={onContinue}
          />
        }
      >
        <ol className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {steps.map((step) => (
            <li key={step.label}>
              <p className="type-small text-muted">{step.label}</p>
              <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
                {step.value}
              </p>
            </li>
          ))}
        </ol>
      </StageResult>

      <StageSection title="Commercial dimensions">
        <dl className="max-w-md space-y-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt>Price</dt>
            <dd className="font-mono tabular-nums text-muted">{story.price}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt>Delivery</dt>
            <dd className="font-mono tabular-nums text-muted">{story.delivery}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt>Warranty</dt>
            <dd className="font-mono tabular-nums text-muted">{story.warranty}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt>Bundle</dt>
            <dd className="font-mono tabular-nums text-muted">{story.bundle}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt>Returns</dt>
            <dd className="font-mono tabular-nums text-muted">{story.returns}</dd>
          </div>
        </dl>
      </StageSection>

      <StageSection
        title="Offer explorer"
        description="Feasible configurations only. No offer is recommended here."
        boxed={false}
      >
        <OfferExplorer
          construction={construction}
          heroProduct={heroProduct}
          policySafe={optimisation?.summary.policy_safe}
          pareto={optimisation?.summary.pareto_efficient}
          explorerOnly
        />
      </StageSection>
    </>
  );
}

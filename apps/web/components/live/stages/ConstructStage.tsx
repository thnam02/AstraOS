"use client";

import { AstraPanel } from "@/components/astra";
import { useState } from "react";
import { CommercialDimensionsRadar } from "@/components/live/CommercialDimensionsRadar";
import { OfferExplorer } from "@/components/live/OfferExplorer";
import {
  StagePrimaryAction,
  StageSplit,
  StageSection,
} from "@/components/live/StageShell";
import { constructStory, expansionSteps } from "@/lib/decisionNarrative";
import type {
  GenerateOffersResponse,
  OptimisationResponse,
  PublicOffer,
} from "@/types";

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
  const [configuration, setConfiguration] = useState<PublicOffer | null>(null);
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
    <div className="construct-workspace grid gap-3">
      <StageSplit stretch>
        <AstraPanel
          tone="primary"
          className="flex flex-col justify-between gap-3"
        >
          <div>
            <p className="eyebrow text-mark">Offer space summary</p>
            <div className="mt-2 flex items-baseline justify-between gap-3">
              <h3 className="text-lg font-semibold">
                {story.products} matched products
              </h3>
              <p className="font-mono text-2xl font-semibold">
                {story.generated.toLocaleString()}
              </p>
            </div>
            <p className="text-xs text-muted">
              Possible commercial configurations
            </p>
          </div>
          <ol className="grid grid-cols-3 gap-2 sm:grid-cols-5">
            {steps.map((step) => (
              <li key={step.label}>
                <p className="text-xs text-muted">{step.label}</p>
                <p className="mt-1 font-mono text-lg font-semibold">
                  {step.value}
                </p>
              </li>
            ))}
          </ol>
          <StagePrimaryAction
            label="Continue to optimisation"
            onClick={onContinue}
          />
        </AstraPanel>

        <StageSection title="Commercial dimensions">
          <CommercialDimensionsRadar
            dimensions={construction.dimensions}
            configuration={configuration}
            runId={construction.offer_run_id}
          />
        </StageSection>
      </StageSplit>
      <StageSection title="Offer explorer">
        <OfferExplorer
          construction={construction}
          heroProduct={heroProduct}
          policySafe={optimisation?.summary.policy_safe}
          pareto={optimisation?.summary.pareto_efficient}
          onConfigurationSelect={setConfiguration}
          embedded
          explorerOnly
        />
      </StageSection>
    </div>
  );
}

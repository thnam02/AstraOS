"use client";

import { useState } from "react";

import { OfferExplorer } from "@/components/live/OfferExplorer";
import {
  StagePrimaryAction,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { constructStory } from "@/lib/decisionNarrative";
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
  const [explore, setExplore] = useState(false);
  const story = constructStory(construction);
  const pareto = optimisation?.summary.pareto_efficient;

  return (
    <>
      <StageResult
        label="Offer space created"
        title={`${story.products} matched products generated`}
        value={story.generated.toLocaleString()}
        explanation={
          <p>
            AstraOS expanded {story.products} matched products into{" "}
            {story.generated.toLocaleString()} possible commercial configurations.
          </p>
        }
        actions={
          <>
            <StagePrimaryAction
              label="Continue to optimisation"
              onClick={onContinue}
            />
            <button
              type="button"
              className="btn-quiet"
              aria-expanded={explore}
              onClick={() => setExplore((current) => !current)}
            >
              {explore ? "Hide offer space" : "Explore offer space"}
            </button>
          </>
        }
      >
        <ol className="grid gap-4 sm:grid-cols-3">
          <li>
            <p className="type-small text-muted">Matched products</p>
            <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {story.products}
            </p>
          </li>
          <li>
            <p className="type-small text-muted">Generated offers</p>
            <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {story.generated.toLocaleString()}
            </p>
          </li>
          <li>
            <p className="type-small text-muted">Feasible</p>
            <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {story.feasible.toLocaleString()}
            </p>
            {pareto != null ? (
              <p className="mt-1 text-xs text-muted">
                {pareto} later marked Pareto-efficient
              </p>
            ) : null}
          </li>
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

      {explore ? (
        <OfferExplorer
          construction={construction}
          heroProduct={heroProduct}
          policySafe={optimisation?.summary.policy_safe}
          pareto={pareto}
          explorerOnly
        />
      ) : null}
    </>
  );
}

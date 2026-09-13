import { dimensionLine, expansionSteps } from "@/lib/decisionNarrative";
import type { GenerateOffersResponse, OptimisationResponse } from "@/types";

function numericValue(value: string): number | null {
  const parsed = Number(value.replaceAll(",", ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function Funnel({
  steps,
}: {
  steps: { label: string; value: string }[];
}) {
  return (
    <ol>
      {steps.map((step, index) => {
        const previous = index > 0 ? numericValue(steps[index - 1].value) : null;
        const current = numericValue(step.value);
        const nested =
          previous != null && current != null && current <= previous;
        return (
          <li key={step.label}>
            {index > 0 ? (
              <p className="pl-1 text-muted" aria-hidden>
                {nested ? "↓" : "·"}
              </p>
            ) : null}
            <div className="flex items-baseline justify-between gap-4 py-0.5 text-sm">
              <span>{step.label}</span>
              <span className="font-mono tabular-nums">{step.value}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function OfferOptimisationSummary({
  construction,
  optimisation,
  onViewConstruct,
  onViewOptimise,
}: {
  construction: GenerateOffersResponse;
  optimisation: OptimisationResponse | null;
  onViewConstruct?: () => void;
  onViewOptimise?: () => void;
}) {
  const steps = expansionSteps(construction, optimisation);
  const constructionSteps = steps.filter((step) =>
    ["Matched products", "Candidate offers", "Feasible"].includes(step.label),
  );
  const optimisationSteps = steps.filter(
    (step) => !["Matched products", "Candidate offers", "Feasible"].includes(step.label),
  );
  if (
    optimisation?.summary.offers_considered != null &&
    optimisationSteps[0]?.label !== "Offers considered"
  ) {
    optimisationSteps.unshift({
      label: "Offers scored",
      value: optimisation.summary.offers_considered.toLocaleString(),
    });
  }

  return (
    <section>
      <p className="eyebrow">Offer optimisation</p>
      <div className="mt-4 grid gap-8 sm:grid-cols-2">
        <div>
          <p className="type-small text-muted">Construction</p>
          <p className="mt-1 text-sm text-muted">
            Combinations are generated, then feasibility is applied.
          </p>
          <div className="mt-3">
            <Funnel steps={constructionSteps} />
          </div>
        </div>
        {optimisationSteps.length ? (
          <div>
            <p className="type-small text-muted">Selection</p>
            <p className="mt-1 text-sm text-muted">
              Buyer-safe, feasible, and policy-safe offers enter Pareto.
            </p>
            <div className="mt-3">
              <Funnel steps={optimisationSteps} />
            </div>
          </div>
        ) : null}
      </div>
      <details className="mt-4 group">
        <summary className="btn-quiet cursor-pointer list-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink [&::-webkit-details-marker]:hidden">
          <span className="group-open:hidden">How the offer space was built</span>
          <span className="hidden group-open:inline">Hide offer-space detail</span>
        </summary>
        <p className="mt-3 text-sm text-muted">{dimensionLine(construction)}</p>
      </details>
      <div className="mt-4 flex flex-wrap gap-4">
        {onViewConstruct ? (
          <button type="button" className="btn-quiet" onClick={onViewConstruct}>
            View construction
          </button>
        ) : null}
        {onViewOptimise ? (
          <button type="button" className="btn-quiet" onClick={onViewOptimise}>
            View frontier
          </button>
        ) : null}
      </div>
    </section>
  );
}

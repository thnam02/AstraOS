import { formatAudCents } from "@/lib/money";
import {
  bestPointForProduct,
  commercialLevers,
  dimensionLine,
  expansionSteps,
  offerVsProductCopy,
  productsDiffer,
} from "@/lib/decisionNarrative";
import type {
  GenerateOffersResponse,
  OptimisationResponse,
  PublicScoredOffer,
  RankedProductMatch,
} from "@/types";

export function DecisionBridge({
  topMatch,
  construction,
  optimisation,
  offer,
}: {
  topMatch: RankedProductMatch | null;
  construction: GenerateOffersResponse | null;
  optimisation: OptimisationResponse | null;
  offer: PublicScoredOffer | null;
}) {
  if (!topMatch || !offer) return null;
  const differ = productsDiffer(topMatch, offer);
  const topOffer = bestPointForProduct(optimisation, topMatch);
  const steps = construction ? expansionSteps(construction, optimisation) : [];

  return (
    <section className="space-y-4">
      <div>
        <p className="eyebrow">Product → offer</p>
        <p className="mt-1 text-xs text-muted">
          Product ranking is not the merchant response. The offer is.
        </p>
      </div>

      <div className="grid items-start gap-3 text-sm md:grid-cols-[1fr_auto_1fr]">
        <div>
          <p className="eyebrow">Best product match</p>
          <p className="mt-1 text-base font-semibold">{topMatch.product_name}</p>
          <p
            className="font-mono text-sm tabular-nums"
            title="How strongly the product itself aligns with buyer intent."
          >
            {Math.round(topMatch.overall_semantic_fit * 100)} / 100
          </p>
        </div>
        <p
          className="self-center font-mono text-2xl text-muted"
          aria-label={differ ? "not equal" : "same product"}
        >
          {differ ? "≠" : "="}
        </p>
        <div>
          <p className="eyebrow">Selected commercial offer</p>
          <p className="mt-1 text-base font-semibold">{offer.product_name}</p>
          <p
            className="font-mono text-sm tabular-nums"
            title="Transparent cold-start score for the complete offer."
          >
            {offer.buyer_utility.toFixed(2)} utility ·{" "}
            {formatAudCents(offer.contribution_margin_cents)}
          </p>
        </div>
      </div>

      {construction ? (
        <ol className="space-y-1 text-sm">
          <li className="text-xs text-muted">{dimensionLine(construction)}</li>
          {steps.map((step, index) => (
            <li key={step.label} className="flex items-baseline justify-between gap-3">
              <span className="text-muted">
                {index > 0 ? "↓ " : ""}
                {step.label}
              </span>
              <span className="font-mono tabular-nums">{step.value}</span>
            </li>
          ))}
        </ol>
      ) : null}

      {differ ? (
        <div className="bg-canvas px-4 py-3">
          <p className="eyebrow">Why different?</p>
          <p className="mt-1 text-sm">
            {topMatch.product_name} had the stronger standalone product match.
            {offer.product_name} won as a complete commercial response.
          </p>
          <p className="mt-2 text-xs text-muted">
            Commercial configuration: {commercialLevers(offer).join(" · ")}
          </p>
          {topOffer ? (
            <p className="mt-2 font-mono text-xs tabular-nums text-muted">
              Top-product best offer {topOffer.buyer_utility.toFixed(2)} ·{" "}
              {formatAudCents(topOffer.contribution_margin_cents)} vs selected{" "}
              {offer.buyer_utility.toFixed(2)} ·{" "}
              {formatAudCents(offer.contribution_margin_cents)}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="bg-canvas px-4 py-3">
          <p className="eyebrow">Same product</p>
          <p className="mt-1 text-sm">
            Top product remained the best complete offer. AstraOS still changed
            commercial terms: {commercialLevers(offer).join(" · ")}.
          </p>
        </div>
      )}
      <p className="text-xs text-muted">{offerVsProductCopy(differ)}</p>
    </section>
  );
}

import { formatAudCents } from "@/lib/money";
import {
  bestPointForProduct,
  commercialLevers,
  matchScoreDisplay,
  offerVsProductCopy,
  productsDiffer,
} from "@/lib/decisionNarrative";
import type {
  OptimisationResponse,
  PublicScoredOffer,
  RankedProductMatch,
} from "@/types";

export function DecisionBridge({
  topMatch,
  optimisation,
  offer,
  onCompare,
  onInspect,
}: {
  topMatch: RankedProductMatch | null;
  optimisation: OptimisationResponse | null;
  offer: PublicScoredOffer | null;
  onCompare?: () => void;
  onInspect?: () => void;
}) {
  if (!topMatch || !offer) return null;
  const differ = productsDiffer(topMatch, offer);
  const topOffer = bestPointForProduct(optimisation, topMatch);
  const productScore = matchScoreDisplay(topMatch.overall_semantic_fit);

  return (
    <section>
      <p className="eyebrow">Why this response?</p>
      <div className="mt-3 grid items-start gap-4 text-sm md:grid-cols-[1fr_auto_1fr]">
        <div>
          <p className="type-small text-muted">Best standalone product</p>
          <p className="mt-1 text-base font-semibold">{topMatch.product_name}</p>
          <p className="mt-1 font-mono tabular-nums">
            {productScore.value} {productScore.suffix}
          </p>
        </div>
        <p
          className="self-center font-medium text-muted md:pt-6"
          aria-label={differ ? "not equal" : "same product"}
        >
          {differ ? "≠" : "="}
        </p>
        <div>
          <p className="type-small text-muted">Selected commercial response</p>
          <p className="mt-1 text-base font-semibold">{offer.product_name}</p>
          <p className="mt-1 font-mono tabular-nums">
            {offer.buyer_utility.toFixed(2)} utility
          </p>
        </div>
      </div>

      <div className="mt-5 space-y-3 text-[15px] leading-6">
        {differ ? (
          <>
            <p>
              {topMatch.product_name} is the stronger standalone product.
            </p>
            <p>
              {offer.product_name} produces the stronger complete commercial
              response once delivery, warranty, returns, intervention cost and
              merchant economics are considered.
            </p>
          </>
        ) : (
          <p>
            {topMatch.product_name} remained the strongest product after offer
            optimisation. AstraOS still configured commercial terms:{" "}
            {commercialLevers(offer).join(", ")}.
          </p>
        )}
        <p className="text-sm text-muted">{offerVsProductCopy(differ)}</p>
        {differ && topOffer ? (
          <p className="text-sm text-muted">
            Best offer on {topMatch.product_name}:{" "}
            {topOffer.buyer_utility.toFixed(2)} utility ·{" "}
            {formatAudCents(topOffer.contribution_margin_cents)}. Selected
            response: {offer.buyer_utility.toFixed(2)} utility ·{" "}
            {formatAudCents(offer.contribution_margin_cents)}.
          </p>
        ) : null}
      </div>

      {onCompare || onInspect ? (
        <div className="mt-4 flex flex-wrap gap-4">
          {onCompare ? (
            <button type="button" className="btn-quiet" onClick={onCompare}>
              Compare decisions
            </button>
          ) : null}
          {onInspect ? (
            <button type="button" className="btn-quiet" onClick={onInspect}>
              Inspect evidence
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

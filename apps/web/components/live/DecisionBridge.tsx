import { formatAudCents } from "@/lib/money";
import {
  bestPointForProduct,
  commercialLevers,
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

  return (
    <section className="space-y-3">
      <div className="grid items-center gap-3 text-sm md:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <div>
          <p className="eyebrow">Best product</p>
          <p className="mt-1 text-base font-semibold">{topMatch.product_name}</p>
          <p className="font-mono text-sm tabular-nums">
            {Math.round(topMatch.overall_semantic_fit * 100)} match
          </p>
        </div>
        <p className="font-mono text-lg text-muted" aria-label={differ ? "not equal" : "equals"}>
          {differ ? "≠" : "="}
        </p>
        <div>
          <p className="eyebrow">Offer optimisation</p>
          <p className="mt-1 font-mono text-sm tabular-nums">
            {construction?.input.matched_products ?? "—"} products ·{" "}
            {construction?.summary.generated_candidates.toLocaleString() ?? "—"} configs
          </p>
          <p className="text-xs text-muted">
            {optimisation?.summary.policy_safe.toLocaleString() ?? "—"} policy-safe ·{" "}
            {optimisation?.summary.pareto_efficient ?? "—"} Pareto
          </p>
        </div>
        <p className="text-muted" aria-hidden>
          →
        </p>
        <div>
          <p className="eyebrow">Best offer</p>
          <p className="mt-1 text-base font-semibold">{offer.product_name}</p>
          <p className="font-mono text-sm tabular-nums">
            {offer.buyer_utility.toFixed(2)} buyer utility ·{" "}
            {formatAudCents(offer.contribution_margin_cents)}
          </p>
        </div>
      </div>
      {differ ? (
        <p className="text-sm">Commercial configuration changed the outcome.</p>
      ) : null}

      <p className="text-xs text-muted">{offerVsProductCopy(differ)}</p>

      {differ ? (
        <div className="bg-canvas px-4 py-3">
          <p className="eyebrow">Why a different product?</p>
          <div className="mt-2 grid gap-4 md:grid-cols-2">
            <div>
              <p className="text-sm font-medium">{topMatch.product_name}</p>
              <p className="text-xs text-muted">Best standalone product match</p>
              <p className="mt-1 font-mono text-sm tabular-nums">
                Match {Math.round(topMatch.overall_semantic_fit * 100)} / 100
              </p>
              {topOffer ? (
                <p className="font-mono text-sm tabular-nums">
                  Best offer {topOffer.buyer_utility.toFixed(2)} ·{" "}
                  {formatAudCents(topOffer.contribution_margin_cents)}
                </p>
              ) : null}
            </div>
            <div>
              <p className="text-sm font-medium">{offer.product_name}</p>
              <p className="text-xs text-muted">Strongest complete offer</p>
              <p className="mt-1 font-mono text-sm tabular-nums">
                Product match {Math.round(offer.product_fit * 100)} / 100
              </p>
              <p className="font-mono text-sm tabular-nums">
                Offer fit {offer.buyer_utility.toFixed(2)} ·{" "}
                {formatAudCents(offer.contribution_margin_cents)}
              </p>
              <p className="mt-2 text-xs text-muted">
                {commercialLevers(offer).join(" · ")}
              </p>
            </div>
          </div>
          <p className="mt-3 text-sm">
            {offer.product_name} is not the strongest standalone product match.
            Offer optimisation selected this complete configuration as the
            merchant response
            {topOffer && topOffer.buyer_utility > offer.buyer_utility
              ? ` — a small buyer-utility difference for ${formatAudCents(offer.contribution_margin_cents - topOffer.contribution_margin_cents)} more contribution.`
              : " because its commercial configuration creates the stronger buyer/merchant trade-off."}
          </p>
        </div>
      ) : (
        <p className="text-sm text-muted">
          Top product remained strongest after offer optimisation.
        </p>
      )}
    </section>
  );
}

import { ArrowRight } from "@phosphor-icons/react";

import { formatAudCents } from "@/lib/money";
import type { PublicScoredOffer } from "@/types";

export function SelectedOfferSummary({
  offer,
  onNegotiate,
  onInspect,
}: {
  offer: PublicScoredOffer;
  onNegotiate?: () => void;
  onInspect?: () => void;
}) {
  return (
    <aside className="space-y-5">
      <div>
        <p className="eyebrow">Selected offer</p>
        <h2 className="mt-2 type-section">{offer.product_name}</h2>
        <p className="mt-1 font-mono text-2xl font-semibold tabular-nums">
          {formatAudCents(offer.pricing.total_price_cents)}
        </p>
      </div>
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Buyer utility</dt>
          <dd className="font-mono tabular-nums">
            {offer.buyer_utility.toFixed(2)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Merchant contribution</dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.contribution_margin_cents)}
          </dd>
        </div>
      </dl>
      <ul className="space-y-1.5 text-sm">
        <li className="flex gap-2">
          <span aria-hidden>{offer.policy_safe ? "✓" : "!"}</span>
          <span>
            {offer.policy_safe
              ? "Requirements satisfied"
              : "Requirements not fully satisfied"}
          </span>
        </li>
        <li className="flex gap-2">
          <span aria-hidden>{offer.is_pareto_efficient ? "✓" : "○"}</span>
          <span>
            {offer.is_pareto_efficient
              ? "Pareto-efficient"
              : "Not on the efficient frontier"}
          </span>
        </li>
      </ul>
      {onNegotiate ? (
        <button
          type="button"
          className="btn-primary w-full"
          onClick={onNegotiate}
        >
          Continue to negotiation
          <ArrowRight size={16} weight="bold" aria-hidden />
        </button>
      ) : null}
      {onInspect ? (
        <button type="button" className="btn-quiet" onClick={onInspect}>
          Inspect decision
        </button>
      ) : null}
    </aside>
  );
}

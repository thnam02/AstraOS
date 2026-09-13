import { commercialLevers } from "@/lib/decisionNarrative";
import { formatAudCents } from "@/lib/money";
import type { PublicScoredOffer } from "@/types";

export function DecisionSummary({ offer }: { offer: PublicScoredOffer }) {
  const levers = commercialLevers(offer);
  const mandatory = offer.policy_safe
    ? "All mandatory requirements satisfied"
    : "Mandatory requirements not fully satisfied";
  const pareto = offer.is_pareto_efficient
    ? "Pareto-efficient"
    : "Not on the efficient frontier";

  return (
    <section>
      <p className="eyebrow">Recommended commercial response</p>
      <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 className="type-page">{offer.product_name}</h2>
        <p className="font-mono text-2xl font-semibold tabular-nums">
          {formatAudCents(offer.pricing.total_price_cents)}
        </p>
      </div>
      <ul className="mt-3 space-y-1 text-[15px] leading-6">
        {levers.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <dl className="mt-6 grid gap-4 sm:grid-cols-3">
        <div>
          <dt className="type-small text-muted">Buyer utility</dt>
          <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {offer.buyer_utility.toFixed(2)}
          </dd>
        </div>
        <div>
          <dt className="type-small text-muted">Merchant contribution</dt>
          <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {formatAudCents(offer.contribution_margin_cents)}
          </dd>
        </div>
        <div>
          <dt className="type-small text-muted">Product match</dt>
          <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
            {Math.round(offer.product_fit * 100)}
            <span className="ml-1 text-sm font-medium text-muted">/ 100</span>
          </dd>
        </div>
      </dl>
      <ul className="mt-5 space-y-1.5 text-sm">
        <li className="flex gap-2">
          <span aria-hidden>{offer.policy_safe ? "✓" : "!"}</span>
          <span>{mandatory}</span>
        </li>
        <li className="flex gap-2">
          <span aria-hidden>{offer.is_pareto_efficient ? "✓" : "○"}</span>
          <span>{pareto}</span>
        </li>
      </ul>
    </section>
  );
}

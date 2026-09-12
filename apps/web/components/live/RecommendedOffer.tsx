import { Disclosure } from "@/components/shared/Disclosure";
import { formatAudCents } from "@/lib/money";
import type { PublicScoredOffer } from "@/types";

export function RecommendedOffer({
  offer,
  explanation,
}: {
  offer: PublicScoredOffer;
  explanation: string[];
}) {
  return (
    <article className="space-y-4">
      <div>
        <p className="eyebrow">AstraOS response</p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight">
          {offer.product_name}
        </h2>
        <p className="font-mono text-[11px] text-muted">{offer.sku}</p>
        <p className="mt-2 font-mono text-2xl font-semibold tabular-nums">
          {formatAudCents(offer.pricing.total_price_cents)}
        </p>
        <p className="mt-1 text-sm text-muted">
          {offer.delivery.name} · {offer.warranty.months}-month warranty ·{" "}
          {offer.bundle?.name ?? "No bundle"}
        </p>
      </div>

      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Buyer fit</dt>
          <dd className="font-mono tabular-nums">{offer.buyer_utility.toFixed(2)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Merchant contribution</dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.contribution_margin_cents)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Intervention cost</dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.incremental_intervention_cost_cents)}
          </dd>
        </div>
      </dl>

      {explanation.length ? (
        <div>
          <p className="eyebrow">Why this offer</p>
          <ul className="mt-2 space-y-1.5 text-sm">
            {explanation.map((reason) => (
              <li key={reason} className="flex gap-2">
                <span className="text-success">✓</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {offer.utility_trace.components.length ? (
        <Disclosure title="Inspect proof">
          <ul className="space-y-1 text-xs text-muted">
            {offer.utility_trace.components.map((item) => (
              <li key={item.component}>
                {item.component}: {item.fit.toFixed(2)} × {item.weight.toFixed(2)} ={" "}
                {item.weighted.toFixed(4)}
              </li>
            ))}
            <li>total {offer.utility_trace.total.toFixed(4)}</li>
          </ul>
        </Disclosure>
      ) : null}
    </article>
  );
}

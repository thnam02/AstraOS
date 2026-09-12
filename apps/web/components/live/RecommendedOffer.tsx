import { Disclosure } from "@/components/shared/Disclosure";
import { conciseOfferReasons, commercialLevers } from "@/lib/decisionNarrative";
import { formatAudCents } from "@/lib/money";
import type { PublicScoredOffer } from "@/types";

export function RecommendedOffer({
  offer,
  explanation,
  onWhyDifferent,
}: {
  offer: PublicScoredOffer;
  explanation: string[];
  onWhyDifferent?: () => void;
}) {
  const reasons = conciseOfferReasons(explanation);
  return (
    <article className="space-y-4">
      <div>
        <p className="eyebrow" title="Complete commercial configuration selected by AstraOS.">
          Selected commercial offer
        </p>
        <h2 className="mt-2 text-[22px] font-semibold tracking-tight">
          {offer.product_name}
        </h2>
        <p className="font-mono text-[11px] text-muted">{offer.sku}</p>
        <p className="mt-2 font-mono text-3xl font-semibold tabular-nums">
          {formatAudCents(offer.pricing.total_price_cents)}
        </p>
        <ul className="mt-2 space-y-0.5 text-sm">
          {commercialLevers(offer).map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      <div className="space-y-1 text-sm">
        <p className="text-xs text-muted">Product</p>
        <p>
          {offer.product_name}{" "}
          <span className="font-mono tabular-nums text-muted">
            match {Math.round(offer.product_fit * 100)} / 100
          </span>
        </p>
        <p className="pt-2 text-xs text-muted">Commercial enhancements</p>
        <p>{commercialLevers(offer).join(" · ")}</p>
      </div>

      <dl className="space-y-2">
        <div>
          <dt
            className="eyebrow"
            title="Transparent cold-start score for the complete offer configuration."
          >
            Simulated buyer utility
          </dt>
          <dd className="font-mono text-3xl font-semibold tabular-nums">
            {offer.buyer_utility.toFixed(2)}
          </dd>
          <p className="text-[11px] text-muted">Cold-start score — not purchase probability.</p>
        </div>
        <div className="flex justify-between gap-3 text-sm">
          <dt
            className="text-muted"
            title="Estimated contribution from the complete commercial offer."
          >
            Merchant contribution
          </dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.contribution_margin_cents)}
          </dd>
        </div>
        <div className="flex justify-between gap-3 text-sm">
          <dt className="text-muted">Intervention cost</dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(offer.incremental_intervention_cost_cents)}
          </dd>
        </div>
      </dl>

      {reasons.length ? (
        <div>
          <p className="eyebrow">Why this offer</p>
          <ul className="mt-2 space-y-1 text-sm">
            {reasons.map((reason) => (
              <li key={reason} className="flex gap-2">
                <span className="text-success">✓</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3">
        {onWhyDifferent ? (
          <button type="button" className="btn-quiet" onClick={onWhyDifferent}>
            Why this product instead of #1?
          </button>
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
      </div>
    </article>
  );
}

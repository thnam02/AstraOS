import { StageResult } from "@/components/live/StageShell";
import { commercialLevers } from "@/lib/decisionNarrative";
import { formatAudCents } from "@/lib/money";
import type { PublicScoredOffer } from "@/types";

export function DecisionSummary({
  offer,
  hideEyebrow = false,
}: {
  offer: PublicScoredOffer;
  hideEyebrow?: boolean;
}) {
  const levers = commercialLevers(offer);

  return (
    <StageResult
      label={hideEyebrow ? "Selected offer" : "Recommended commercial response"}
      title={offer.product_name}
      value={formatAudCents(offer.pricing.total_price_cents)}
      explanation={
        <ul className="space-y-1">
          {levers.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      }
      metrics={[
        { label: "Buyer utility", value: offer.buyer_utility.toFixed(2) },
        {
          label: "Merchant contribution",
          value: formatAudCents(offer.contribution_margin_cents),
        },
        {
          label: "Product match",
          value: (
            <>
              {Math.round(offer.product_fit * 100)}
              <span className="ml-1 text-sm font-medium text-muted">/ 100</span>
            </>
          ),
        },
      ]}
    >
      <ul className="space-y-1.5 text-sm">
        <li className="flex gap-2">
          <span aria-hidden className={offer.policy_safe ? "text-mark" : "text-danger"}>
            {offer.policy_safe ? "✓" : "!"}
          </span>
          <span>
            {offer.policy_safe
              ? "All mandatory requirements satisfied"
              : "Mandatory requirements not fully satisfied"}
          </span>
        </li>
        <li className="flex gap-2">
          <span
            aria-hidden
            className={offer.is_pareto_efficient ? "text-mark" : "text-muted"}
          >
            {offer.is_pareto_efficient ? "✓" : "○"}
          </span>
          <span>
            {offer.is_pareto_efficient
              ? "Pareto-efficient"
              : "Not on the efficient frontier"}
          </span>
        </li>
      </ul>
    </StageResult>
  );
}

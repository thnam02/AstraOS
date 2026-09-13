import { StageResult } from "@/components/live/StageShell";
import {
  commercialLevers,
  completeOfferMandatorySatisfied,
  mandatoryRequirementsCopy,
} from "@/lib/decisionNarrative";
import { formatAudCents } from "@/lib/money";
import type { PublicScoredOffer, ShoppingIntent } from "@/types";

export function DecisionSummary({
  offer,
  intent,
  hideEyebrow = false,
}: {
  offer: PublicScoredOffer;
  intent?: ShoppingIntent | null;
  hideEyebrow?: boolean;
}) {
  const levers = commercialLevers(offer);
  const mandatoryOk = completeOfferMandatorySatisfied(offer, intent);

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
          <span aria-hidden className={mandatoryOk ? "text-mark" : "text-danger"}>
            {mandatoryOk ? "✓" : "!"}
          </span>
          <span>{mandatoryRequirementsCopy(mandatoryOk)}</span>
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

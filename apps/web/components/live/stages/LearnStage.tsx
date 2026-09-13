import Link from "next/link";

import { LIVE_STAGES } from "@/components/live/ProcessRail";
import { StageResult, StageSection } from "@/components/live/StageShell";
import { STAGE_META } from "@/lib/liveStages";
import { formatAudCents } from "@/lib/money";
import type { AcceptProposalResponse, NegotiationResponse } from "@/types";

function outcomeCopy(
  confirmed: boolean,
  transaction: AcceptProposalResponse | null,
): { title: string; explanation: string } {
  if (confirmed) {
    return {
      title: "Offer accepted",
      explanation:
        "The buyer accepted the merchant proposal and the transaction completed.",
    };
  }
  if (transaction) {
    return {
      title: "Transaction did not complete",
      explanation:
        "A proposal was accepted but the transaction did not confirm. Calibration and model status live in LEARN.",
    };
  }
  return {
    title: "No transaction recorded yet",
    explanation:
      "A merchant response exists. This page only reports what this decision run actually produced.",
  };
}

export function LearnStage({
  negotiation,
  transaction,
}: {
  negotiation: NegotiationResponse | null;
  transaction: AcceptProposalResponse | null;
}) {
  const offer = negotiation?.proposal?.offer;
  const confirmed = transaction?.state === "CONFIRMED";
  const outcome = outcomeCopy(confirmed, transaction);

  return (
    <>
      <StageResult
        label="Outcome"
        title={outcome.title}
        explanation={<p>{outcome.explanation}</p>}
        metrics={
          offer
            ? [
                { label: "Final utility", value: offer.buyer_utility.toFixed(2) },
                {
                  label: "Merchant contribution",
                  value: formatAudCents(offer.contribution_margin_cents),
                },
                {
                  label: "Negotiation",
                  value: negotiation?.state.replaceAll("_", " ") ?? "—",
                },
              ]
            : undefined
        }
        actions={
          <Link href="/learn" className="btn-quiet">
            Open LEARN
          </Link>
        }
      >
        {offer ? (
          <p className="text-sm">
            {offer.product_name}
            <span className="mx-2 text-muted">·</span>
            <span className="font-mono tabular-nums">
              {formatAudCents(offer.pricing.total_price_cents)}
            </span>
          </p>
        ) : null}
      </StageResult>

      <StageSection
        title="What happened"
        description="A compact trace of this decision run. No fabricated learning metrics."
      >
        <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
          {LIVE_STAGES.filter((id) => id !== "learn").map((id, index) => (
            <li key={id} className="flex items-center gap-2">
              {index > 0 ? (
                <span className="text-muted" aria-hidden>
                  →
                </span>
              ) : null}
              <span>
                {STAGE_META[id].number} {STAGE_META[id].title}
              </span>
            </li>
          ))}
        </ol>
      </StageSection>
    </>
  );
}

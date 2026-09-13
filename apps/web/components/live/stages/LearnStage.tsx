import Link from "next/link";

import { AstraDataTable, AstraStatusBadge, type AstraTone } from "@/components/astra";
import { LIVE_STAGES } from "@/components/live/ProcessRail";
import { StageResult, StageSection } from "@/components/live/StageShell";
import { LEARN_STATUS } from "@/lib/decisionNarrative";
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

function statusTone(state: string): AstraTone {
  if (state === "ACTIVE" || state === "PRIMARY") return "positive";
  if (state === "EXPERIMENTAL") return "warning";
  return "neutral";
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
        label="Outcome record"
        title={outcome.title}
        explanation={<p>{outcome.explanation}</p>}
        actions={
          <Link href="/learn" className="btn-quiet">
            Open LEARN
          </Link>
        }
      >
        {offer ? (
          <dl className="max-w-md space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Product</dt>
              <dd>{offer.product_name}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Final price</dt>
              <dd className="font-mono tabular-nums">
                {formatAudCents(offer.pricing.total_price_cents)}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Final utility</dt>
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
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Negotiation</dt>
              <dd>{negotiation?.state.replaceAll("_", " ") ?? "—"}</dd>
            </div>
          </dl>
        ) : null}
      </StageResult>

      <StageSection title="Learning status">
        <AstraDataTable bordered={false}>
          <thead>
            <tr>
              <th>Capability</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {LEARN_STATUS.map((item) => (
              <tr key={item.label}>
                <td>{item.label}</td>
                <td>
                  <AstraStatusBadge tone={statusTone(item.state)}>
                    {item.state}
                  </AstraStatusBadge>
                </td>
              </tr>
            ))}
          </tbody>
        </AstraDataTable>
        <p className="mt-3 text-sm text-muted">
          LIVE uses transparent cold-start scoring. The learned response model is
          experimental. A real observed-data model is future work.
        </p>
      </StageSection>

      <StageSection
        title="Model / evaluation"
        description="Trace of this decision run. No fabricated learning metrics."
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

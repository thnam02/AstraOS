import Link from "next/link";

import {
  AstraDataTable,
  AstraStatusBadge,
  type AstraTone,
} from "@/components/astra";
import {
  StageResult,
  StageSection,
  StageSplit,
} from "@/components/live/StageShell";
import {
  LEARN_STATUS,
  learnCapabilityStatusLabel,
  type LearnCapabilityState,
} from "@/lib/decisionNarrative";
import { formatUtilityShort, humanizeEnum } from "@/lib/format";
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

function statusTone(state: LearnCapabilityState): AstraTone {
  if (state === "ACTIVE") return "positive";
  if (state === "PRIMARY") return "info";
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
    <StageSplit stretch>
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
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div className="space-y-1 border-t border-line-muted pt-3">
              <dt className="text-muted">Product</dt>
              <dd className="font-medium">{offer.product_name}</dd>
            </div>
            <div className="space-y-1 border-t border-line-muted pt-3">
              <dt className="text-muted">Final price</dt>
              <dd className="font-mono text-lg tabular-nums">
                {formatAudCents(offer.pricing.total_price_cents)}
              </dd>
            </div>
            <div className="space-y-1 border-t border-line-muted pt-3">
              <dt className="text-muted">Final utility</dt>
              <dd className="font-mono text-lg tabular-nums">
                {formatUtilityShort(offer.buyer_utility)}
              </dd>
            </div>
            <div className="space-y-1 border-t border-line-muted pt-3">
              <dt className="text-muted">Merchant contribution</dt>
              <dd className="font-mono text-lg tabular-nums">
                {formatAudCents(offer.contribution_margin_cents)}
              </dd>
            </div>
            <div className="space-y-1 border-t border-line-muted pt-3">
              <dt className="text-muted">Negotiation</dt>
              <dd>
                {negotiation?.state ? humanizeEnum(negotiation.state) : "—"}
              </dd>
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
                    {learnCapabilityStatusLabel(item.state)}
                  </AstraStatusBadge>
                </td>
              </tr>
            ))}
          </tbody>
        </AstraDataTable>
        <p className="mt-3 text-sm text-muted">
          LIVE uses transparent cold-start scoring. The learned response model
          is experimental. A real observed-data model is future work.
        </p>
      </StageSection>
    </StageSplit>
  );
}

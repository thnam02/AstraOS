"use client";

import { useState } from "react";

import { Disclosure } from "@/components/shared/Disclosure";
import {
  StageDisclosure,
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { negotiationConstraint } from "@/lib/decisionNarrative";
import { formatAudCents, formatRate } from "@/lib/money";
import type { MerchantProposal, NegotiationResponse, NegotiationTurn } from "@/types";

function offerTerms(proposal: MerchantProposal | null): string[] {
  const offer = proposal?.offer;
  if (!offer) return [];
  return [
    formatAudCents(offer.pricing.total_price_cents),
    offer.delivery.name,
    `${offer.warranty.months}-month warranty`,
    offer.bundle?.name ?? "No bundle",
  ];
}

function lastBuyerTurn(turns: NegotiationTurn[]): NegotiationTurn | null {
  return (
    [...turns]
      .reverse()
      .find((turn) => turn.actor === "BUYER" || turn.actor === "BUYER_AGENT") ??
    null
  );
}

function Delta({
  previous,
  current,
}: {
  previous: MerchantProposal | null;
  current: MerchantProposal | null;
}) {
  if (!previous?.offer || !current?.offer) return null;
  const a = previous.offer;
  const b = current.offer;
  const rows: { label: string; from: string; to: string }[] = [];
  if (a.pricing.total_price_cents !== b.pricing.total_price_cents) {
    rows.push({
      label: "Price",
      from: formatAudCents(a.pricing.total_price_cents),
      to: formatAudCents(b.pricing.total_price_cents),
    });
  }
  if (a.delivery.code !== b.delivery.code) {
    rows.push({ label: "Delivery", from: a.delivery.name, to: b.delivery.name });
  }
  if (a.warranty.months !== b.warranty.months) {
    rows.push({
      label: "Warranty",
      from: `${a.warranty.months} mo`,
      to: `${b.warranty.months} mo`,
    });
  }
  if ((a.bundle?.code ?? null) !== (b.bundle?.code ?? null)) {
    rows.push({
      label: "Bundle",
      from: a.bundle?.name ?? "None",
      to: b.bundle?.name ?? "None",
    });
  }
  if (!rows.length) return null;
  return (
    <StageSection title="Term movement">
      <table className="w-full max-w-lg text-sm">
        <thead>
          <tr className="text-left text-xs text-muted">
            <th className="pb-2 font-medium">Term</th>
            <th className="pb-2 font-medium">Previous</th>
            <th className="pb-2 font-medium">Current</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-t border-line-muted">
              <td className="py-2">{row.label}</td>
              <td className="py-2 font-mono tabular-nums text-muted">{row.from}</td>
              <td className="py-2 font-mono tabular-nums">{row.to}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </StageSection>
  );
}

function ProtocolTurn({
  turn,
  proposal,
}: {
  turn: NegotiationTurn;
  proposal: MerchantProposal | null;
}) {
  const buyer = turn.actor === "BUYER" || turn.actor === "BUYER_AGENT";
  const constraint = negotiationConstraint(turn.structured_payload);
  const action = turn.structured_action.replaceAll("_", " ");
  const related =
    proposal?.offer && proposal.offer_id === turn.related_offer_id
      ? proposal
      : proposal;

  return (
    <article className="grid gap-4 md:grid-cols-[140px_minmax(0,1fr)]">
      <div>
        <p className="eyebrow">{buyer ? "Buyer agent" : "AstraOS"}</p>
        <p className="mt-1 text-xs uppercase tracking-[0.08em] text-muted">
          {action}
        </p>
      </div>
      <div className="space-y-2 text-sm">
        {turn.raw_message ? (
          <p>
            <span className="text-xs text-muted">Natural request </span>
            “{turn.raw_message}”
          </p>
        ) : null}
        {constraint ? (
          <p>
            <span className="text-xs text-muted">Parsed constraint </span>
            <span className="font-mono tabular-nums">{constraint}</span>
          </p>
        ) : null}
        {!buyer && related?.offer ? (
          <div>
            <p className="text-xs text-muted">Counteroffer</p>
            <p className="mt-1 font-medium">{related.offer.product_name}</p>
            <p className="font-mono tabular-nums">{offerTerms(related).join(" · ")}</p>
            {related.reason_codes.length ? (
              <p className="mt-1 text-xs text-muted">
                {related.reason_codes.join(" · ").replaceAll("_", " ")}
              </p>
            ) : null}
          </div>
        ) : null}
        {Object.keys(turn.structured_payload ?? {}).length ? (
          <Disclosure title="Structured payload">
            <pre className="overflow-x-auto text-[11px] text-muted">
              {JSON.stringify(turn.structured_payload, null, 2)}
            </pre>
          </Disclosure>
        ) : null}
      </div>
    </article>
  );
}

export function NegotiationPanel({
  negotiation,
  busy,
  onMessage,
  onSimulate,
}: {
  negotiation: NegotiationResponse;
  busy: boolean;
  onMessage: (message: string) => void;
  onSimulate: (mode: "TRAVEL" | "BUDGET") => void;
}) {
  const [draft, setDraft] = useState("Can you get this below A$315?");
  const commercial = negotiation.commercial;
  const turns = negotiation.turns.filter(
    (turn) => turn.structured_action !== "SESSION_OPENED",
  );
  const offer = negotiation.proposal?.offer;
  const buyerTurn = lastBuyerTurn(turns);
  const buyerResponse =
    buyerTurn?.raw_message ??
    (buyerTurn ? buyerTurn.structured_action.replaceAll("_", " ") : null);

  return (
    <>
      <StageResult
        label="Negotiation status"
        title={negotiation.state.replaceAll("_", " ")}
        explanation={
          offer ? (
            <p>
              {offer.product_name}
              {buyerResponse ? (
                <>
                  <span className="mx-2 text-muted">·</span>
                  Buyer: “{buyerResponse}”
                </>
              ) : (
                <span className="text-muted"> · Awaiting buyer response</span>
              )}
            </p>
          ) : undefined
        }
        metrics={[
          {
            label: "Round",
            value: negotiation.proposal?.version ?? "—",
          },
          {
            label: "Utility",
            value: offer ? offer.buyer_utility.toFixed(2) : "—",
          },
          {
            label: "Contribution",
            value: offer
              ? formatAudCents(offer.contribution_margin_cents)
              : "—",
          },
        ]}
        actions={
          <div className="flex w-full flex-wrap gap-2">
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              className="control min-w-[240px] flex-1 px-3 py-2 text-sm"
              aria-label="Buyer counter message"
            />
            <button
              type="button"
              disabled={busy || !draft.trim()}
              onClick={() => onMessage(draft)}
              className="btn-ghost"
            >
              Send counter
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onMessage("I'll take it.")}
              className="btn-primary"
            >
              Accept
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onSimulate("TRAVEL")}
              className="btn-quiet"
            >
              Simulate travel
            </button>
          </div>
        }
      />

      {offer ? (
        <StageSection title="Current terms">
          <dl className="max-w-md space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Price</dt>
              <dd className="font-mono tabular-nums">
                {formatAudCents(offer.pricing.total_price_cents)}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Delivery</dt>
              <dd>{offer.delivery.name}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Warranty</dt>
              <dd>{offer.warranty.months}-month</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Bundle</dt>
              <dd>{offer.bundle?.name ?? "None"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Returns</dt>
              <dd>
                {offer.returns?.window_days
                  ? `${offer.returns.window_days}-day`
                  : "Standard"}
              </dd>
            </div>
          </dl>
        </StageSection>
      ) : null}

      <Delta
        previous={negotiation.previous_proposal}
        current={negotiation.proposal}
      />

      {turns.length ? (
        <StageDisclosure title="Negotiation history">
          <ol className="space-y-5">
            {turns.map((turn, index) => (
              <li key={turn.turn_id}>
                <ProtocolTurn turn={turn} proposal={negotiation.proposal} />
                {index < turns.length - 1 ? (
                  <p className="mt-3 text-center text-muted" aria-hidden>
                    ↓
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        </StageDisclosure>
      ) : null}

      {commercial ? (
        <StageDisclosure title="Commercial bounds">
          <dl className="grid max-w-lg gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-muted">Min margin</dt>
              <dd className="tabular-nums">{formatRate(commercial.minimum_margin_rate)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Max discount</dt>
              <dd className="tabular-nums">{formatRate(commercial.maximum_discount_rate)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Inventory</dt>
              <dd className="tabular-nums">{commercial.inventory_units ?? "—"}</dd>
            </div>
          </dl>
        </StageDisclosure>
      ) : null}
    </>
  );
}

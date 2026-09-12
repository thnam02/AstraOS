"use client";

import { useState } from "react";

import { formatAudCents, formatRate } from "@/lib/money";
import type { MerchantProposal, NegotiationResponse } from "@/types";

function offerLine(proposal: MerchantProposal | null): string {
  const offer = proposal?.offer;
  if (!offer) return "No commercial proposal";
  return [
    offer.product_name,
    formatAudCents(offer.pricing.total_price_cents),
    offer.delivery.name,
    `${offer.warranty.months}m warranty`,
  ].join(" · ");
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
  const price = b.pricing.total_price_cents - a.pricing.total_price_cents;
  const contrib =
    b.contribution_margin_cents - a.contribution_margin_cents;
  const utility = b.buyer_utility - a.buyer_utility;
  return (
    <div className="border border-line px-4 py-3 text-sm">
      <p className="text-[11px] tracking-[0.14em] text-muted">
        PROPOSAL DELTA
      </p>
      <p className="mt-2">
        Price {formatAudCents(a.pricing.total_price_cents)} →{" "}
        {formatAudCents(b.pricing.total_price_cents)}{" "}
        {price ? `(${price > 0 ? "+" : ""}${formatAudCents(price)})` : "—"}
      </p>
      <p>
        Delivery {a.delivery.name} → {b.delivery.name}
      </p>
      <p>
        Warranty {a.warranty.months}m → {b.warranty.months}m
      </p>
      <p>
        Contribution {formatAudCents(a.contribution_margin_cents)} →{" "}
        {formatAudCents(b.contribution_margin_cents)}{" "}
        {contrib ? `(${contrib > 0 ? "+" : ""}${formatAudCents(contrib)})` : ""}
      </p>
      <p>
        Simulated utility {a.buyer_utility.toFixed(3)} →{" "}
        {b.buyer_utility.toFixed(3)} ({utility >= 0 ? "+" : ""}
        {utility.toFixed(3)})
      </p>
    </div>
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

  return (
    <section className="space-y-5 border border-line bg-surface px-5 py-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[11px] font-medium tracking-[0.14em] text-muted">
            MACHINE-TO-MACHINE EXCHANGE
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Negotiate
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted">
            LLMs interpret language. Deterministic AstraOS services control
            every commercial term.
          </p>
        </div>
        <p className="font-mono text-[11px] text-muted">
          {negotiation.state}
        </p>
      </div>

      {commercial ? (
        <div className="grid gap-3 border border-line px-4 py-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-[11px] text-muted">MIN MARGIN</p>
            <p className="tabular-nums">{formatRate(commercial.minimum_margin_rate)}</p>
          </div>
          <div>
            <p className="text-[11px] text-muted">MAX DISCOUNT</p>
            <p className="tabular-nums">
              {formatRate(commercial.maximum_discount_rate)}
            </p>
          </div>
          <div>
            <p className="text-[11px] text-muted">INVENTORY</p>
            <p className="tabular-nums">{commercial.inventory_units ?? "—"}</p>
          </div>
          <div>
            <p className="text-[11px] text-muted">EXPIRES</p>
            <p className="font-mono text-[11px]">
              {commercial.expires_at
                ? new Date(commercial.expires_at).toLocaleTimeString()
                : "—"}
            </p>
          </div>
        </div>
      ) : null}

      <ol className="space-y-3">
        {negotiation.turns.map((turn) => (
          <li key={turn.turn_id} className="border border-line px-4 py-3">
            <div className="flex justify-between gap-3 text-[11px] tracking-[0.12em] text-muted">
              <span>
                {turn.actor} · {turn.structured_action}
              </span>
              <span>#{turn.turn_number}</span>
            </div>
            {turn.raw_message ? (
              <p className="mt-2 text-sm">{turn.raw_message}</p>
            ) : null}
            <pre className="mt-2 overflow-x-auto text-[11px] text-muted">
              {JSON.stringify(turn.structured_payload, null, 2)}
            </pre>
          </li>
        ))}
      </ol>

      {negotiation.proposal ? (
        <div className="border border-line px-4 py-4">
          <p className="text-[11px] tracking-[0.14em] text-muted">
            {negotiation.proposal.proposal_type} #{negotiation.proposal.version}
          </p>
          <p className="mt-2 text-sm font-medium">
            {offerLine(negotiation.proposal)}
          </p>
          <p className="mt-2 text-[11px] text-muted">
            {negotiation.proposal.outcome} ·{" "}
            {negotiation.proposal.reason_codes.join(" · ")}
          </p>
          <ul className="mt-3 space-y-1 text-sm">
            {negotiation.proposal.explanation.map((line) => (
              <li key={line}>✓ {line}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <Delta
        previous={negotiation.previous_proposal}
        current={negotiation.proposal}
      />

      <div className="flex flex-wrap gap-2">
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="min-w-[240px] flex-1 border border-line bg-surface px-3 py-2 text-sm"
        />
        <button
          type="button"
          disabled={busy || !draft.trim()}
          onClick={() => onMessage(draft)}
          className="border border-ink px-3 py-2 text-xs tracking-[0.12em]"
        >
          SEND TURN
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onMessage("I'll take it.")}
          className="border border-line px-3 py-2 text-xs tracking-[0.12em]"
        >
          ACCEPT
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onSimulate("TRAVEL")}
          className="border border-line px-3 py-2 text-xs tracking-[0.12em]"
        >
          SIMULATE TRAVEL
        </button>
      </div>
    </section>
  );
}

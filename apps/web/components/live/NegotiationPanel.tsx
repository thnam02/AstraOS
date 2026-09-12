"use client";

import { useState } from "react";

import { Disclosure } from "@/components/shared/Disclosure";
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
  const contrib = b.contribution_margin_cents - a.contribution_margin_cents;
  const utility = b.buyer_utility - a.buyer_utility;
  return (
    <div className="text-sm">
      <p className="eyebrow">Proposal delta</p>
      <p className="mt-2">
        Price {formatAudCents(a.pricing.total_price_cents)} →{" "}
        {formatAudCents(b.pricing.total_price_cents)}{" "}
        {price ? `(${price > 0 ? "+" : ""}${formatAudCents(price)})` : ""}
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
        Buyer utility {a.buyer_utility.toFixed(2)} → {b.buyer_utility.toFixed(2)}{" "}
        ({utility >= 0 ? "+" : ""}
        {utility.toFixed(2)})
      </p>
    </div>
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
  const related = proposal?.offer && proposal.offer_id === turn.related_offer_id
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

  return (
    <section className="space-y-5">
      <div>
        <p className="eyebrow">Negotiate</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">
          Protocol exchange
        </h2>
        <p className="mt-1 text-sm text-muted">
          Language is interpreted. Deterministic services control commercial terms.
        </p>
      </div>

      {commercial ? (
        <dl className="grid gap-3 text-sm sm:grid-cols-4">
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
          <div>
            <dt className="text-xs text-muted">State</dt>
            <dd className="font-mono text-xs">{negotiation.state}</dd>
          </div>
        </dl>
      ) : null}

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

      {negotiation.proposal?.offer ? (
        <div className="bg-canvas px-4 py-3">
          <p className="eyebrow">Current merchant counteroffer</p>
          <p className="mt-1 text-lg font-semibold">
            {negotiation.proposal.offer.product_name}
          </p>
          <p className="font-mono text-sm tabular-nums">
            {offerTerms(negotiation.proposal).join(" · ")}
          </p>
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
    </section>
  );
}

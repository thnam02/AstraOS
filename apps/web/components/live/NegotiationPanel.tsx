"use client";

import { useState } from "react";

import {
  AstraCallout,
  AstraDataTable,
  AstraDelta,
  AstraEmptyState,
  AstraErrorState,
  AstraInspector,
  AstraKeyValue,
  AstraStatusBadge,
} from "@/components/astra";
import {
  StageResult,
  StageSection,
} from "@/components/live/StageShell";
import { METRIC_HELP } from "@/lib/decisionNarrative";
import {
  activeConstraintLabels,
  buildNegotiationTimeline,
  buyerMayAct,
  commercialChanges,
  constraintChanges,
  currentMerchantEvent,
  currentRoundLabel,
  latestBuyerCounter,
  merchantGuardrails,
  negotiationStatus,
  offerTermsFromProposal,
  previousOfferTerms,
  termDeltaRows,
  whyNotBuyerRequest,
  type TimelineEvent,
} from "@/lib/negotiationStory";
import { formatAudCents } from "@/lib/money";
import type { NegotiationResponse } from "@/types";

function TermsList({
  terms,
}: {
  terms: NonNullable<ReturnType<typeof offerTermsFromProposal>>;
}) {
  return (
    <ul className="space-y-1 text-[15px] leading-6">
      {terms.delivery ? <li>{terms.delivery}</li> : null}
      {terms.warranty ? <li>{terms.warranty}</li> : null}
      {terms.bundle ? <li>{terms.bundle === "None" ? "No bundle" : terms.bundle}</li> : null}
      {terms.returns ? <li>{terms.returns}</li> : null}
    </ul>
  );
}

function TimelineCard({
  event,
  onInspect,
}: {
  event: TimelineEvent;
  onInspect: (event: TimelineEvent) => void;
}) {
  return (
    <article className="grid gap-3 md:grid-cols-[9.5rem_minmax(0,1fr)]">
      <div>
        <p className="eyebrow">{event.actor === "BUYER" ? "Buyer agent" : "AstraOS"}</p>
        <p className="mt-1 text-xs uppercase tracking-[0.08em] text-muted">
          {event.subtitle}
        </p>
      </div>
      <div className="space-y-3 text-sm">
        {event.message ? (
          <div>
            <p className="type-small text-muted">Buyer message</p>
            <p className="mt-1">“{event.message}”</p>
          </div>
        ) : null}
        {event.parsed.length ? (
          <div>
            <p className="type-small text-muted">Parsed commercial request</p>
            <dl className="mt-1 space-y-1">
              {event.parsed.map((row) => (
                <div key={`${row.field}-${row.value}`} className="flex gap-3">
                  <dt className="text-muted">{row.label}</dt>
                  <dd className="font-mono tabular-nums">{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}
        {event.terms?.total ? (
          <div>
            <p className="font-medium">{event.terms.productName}</p>
            <p className="font-mono text-lg font-semibold tabular-nums">
              {event.terms.total}
            </p>
            <TermsList terms={event.terms} />
          </div>
        ) : null}
        {event.kind === "NO_SAFE_COUNTER" ? (
          <p className="text-muted">
            No merchant-policy-safe configuration can satisfy this request.
          </p>
        ) : null}
        {event.inspectPayload ? (
          <button
            type="button"
            className="btn-quiet"
            onClick={() => onInspect(event)}
          >
            Inspect machine payload
          </button>
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
  onMessage: (payload: { message?: string; action?: string }) => void;
  onSimulate: (mode: "TRAVEL" | "BUDGET") => void;
}) {
  const [draft, setDraft] = useState("");
  const [inspect, setInspect] = useState<TimelineEvent | null>(null);
  const events = buildNegotiationTimeline(negotiation);
  const status = negotiationStatus(negotiation.state);
  const current = currentMerchantEvent(events);
  const buyer = latestBuyerCounter(events);
  const proposal = negotiation.proposal;
  const offer = proposal?.offer ?? null;
  const currentTerms = offerTermsFromProposal(proposal);
  const previousTerms = previousOfferTerms(negotiation);
  const deltaRows = termDeltaRows(previousTerms, buyer?.parsed ?? [], currentTerms);
  const changes = commercialChanges(previousTerms, currentTerms);
  const why = whyNotBuyerRequest(
    proposal,
    buyer,
    negotiation.previous_proposal,
  );
  const allowed = buyerMayAct(proposal, negotiation.state);
  const working =
    negotiation.working_intent ??
    negotiation.original_intent ??
    negotiation.match?.intent ??
    negotiation.construction?.intent ??
    null;
  const original = negotiation.original_intent ?? negotiation.match?.intent ?? null;
  const constraints = activeConstraintLabels(working);
  const evolved = constraintChanges(original, working);
  const guardrails = merchantGuardrails(proposal, negotiation.commercial);
  const noSafe =
    negotiation.state === "NO_POLICY_SAFE_COUNTER" ||
    current?.kind === "NO_SAFE_COUNTER" ||
    (!offer && proposal?.outcome === "DECLINE");
  const terminal =
    negotiation.state === "EXPIRED" ||
    negotiation.state === "NEGOTIATION_LIMIT_REACHED" ||
    negotiation.state === "BUYER_REJECTED";
  const accepted =
    negotiation.state === "BUYER_ACCEPTED" ||
    negotiation.state === "READY_FOR_CHECKOUT";
  const counterLabel =
    current?.kind === "INITIAL_PROPOSAL"
      ? "Initial proposal"
      : noSafe
        ? "No safe counter"
        : "Merchant counter";
  const acceptPrice =
    currentTerms?.total ??
    (offer ? formatAudCents(offer.pricing.total_price_cents) : null);

  let lastRound: number | null = null;
  const rows = events.map((event) => {
    const showRound =
      event.actor === "ASTRAOS" &&
      event.round != null &&
      event.round !== lastRound;
    if (showRound && event.round != null) lastRound = event.round;
    return { event, showRound };
  });

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <AstraStatusBadge tone={status.tone}>{status.label}</AstraStatusBadge>
        <p className="type-small text-muted">{currentRoundLabel(negotiation)}</p>
      </div>

      {terminal ? (
        <AstraErrorState
          title={status.label}
          message={
            negotiation.state === "NEGOTIATION_LIMIT_REACHED"
              ? "This session has reached the maximum number of buyer turns."
              : negotiation.state === "EXPIRED"
                ? "The current proposal is no longer valid."
                : "The buyer rejected the merchant proposal."
          }
        />
      ) : null}

      {constraints.length ? (
        <StageSection title="Active buyer constraints">
          <p className="text-sm leading-6">{constraints.join(" · ")}</p>
          {evolved.length ? (
            <ul className="mt-3 space-y-1 text-sm">
              {evolved.map((item) => (
                <li key={`${item.kind}-${item.field}-${item.to}`}>
                  <span className="eyebrow mr-2">
                    {item.kind === "RELAXED"
                      ? "Buyer relaxed budget"
                      : item.kind === "ADDED"
                        ? "Added requirement"
                        : item.kind === "REMOVED"
                          ? "Removed requirement"
                          : "Updated constraint"}
                  </span>
                  <span className="text-muted">{item.from ?? "—"}</span>
                  {item.to ? (
                    <>
                      <span className="mx-2 text-muted">→</span>
                      <span>{item.to}</span>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </StageSection>
      ) : null}

      <StageSection
        title="Negotiation timeline"
        description="Structured protocol exchange. Language is interpreted; commercial control stays deterministic."
      >
        {events.length ? (
          <ol className="space-y-6">
            {rows.map(({ event, showRound }, index) => (
              <li key={event.id}>
                {showRound ? (
                  <p className="eyebrow mb-3">Round {event.round}</p>
                ) : null}
                <TimelineCard event={event} onInspect={setInspect} />
                {index < rows.length - 1 ? (
                  <p className="mt-4 text-center text-muted" aria-hidden>
                    ↓
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-muted">Awaiting the merchant proposal.</p>
        )}
      </StageSection>

      {noSafe ? (
        <AstraEmptyState
          title="No safe counter"
          body={
            why
              ? `Buyer requested ${why.requested ?? "a change that cannot be met"}. No merchant-policy-safe configuration can satisfy this request.${why.closest ? ` Closest available configuration: ${why.closest}.` : ""} Requires buyer relaxation.`
              : "No merchant-policy-safe configuration can satisfy this request. Requires buyer relaxation."
          }
        />
      ) : offer && currentTerms ? (
        <StageResult
          label={counterLabel}
          title={currentTerms.productName ?? offer.product_name}
          value={currentTerms.total}
          explanation={<TermsList terms={currentTerms} />}
          metrics={[
            {
              label: "Simulated buyer utility",
              value:
                currentTerms.utility != null
                  ? currentTerms.utility.toFixed(2)
                  : "—",
              hint: METRIC_HELP.buyerUtility,
            },
            {
              label: "Merchant contribution",
              value: currentTerms.contribution ?? "—",
              hint: METRIC_HELP.contribution,
            },
          ]}
        >
          {why ? (
            <AstraCallout title={why.title}>
              <dl className="grid gap-3 sm:grid-cols-3">
                <div>
                  <dt>Requested maximum</dt>
                  <dd className="font-mono tabular-nums text-ink">
                    {why.requested ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt>Lowest safe configuration</dt>
                  <dd className="font-mono tabular-nums text-ink">
                    {why.closest ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt>Gap</dt>
                  <dd className="font-mono tabular-nums text-ink">{why.gap ?? "—"}</dd>
                </div>
              </dl>
              {why.reasons.length ? (
                <p className="mt-2">{why.reasons[0]}</p>
              ) : null}
            </AstraCallout>
          ) : null}
          {guardrails.length ? (
            <ul className="mt-4 space-y-1 text-sm">
              {guardrails.map((item) => (
                <li key={item.label} className="flex gap-2">
                  <span aria-hidden className={item.ok ? "text-mark" : "text-danger"}>
                    {item.ok ? "✓" : "!"}
                  </span>
                  <span>{item.label}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </StageResult>
      ) : null}

      {deltaRows.length && previousTerms && (buyer || changes.length) ? (
        <StageSection title="What changed?">
          <div className="overflow-x-auto">
            <AstraDataTable>
              <thead>
                <tr>
                  <th>Term</th>
                  <th>Previous offer</th>
                  <th>Buyer request</th>
                  <th>AstraOS counter</th>
                </tr>
              </thead>
              <tbody>
                {deltaRows.map((row) => (
                  <tr key={row.term}>
                    <td>{row.term}</td>
                    <td className="font-mono tabular-nums text-muted">{row.previous}</td>
                    <td className="font-mono tabular-nums">{row.requested}</td>
                    <td
                      className={
                        row.changed
                          ? "font-mono font-medium tabular-nums"
                          : "font-mono tabular-nums text-muted"
                      }
                    >
                      {row.counter}
                    </td>
                  </tr>
                ))}
              </tbody>
            </AstraDataTable>
          </div>
          {changes.length ? (
            <div className="mt-4 space-y-1">
              {changes.map((item) => (
                <AstraDelta
                  key={item.label}
                  label={item.label}
                  from={item.from}
                  to={item.to}
                  delta={item.delta}
                />
              ))}
            </div>
          ) : null}
        </StageSection>
      ) : null}

      {currentTerms && !noSafe ? (
        <StageSection
          title={
            current?.kind === "INITIAL_PROPOSAL"
              ? "Current proposal terms"
              : "Current counter terms"
          }
        >
          <AstraKeyValue
            rows={[
              { label: "Price", value: currentTerms.total ?? "—" },
              { label: "Delivery", value: currentTerms.delivery ?? "—" },
              { label: "Warranty", value: currentTerms.warranty ?? "—" },
              { label: "Bundle", value: currentTerms.bundle ?? "None" },
              { label: "Returns", value: currentTerms.returns ?? "—" },
            ]}
          />
        </StageSection>
      ) : null}

      {accepted ? (
        <p className="text-sm">Buyer accepted {acceptPrice ?? "the current proposal"}.</p>
      ) : null}

      {!terminal && !accepted ? (
        <StageSection title="Buyer actions">
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (!draft.trim() || !allowed.counter) return;
              onMessage({ message: draft.trim() });
              setDraft("");
            }}
          >
            <div>
              <label htmlFor="buyer-counter" className="eyebrow">
                Buyer counter
              </label>
              <textarea
                id="buyer-counter"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="control mt-2 min-h-[5.5rem] w-full px-3 py-2 text-sm"
                placeholder='e.g. “I can accept A$85 if same-day delivery is included.”'
                disabled={busy || !allowed.counter}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={busy || !allowed.counter || !draft.trim()}
                className="btn-ghost"
              >
                Send buyer counter
              </button>
              {allowed.accept && acceptPrice ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onMessage({ message: "I'll take it.", action: "ACCEPT" })}
                  className="btn-primary"
                >
                  Buyer accepts {acceptPrice}
                </button>
              ) : null}
              {allowed.reject ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => onMessage({ action: "REJECT" })}
                  className="btn-quiet"
                >
                  Buyer rejects
                </button>
              ) : null}
              <button
                type="button"
                disabled={busy || !offer}
                onClick={() => onSimulate("TRAVEL")}
                className="btn-quiet"
              >
                Simulate traveller response
              </button>
            </div>
          </form>
        </StageSection>
      ) : null}

      <AstraInspector
        open={Boolean(inspect)}
        title="Machine payload"
        onClose={() => setInspect(null)}
      >
        <pre className="overflow-x-auto text-[11px] text-muted">
          {JSON.stringify(inspect?.inspectPayload ?? {}, null, 2)}
        </pre>
      </AstraInspector>
    </>
  );
}

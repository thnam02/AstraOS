"use client";

import { useState } from "react";

import {
  AstraDataTable,
  AstraDelta,
  AstraEmptyState,
  AstraErrorState,
  AstraInspector,
  AstraKeyValue,
  AstraStatusBadge,
} from "@/components/astra";
import {
  StageSection,
  StageSplit,
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
        {event.kind === "BUYER_ASK" && !event.parsed.length ? (
          <p className="text-muted">No commercial change was extracted.</p>
        ) : null}
        {event.kind === "NO_SAFE_COUNTER" ? (
          <p className="text-muted">
            No merchant-policy-safe configuration can satisfy this request.
          </p>
        ) : null}
        {event.kind === "CLARIFY" && event.explanation.length ? (
          <div>
            {event.explanation.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
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
  const current = currentMerchantEvent(events);
  const status =
    current?.kind === "CLARIFY"
      ? {
          code: "CLARIFICATION_REQUIRED",
          label: "Clarification required",
          tone: "warning" as const,
        }
      : negotiationStatus(negotiation.state);
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
        tone="primary"
      >
        {events.length ? (
          <ol className="space-y-5">
            {rows.map(({ event, showRound }, index) => (
              <li
                key={event.id}
                className={
                  index < rows.length - 1
                    ? "border-b border-line-muted pb-5"
                    : undefined
                }
              >
                {showRound ? (
                  <p className="eyebrow mb-3">Round {event.round}</p>
                ) : null}
                <TimelineCard event={event} onInspect={setInspect} />
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
      ) : null}

      {currentTerms && !noSafe ? (
        <StageSplit>
          <StageSection
            title={
              current?.kind === "INITIAL_PROPOSAL"
                ? "Current proposal terms"
                : "Current counter terms"
            }
          >
            <p className="font-medium">{currentTerms.productName}</p>
            <p className="mt-1 font-mono text-xl font-semibold tabular-nums">
              {currentTerms.total}
            </p>
            <div className="mt-4">
              <AstraKeyValue
                rows={[
                  { label: "Price", value: currentTerms.total ?? "—" },
                  { label: "Delivery", value: currentTerms.delivery ?? "—" },
                  { label: "Warranty", value: currentTerms.warranty ?? "—" },
                  { label: "Bundle", value: currentTerms.bundle ?? "None" },
                  { label: "Returns", value: currentTerms.returns ?? "—" },
                ]}
              />
            </div>
          </StageSection>
          <StageSection title="Commercial health">
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="type-small text-muted">Simulated buyer utility</dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
                  {currentTerms.utility != null
                    ? currentTerms.utility.toFixed(2)
                    : "—"}
                </dd>
                <p className="mt-1 text-xs text-muted">{METRIC_HELP.buyerUtility}</p>
              </div>
              <div>
                <dt className="type-small text-muted">Merchant contribution</dt>
                <dd className="mt-1 font-mono text-xl font-semibold tabular-nums">
                  {currentTerms.contribution ?? "—"}
                </dd>
                <p className="mt-1 text-xs text-muted">{METRIC_HELP.contribution}</p>
              </div>
            </dl>
            {why ? (
              <div className="mt-5">
                <p className="type-small text-muted">{why.title}</p>
                <dl className="mt-2 grid gap-3 sm:grid-cols-3">
                  <div>
                    <dt className="text-xs text-muted">Requested maximum</dt>
                    <dd className="font-mono tabular-nums">{why.requested ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Lowest safe configuration</dt>
                    <dd className="font-mono tabular-nums">{why.closest ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Gap</dt>
                    <dd className="font-mono tabular-nums">{why.gap ?? "—"}</dd>
                  </div>
                </dl>
                {why.reasons.length ? (
                  <p className="mt-2 text-sm">{why.reasons[0]}</p>
                ) : null}
              </div>
            ) : null}
            {guardrails.length ? (
              <ul className="mt-4 space-y-1 text-sm">
                {guardrails.map((item) => (
                  <li key={item.label} className="flex gap-2">
                    <span
                      aria-hidden
                      className={item.ok ? "text-mark" : "text-danger"}
                    >
                      {item.ok ? "✓" : "!"}
                    </span>
                    <span>{item.label}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </StageSection>
        </StageSplit>
      ) : null}

      {deltaRows.length && previousTerms && (buyer || changes.length) ? (
        <StageSection title="What changed?">
          <div className="overflow-x-auto">
            <AstraDataTable bordered={false}>
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

      {accepted ? (
        <StageSection title="Buyer action">
          <p className="text-sm">
            Buyer accepted {acceptPrice ?? "the current proposal"}.
          </p>
        </StageSection>
      ) : null}

      {!terminal && !accepted ? (
        <StageSection title="Buyer action">
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
              {current?.kind === "CLARIFY" ? (
                <p className="mt-1 text-sm text-muted">
                  Last message was not a commercial change. Specify a price,
                  delivery, warranty, bundle, or product change.
                </p>
              ) : null}
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

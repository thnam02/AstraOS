"use client";

import { useEffect, useState } from "react";

import {
  AstraEmptyState,
  AstraErrorState,
  AstraInspector,
  AstraLoadingState,
  AstraPanel,
  AstraStatusBadge,
} from "@/components/astra";
import { getNegotiation } from "@/lib/api";
import {
  buildExchangeEvents,
  type ExchangeEvent,
} from "@/lib/integrationsDisplay";
import { humanizeEnum } from "@/lib/format";
import type { AgentActivityItem, NegotiationResponse } from "@/types";

function TermsBlock({ event }: { event: ExchangeEvent }) {
  const terms = event.terms;
  if (!terms) return null;
  return (
    <dl className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
      {[
        ["Product", terms.product],
        ["Customer total", terms.total],
        ["Delivery", terms.delivery],
        ["Warranty", terms.warranty],
        ["Bundle", terms.bundle],
        ["Returns", terms.returns],
      ].map(([label, value]) =>
        value ? (
          <div key={label} className="flex justify-between gap-3 sm:block">
            <dt className="text-muted">{label}</dt>
            <dd className="font-medium tabular-nums">{value}</dd>
          </div>
        ) : null,
      )}
    </dl>
  );
}

export function ExchangeInspector({
  item,
  open,
  onClose,
}: {
  item: AgentActivityItem | null;
  open: boolean;
  onClose: () => void;
}) {
  const [negotiation, setNegotiation] = useState<NegotiationResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [showPayload, setShowPayload] = useState(false);
  const sessionId = item?.negotiation_session_id ?? null;

  useEffect(() => {
    if (!open || !sessionId) {
      return;
    }
    let cancelled = false;
    getNegotiation(sessionId)
      .then((data) => {
        if (!cancelled) {
          setNegotiation(data);
          setError(null);
          setShowPayload(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setNegotiation(null);
          setError("Unable to load exchange details.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, sessionId]);

  const matched =
    negotiation && sessionId && negotiation.session_id === sessionId
      ? negotiation
      : null;
  const showLoading = open && Boolean(sessionId) && !matched && !error;
  const events = matched ? buildExchangeEvents(matched) : [];

  return (
    <AstraInspector
      open={open}
      title="Inspect exchange"
      onClose={onClose}
    >
      <div className="space-y-4">
        {item ? (
          <div className="flex flex-wrap gap-2 text-xs text-muted">
            <AstraStatusBadge tone="info">
              {humanizeEnum(item.kind)}
            </AstraStatusBadge>
            <span>Session {item.negotiation_session_id}</span>
            {item.request_id ? <span>Request {item.request_id}</span> : null}
            {item.order_number ? <span>Order {item.order_number}</span> : null}
          </div>
        ) : null}

        {showLoading ? (
          <AstraLoadingState
            title="Loading exchange"
            steps={[
              "Fetching negotiation session",
              "Reading turns and proposals",
              "Building timeline",
            ]}
          />
        ) : null}

        {error ? (
          <AstraErrorState
            title="Exchange unavailable"
            message={error}
            next="Retry from the activity table once the API is available."
          />
        ) : null}

        {!showLoading && !error && matched && events.length === 0 ? (
          <AstraEmptyState
            title="No exchange events"
            body="This session has no recorded turns or proposals yet."
          />
        ) : null}

        {!showLoading && !error && events.length > 0 ? (
          <ol className="space-y-3">
            {events.map((event, index) => (
              <li key={event.id}>
                {index > 0 ? (
                  <p className="mb-2 text-center text-[11px] text-muted" aria-hidden>
                    ↓
                  </p>
                ) : null}
                <AstraPanel>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="eyebrow">
                      {event.actor} → {event.kind}
                    </p>
                    {event.timestamp ? (
                      <time
                        className="type-small text-muted tabular-nums"
                        dateTime={event.timestamp}
                      >
                        {new Date(event.timestamp).toLocaleString()}
                      </time>
                    ) : null}
                  </div>
                  <h3 className="mt-1 text-sm font-semibold">{event.title}</h3>
                  {event.summary ? (
                    <p className="mt-2 text-sm leading-6">“{event.summary}”</p>
                  ) : null}
                  {event.parsed?.length ? (
                    <div className="mt-2">
                      <p className="text-xs tracking-[0.08em] text-muted">
                        PARSED COMMERCIAL REQUEST
                      </p>
                      <ul className="mt-1 space-y-0.5 text-sm">
                        {event.parsed.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <TermsBlock event={event} />
                  {event.reasons?.length ? (
                    <ul className="mt-2 space-y-1 text-sm text-muted">
                      {event.reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  ) : null}
                  {event.refs?.length ? (
                    <dl className="mt-2 space-y-1 text-xs text-muted">
                      {event.refs.map((ref) => (
                        <div key={ref.label} className="flex gap-2">
                          <dt>{ref.label}</dt>
                          <dd className="font-mono tabular-nums text-ink">
                            {ref.value}
                          </dd>
                        </div>
                      ))}
                    </dl>
                  ) : null}
                </AstraPanel>
              </li>
            ))}
          </ol>
        ) : null}

        {item?.transaction_id || item?.order_number ? (
          <AstraPanel>
            <p className="eyebrow">Transaction</p>
            <dl className="mt-2 space-y-1 text-sm">
              {item.transaction_id ? (
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Transaction</dt>
                  <dd className="font-mono text-xs">{item.transaction_id}</dd>
                </div>
              ) : null}
              {item.order_number ? (
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Order</dt>
                  <dd className="font-mono">{item.order_number}</dd>
                </div>
              ) : null}
              <div className="flex justify-between gap-3">
                <dt className="text-muted">Status</dt>
                <dd>{humanizeEnum(item.status)}</dd>
              </div>
            </dl>
          </AstraPanel>
        ) : null}

        {matched ? (
          <div>
            <button
              type="button"
              className="btn-quiet"
              aria-expanded={showPayload}
              onClick={() => setShowPayload((current) => !current)}
            >
              {showPayload ? "Hide machine payload" : "View machine payload"}
            </button>
            {showPayload ? (
              <pre
                className="mt-2 max-h-80 overflow-auto border border-line bg-canvas p-3 font-mono text-[11px] leading-5"
                tabIndex={0}
              >
                {JSON.stringify(
                  {
                    session_id: matched.session_id,
                    state: matched.state,
                    turns: matched.turns,
                    proposals: matched.proposals.map((proposal) => ({
                      proposal_id: proposal.proposal_id,
                      version: proposal.version,
                      proposal_type: proposal.proposal_type,
                      outcome: proposal.outcome,
                      offer_id: proposal.offer_id,
                      explanation: proposal.explanation,
                      reason_codes: proposal.reason_codes,
                      created_at: proposal.created_at,
                    })),
                  },
                  null,
                  2,
                )}
              </pre>
            ) : null}
          </div>
        ) : null}
      </div>
    </AstraInspector>
  );
}

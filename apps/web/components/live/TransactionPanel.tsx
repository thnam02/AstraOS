"use client";

import { formatAudCents, formatRate } from "@/lib/money";
import type { AcceptProposalResponse, NegotiationResponse } from "@/types";

type Step = "ACCEPTED" | "REVALIDATION" | "RESERVED" | "ORDER CREATED" | "CONFIRMED";

const STEPS: Step[] = [
  "ACCEPTED",
  "REVALIDATION",
  "RESERVED",
  "ORDER CREATED",
  "CONFIRMED",
];

function stepState(
  transaction: AcceptProposalResponse | null,
  label: Step,
): "WAIT" | "ACTIVE" | "PASS" | "FAIL" {
  if (!transaction) {
    return label === "ACCEPTED" ? "ACTIVE" : "WAIT";
  }
  const state = transaction.state;
  const failed = transaction.failure_codes.length > 0;
  if (label === "ACCEPTED") return "PASS";
  if (label === "REVALIDATION") {
    if (!transaction.revalidation) return "ACTIVE";
    return transaction.revalidation.status === "PASSED" ? "PASS" : "FAIL";
  }
  if (label === "RESERVED") {
    if (state === "RESERVATION_FAILED") return "FAIL";
    if (transaction.reservation) return "PASS";
    return state === "READY_TO_RESERVE" || state === "RESERVING" ? "ACTIVE" : "WAIT";
  }
  if (label === "ORDER CREATED") {
    if (state === "ORDER_FAILED") return "FAIL";
    if (transaction.order) return "PASS";
    return state === "CREATING_ORDER" ? "ACTIVE" : "WAIT";
  }
  if (state === "CONFIRMED") return "PASS";
  return failed ? "FAIL" : "WAIT";
}

function mark(status: ReturnType<typeof stepState>): string {
  if (status === "PASS") return "✓";
  if (status === "ACTIVE") return "●";
  if (status === "FAIL") return "!";
  return "○";
}

export function TransactionPanel({
  negotiation,
  transaction,
  busy,
  onExecute,
  onRecover,
  onDemoInventory,
  onDemoDelivery,
  onDemoMargin,
}: {
  negotiation: NegotiationResponse;
  transaction: AcceptProposalResponse | null;
  busy: boolean;
  onExecute: () => void;
  onRecover: () => void;
  onDemoInventory: (units: number) => void;
  onDemoDelivery: (available: boolean) => void;
  onDemoMargin: (rate: number) => void;
}) {
  const offer = negotiation.proposal?.offer;
  const failed = Boolean(transaction && transaction.state !== "CONFIRMED");
  const confirmed = transaction?.state === "CONFIRMED";

  return (
    <section className="space-y-5">
      <div>
        <p className="eyebrow">Transact</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">
          Execution pipeline
        </h2>
        <p className="mt-1 text-sm text-muted">
          Acceptance is not final until live merchant state is revalidated.
          AstraOS does not take payment.
        </p>
      </div>

      <ol className="space-y-2" aria-label="Transaction pipeline">
        {STEPS.map((label, index) => {
          const status = stepState(transaction, label);
          return (
            <li key={label}>
              {index > 0 ? (
                <p className="pl-1 text-muted" aria-hidden>
                  ↓
                </p>
              ) : null}
              <div className="flex items-center justify-between py-1 text-sm">
                <span className="tracking-[0.06em]">
                  <span className="mr-2" aria-hidden>
                    {mark(status)}
                  </span>
                  {label}
                </span>
                <span
                  className={
                    status === "PASS"
                      ? "text-[11px] text-success"
                      : status === "FAIL"
                        ? "text-[11px] text-danger"
                        : "text-[11px] text-muted"
                  }
                >
                  {status}
                </span>
              </div>
              {label === "REVALIDATION" && transaction?.revalidation ? (
                <ul className="mt-1 grid gap-1 pl-6 text-xs sm:grid-cols-2">
                  {transaction.revalidation.checks.map((item) => (
                    <li key={item.check} className="flex justify-between gap-3">
                      <span>{item.check.replaceAll("_", " ")}</span>
                      <span
                        className={
                          item.status === "PASS" ? "text-success" : "text-danger"
                        }
                      >
                        {item.status}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ol>

      {confirmed && transaction?.order ? (
        <div className="bg-canvas px-4 py-3">
          <p className="eyebrow">Confirmed</p>
          <p className="mt-1 font-mono text-xl">{transaction.order.order_number}</p>
          <p className="mt-1 text-sm">{transaction.order.product_name}</p>
          <p className="font-mono text-sm tabular-nums">
            {formatAudCents(transaction.order.total_amount_cents)}
          </p>
        </div>
      ) : null}

      {failed && transaction && !confirmed ? (
        <div>
          <p className="eyebrow text-danger">Proposal cannot be executed</p>
          <p className="mt-2 text-sm">
            {transaction.failure_codes.join(" · ") || transaction.state}
          </p>
          <p className="mt-1 text-xs text-muted">
            The accepted proposal was not silently rewritten.
          </p>
          {transaction.recovery_proposal ? (
            <p className="mt-2 text-sm">
              New proposal #{transaction.recovery_proposal.version} is ready.
            </p>
          ) : null}
          <button
            type="button"
            disabled={busy}
            onClick={onRecover}
            className="btn-ghost mt-3"
          >
            Generate new proposal
          </button>
        </div>
      ) : null}

      {!transaction && offer ? (
        <div>
          <p className="text-sm">{offer.product_name}</p>
          <p className="text-sm text-muted">
            {formatAudCents(offer.pricing.total_price_cents)} · {offer.delivery.name} ·{" "}
            {offer.warranty.months}m
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={onExecute}
            className="btn-primary mt-3"
          >
            {busy ? "Executing…" : "Accept"}
          </button>
        </div>
      ) : null}

      {transaction?.timing ? (
        <p className="text-[11px] text-muted">
          {transaction.timing.total_transaction_ms.toFixed(0)} ms total
        </p>
      ) : null}

      <div>
        <p className="eyebrow">Demo controls</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <button type="button" disabled={busy} onClick={() => onDemoInventory(0)} className="btn-quiet">
            Stock → 0
          </button>
          <button type="button" disabled={busy} onClick={() => onDemoInventory(14)} className="btn-quiet">
            Stock → 14
          </button>
          <button type="button" disabled={busy} onClick={() => onDemoDelivery(false)} className="btn-quiet">
            Same-day full
          </button>
          <button type="button" disabled={busy} onClick={() => onDemoDelivery(true)} className="btn-quiet">
            Same-day available
          </button>
          <button type="button" disabled={busy} onClick={() => onDemoMargin(0.25)} className="btn-quiet">
            Margin {formatRate(0.25)}
          </button>
          <button type="button" disabled={busy} onClick={() => onDemoMargin(0.15)} className="btn-quiet">
            Margin {formatRate(0.15)}
          </button>
        </div>
      </div>
    </section>
  );
}

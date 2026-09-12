"use client";

import { formatAudCents, formatRate } from "@/lib/money";
import type { AcceptProposalResponse, NegotiationResponse } from "@/types";

const STEPS = [
  "BUYER ACCEPTED",
  "REVALIDATING PROPOSAL",
  "RESERVING STOCK",
  "CREATING ORDER",
  "ORDER CONFIRMED",
] as const;

function stepState(
  transaction: AcceptProposalResponse | null,
  label: (typeof STEPS)[number],
): "WAIT" | "ACTIVE" | "PASS" | "FAIL" {
  if (!transaction) {
    return label === "BUYER ACCEPTED" ? "ACTIVE" : "WAIT";
  }
  const state = transaction.state;
  const failed = transaction.failure_codes.length > 0;
  if (label === "BUYER ACCEPTED") return "PASS";
  if (label === "REVALIDATING PROPOSAL") {
    if (!transaction.revalidation) return "ACTIVE";
    return transaction.revalidation.status === "PASSED" ? "PASS" : "FAIL";
  }
  if (label === "RESERVING STOCK") {
    if (state === "RESERVATION_FAILED") return "FAIL";
    if (transaction.reservation) return "PASS";
    return state === "READY_TO_RESERVE" || state === "RESERVING"
      ? "ACTIVE"
      : "WAIT";
  }
  if (label === "CREATING ORDER") {
    if (state === "ORDER_FAILED") return "FAIL";
    if (transaction.order) return "PASS";
    return state === "CREATING_ORDER" ? "ACTIVE" : "WAIT";
  }
  if (state === "CONFIRMED") return "PASS";
  return failed ? "FAIL" : "WAIT";
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
    <section className="panel space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Machine transaction boundary</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
            Transact
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted">
            Acceptance is not final until live merchant state is revalidated.
            AstraOS does not take payment.
          </p>
        </div>
        <p className="font-mono text-[11px] text-muted">
          {transaction?.state ?? negotiation.state}
        </p>
      </div>

      <ol className="space-y-2">
        {STEPS.map((label) => {
          const status = stepState(transaction, label);
          return (
            <li
              key={label}
              className="flex items-center justify-between border border-line px-4 py-2 text-sm"
            >
              <span className="tracking-[0.08em]">{label}</span>
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
            </li>
          );
        })}
      </ol>

      {transaction?.revalidation ? (
        <div className="border border-line px-4 py-3">
          <p className="text-[11px] tracking-[0.14em] text-muted">
            REVALIDATION {transaction.revalidation.status}
          </p>
          <ul className="mt-3 space-y-1 text-sm">
            {transaction.revalidation.checks.map((item) => (
              <li key={item.check} className="flex justify-between gap-3">
                <span>{item.check}</span>
                <span
                  className={
                    item.status === "PASS" ? "text-success" : "text-danger"
                  }
                >
                  {item.status}
                  {item.available_units != null
                    ? ` · ${item.available_units} units`
                    : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {confirmed && transaction?.order ? (
        <div className="border border-ink px-4 py-4">
          <p className="text-[11px] tracking-[0.14em] text-muted">
            ORDER CONFIRMED
          </p>
          <p className="mt-2 font-mono text-lg">{transaction.order.order_number}</p>
          <p className="mt-2 text-sm">{transaction.order.product_name}</p>
          <p className="mt-1 text-sm">
            {formatAudCents(transaction.order.total_amount_cents)}
          </p>
          <p className="mt-1 text-sm text-muted">
            {transaction.order.delivery_code} ·{" "}
            {transaction.order.warranty_months ?? "—"}-month warranty
          </p>
          <p className="mt-3 text-[11px] text-muted">
            Inventory: reserved → {transaction.reservation?.status ?? "CONSUMED"}
          </p>
          <p className="text-[11px] text-muted">
            Payment: {transaction.order.payment_status}
          </p>
        </div>
      ) : null}

      {failed && transaction && !confirmed ? (
        <div className="border border-danger/40 px-4 py-4">
          <p className="text-[11px] tracking-[0.14em] text-danger">
            PROPOSAL CANNOT BE EXECUTED
          </p>
          <p className="mt-2 text-sm">
            {transaction.failure_codes.join(" · ") || transaction.state}
          </p>
          <p className="mt-2 text-xs text-muted">
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
            GENERATE NEW PROPOSAL
          </button>
        </div>
      ) : null}

      {!transaction && offer ? (
        <div className="border border-line px-4 py-4 text-sm">
          <p>{offer.product_name}</p>
          <p className="text-muted">
            {formatAudCents(offer.pricing.total_price_cents)} ·{" "}
            {offer.delivery.name} · {offer.warranty.months}m
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={onExecute}
            className="btn-primary mt-3"
          >
            {busy ? "EXECUTING…" : "EXECUTE ACCEPTANCE"}
          </button>
        </div>
      ) : null}

      {transaction?.timing ? (
        <p className="text-[11px] text-muted">
          {transaction.timing.total_transaction_ms.toFixed(0)} ms total ·
          revalidate {transaction.timing.revalidation_ms.toFixed(0)} · reserve{" "}
          {transaction.timing.reservation_ms.toFixed(0)} · order{" "}
          {transaction.timing.order_creation_ms.toFixed(0)}
        </p>
      ) : null}

      <div className="border border-dashed border-line px-4 py-4">
        <p className="text-[11px] tracking-[0.14em] text-muted">
          HACKATHON DEMO CONTROLS — MUTATES LIVE STATE
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => onDemoInventory(0)}
            className="btn-ghost text-[11px]"
          >
            STOCK → 0
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDemoInventory(14)}
            className="btn-ghost text-[11px]"
          >
            STOCK → 14
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDemoDelivery(false)}
            className="btn-ghost text-[11px]"
          >
            SAME-DAY → FULL
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDemoDelivery(true)}
            className="btn-ghost text-[11px]"
          >
            SAME-DAY → AVAILABLE
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDemoMargin(0.25)}
            className="btn-ghost text-[11px]"
          >
            MARGIN {formatRate(0.25)}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDemoMargin(0.15)}
            className="btn-ghost text-[11px]"
          >
            MARGIN {formatRate(0.15)}
          </button>
        </div>
      </div>
    </section>
  );
}

"use client";

import { StageDisclosure, StageResult, StageSection } from "@/components/live/StageShell";
import { humanizeCheck } from "@/lib/decisionNarrative";
import { formatAudCents, formatRate } from "@/lib/money";
import type { AcceptProposalResponse, NegotiationResponse } from "@/types";

function mark(status: "WAIT" | "ACTIVE" | "PASS" | "FAIL"): string {
  if (status === "PASS") return "✓";
  if (status === "ACTIVE") return "●";
  if (status === "FAIL") return "!";
  return "○";
}

function revalidationState(
  transaction: AcceptProposalResponse | null,
): "WAIT" | "ACTIVE" | "PASS" | "FAIL" {
  if (!transaction?.revalidation) return transaction ? "ACTIVE" : "WAIT";
  return transaction.revalidation.status === "PASSED" ? "PASS" : "FAIL";
}

function reservationState(
  transaction: AcceptProposalResponse | null,
): "WAIT" | "ACTIVE" | "PASS" | "FAIL" {
  if (!transaction) return "WAIT";
  if (transaction.state === "RESERVATION_FAILED") return "FAIL";
  if (transaction.reservation) return "PASS";
  return transaction.state === "READY_TO_RESERVE" || transaction.state === "RESERVING"
    ? "ACTIVE"
    : "WAIT";
}

function orderState(
  transaction: AcceptProposalResponse | null,
): "WAIT" | "ACTIVE" | "PASS" | "FAIL" {
  if (!transaction) return "WAIT";
  if (transaction.state === "ORDER_FAILED") return "FAIL";
  if (transaction.order) return "PASS";
  return transaction.state === "CREATING_ORDER" ? "ACTIVE" : "WAIT";
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
  const status = confirmed
    ? "Confirmed"
    : failed
      ? "Cannot be executed"
      : "Ready for confirmation";
  const reserved = reservationState(transaction);
  const ordered = orderState(transaction);
  const revalidated = revalidationState(transaction);

  return (
    <>
      <StageResult
        label="Accepted agreement"
        title={status}
        value={
          offer
            ? formatAudCents(
                transaction?.order?.total_amount_cents ??
                  offer.pricing.total_price_cents,
              )
            : undefined
        }
        explanation={
          offer ? (
            <p>
              {offer.product_name}
              {transaction?.order?.order_number ? (
                <>
                  <span className="mx-2 text-muted">·</span>
                  {transaction.order.order_number}
                </>
              ) : null}
            </p>
          ) : undefined
        }
        actions={
          <>
            {!transaction && offer ? (
              <button
                type="button"
                disabled={busy}
                onClick={onExecute}
                className="btn-primary"
              >
                {busy ? "Executing…" : "Accept proposal"}
              </button>
            ) : null}
            {failed && transaction && !confirmed ? (
              <button
                type="button"
                disabled={busy}
                onClick={onRecover}
                className="btn-ghost"
              >
                Generate new proposal
              </button>
            ) : null}
          </>
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
                {formatAudCents(
                  transaction?.order?.total_amount_cents ??
                    offer.pricing.total_price_cents,
                )}
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
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Contribution</dt>
              <dd className="font-mono tabular-nums">
                {formatAudCents(offer.contribution_margin_cents)}
              </dd>
            </div>
          </dl>
        ) : null}
        {failed && transaction && !confirmed ? (
          <div className="mt-5">
            <p className="text-sm text-danger">
              {transaction.failure_codes.map(humanizeCheck).join(" · ") ||
                humanizeCheck(transaction.state)}
            </p>
            <p className="mt-1 text-xs text-muted">
              The accepted proposal was not silently rewritten.
            </p>
            {transaction.recovery_proposal ? (
              <p className="mt-2 text-sm">
                New proposal #{transaction.recovery_proposal.version} is ready.
              </p>
            ) : null}
          </div>
        ) : null}
      </StageResult>

      <StageSection title="Revalidation">
        {transaction?.revalidation ? (
          <ul className="space-y-2 text-sm">
            {transaction.revalidation.checks.map((item) => (
              <li key={item.check} className="flex items-baseline justify-between gap-4">
                <span>{humanizeCheck(item.check)}</span>
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
        ) : (
          <p className="text-sm text-muted">
            {mark(revalidated)} Price, inventory, delivery, and merchant policy
            are checked together at execution.
          </p>
        )}
      </StageSection>

      <StageSection title="Execution result">
        <dl className="max-w-md space-y-2 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Inventory reserved</dt>
            <dd>
              {mark(reserved)}{" "}
              {transaction?.reservation?.reservation_id ?? reserved}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Order created</dt>
            <dd>
              {mark(ordered)} {transaction?.order?.status ?? ordered}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Order reference</dt>
            <dd className="font-mono tabular-nums">
              {transaction?.order?.order_number ?? "—"}
            </dd>
          </div>
        </dl>
      </StageSection>

      <StageDisclosure title="Recovery controls">
        <div className="flex flex-wrap gap-2">
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
      </StageDisclosure>
    </>
  );
}

"use client";

import { StageDisclosure, StageResult, StageSection } from "@/components/live/StageShell";
import { humanizeCheck } from "@/lib/decisionNarrative";
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
  const status = confirmed
    ? "Confirmed"
    : failed
      ? "Cannot be executed"
      : "Ready for confirmation";

  return (
    <>
      <StageResult
        label="Transaction status"
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
        metrics={
          offer
            ? [
                {
                  label: "Contribution",
                  value: formatAudCents(offer.contribution_margin_cents),
                },
                {
                  label: "Delivery",
                  value: offer.delivery.name,
                },
                {
                  label: "Warranty",
                  value: `${offer.warranty.months}-month`,
                },
              ]
            : undefined
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
        {failed && transaction && !confirmed ? (
          <div>
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

      {offer ? (
        <StageSection title="Final commercial terms">
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
          </dl>
        </StageSection>
      ) : null}

      <StageDisclosure title="Order pipeline">
        <ol className="space-y-2" aria-label="Transaction pipeline">
          {STEPS.map((label, index) => {
            const statusMark = stepState(transaction, label);
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
                      {mark(statusMark)}
                    </span>
                    {label}
                  </span>
                  <span
                    className={
                      statusMark === "PASS"
                        ? "text-[11px] text-success"
                        : statusMark === "FAIL"
                          ? "text-[11px] text-danger"
                          : "text-[11px] text-muted"
                    }
                  >
                    {statusMark}
                  </span>
                </div>
                {label === "REVALIDATION" && transaction?.revalidation ? (
                  <ul className="mt-1 grid gap-1 pl-6 text-xs sm:grid-cols-2">
                    {transaction.revalidation.checks.map((item) => (
                      <li key={item.check} className="flex justify-between gap-3">
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
                ) : null}
              </li>
            );
          })}
        </ol>
      </StageDisclosure>

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

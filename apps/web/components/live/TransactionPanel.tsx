"use client";

import { useState } from "react";

import { AstraPanel } from "@/components/astra";

import {
  StageDisclosure,
  StageResult,
  StageSection,
  StageSplit,
} from "@/components/live/StageShell";
import { humanizeCheck } from "@/lib/decisionNarrative";
import { humanizeEnum } from "@/lib/format";
import { formatAudCents, formatRate } from "@/lib/money";
import type { AcceptProposalResponse, NegotiationResponse } from "@/types";

function mark(status: "WAIT" | "ACTIVE" | "PASS" | "FAIL"): string {
  if (status === "PASS") return "✓";
  if (status === "ACTIVE") return "●";
  if (status === "FAIL") return "!";
  return "○";
}

function stepLabel(status: "WAIT" | "ACTIVE" | "PASS" | "FAIL"): string {
  if (status === "WAIT") return "Waiting";
  if (status === "ACTIVE") return "In progress";
  if (status === "PASS") return "Passed";
  return "Failed";
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
  return transaction.state === "READY_TO_RESERVE" ||
    transaction.state === "RESERVING"
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
  const [checkPage, setCheckPage] = useState(0);
  const checks = [...(transaction?.revalidation?.checks ?? [])].sort(
    (a, b) => Number(b.status === "FAIL") - Number(a.status === "FAIL"),
  );
  const lastCheckPage = Math.max(0, Math.ceil(checks.length / 8) - 1);
  const activeCheckPage = Math.min(checkPage, lastCheckPage);
  const visibleChecks = checks.slice(
    activeCheckPage * 8,
    (activeCheckPage + 1) * 8,
  );
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
    <StageSplit stretch>
      <div className="space-y-3">
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
              <p className="break-words">{offer.product_name}</p>
            ) : undefined
          }
          actions={
            <div className="flex min-h-10 flex-wrap items-center gap-3">
              {confirmed ? (
                <p className="text-sm font-medium text-success">
                  ✓ Order confirmed
                </p>
              ) : null}
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
            </div>
          }
        >
          {offer ? (
            <dl className="space-y-2 text-sm [&_dd]:min-w-0 [&_dd]:break-words [&_dd]:text-right">
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
                <dt className="text-muted">Product</dt>
                <dd>{offer.product_name}</dd>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
                <dt className="text-muted">Final price</dt>
                <dd className="font-mono tabular-nums">
                  {formatAudCents(
                    transaction?.order?.total_amount_cents ??
                      offer.pricing.total_price_cents,
                  )}
                </dd>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
                <dt className="text-muted">Delivery</dt>
                <dd>{offer.delivery.name}</dd>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
                <dt className="text-muted">Warranty</dt>
                <dd>{offer.warranty.months}-month</dd>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
                <dt className="text-muted">Bundle</dt>
                <dd>{offer.bundle?.name ?? "None"}</dd>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
                <dt className="text-muted">Returns</dt>
                <dd>
                  {offer.returns?.window_days
                    ? `${offer.returns.window_days}-day`
                    : "Standard"}
                </dd>
              </div>
              <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
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
                  New proposal #{transaction.recovery_proposal.version} is
                  ready.
                </p>
              ) : null}
            </div>
          ) : null}
        </StageResult>

        <StageSection title="Execution result">
          <dl className="space-y-2 text-sm [&_dd]:min-w-0 [&_dd]:break-words [&_dd]:text-right">
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
              <dt className="text-muted">Inventory reserved</dt>
              <dd>
                {mark(reserved)} {stepLabel(reserved)}
              </dd>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
              <dt className="text-muted">Order created</dt>
              <dd>
                {mark(ordered)}{" "}
                {transaction?.order?.status
                  ? humanizeEnum(transaction.order.status)
                  : stepLabel(ordered)}
              </dd>
            </div>
            <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)] gap-3">
              <dt className="text-muted">Order reference</dt>
              <dd className="font-mono tabular-nums">
                {transaction?.order?.order_number ?? "—"}
              </dd>
            </div>
          </dl>
          {transaction?.reservation?.reservation_id ? (
            <StageDisclosure title="Reservation details">
              <p className="text-sm text-muted">Reservation reference</p>
              <p className="mt-1 break-all font-mono text-sm">
                {transaction.reservation.reservation_id}
              </p>
            </StageDisclosure>
          ) : null}
        </StageSection>
        <StageDisclosure title="Recovery controls">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => onDemoInventory(0)}
              className="btn-quiet"
            >
              Stock → 0
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDemoInventory(14)}
              className="btn-quiet"
            >
              Stock → 14
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDemoDelivery(false)}
              className="btn-quiet"
            >
              Same-day full
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDemoDelivery(true)}
              className="btn-quiet"
            >
              Same-day available
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDemoMargin(0.25)}
              className="btn-quiet"
            >
              Margin {formatRate(0.25)}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onDemoMargin(0.15)}
              className="btn-quiet"
            >
              Margin {formatRate(0.15)}
            </button>
          </div>
        </StageDisclosure>
      </div>
      <AstraPanel className="flex min-w-0 flex-col">
        <p className="eyebrow">Revalidation</p>
        <p className="mt-2 text-sm text-muted" aria-live="polite">
          {transaction?.revalidation
            ? `${checks.filter((item) => item.status === "PASS").length} of ${checks.length} checks passed · ${humanizeEnum(transaction.revalidation.status)}`
            : busy
              ? "Checking the accepted agreement…"
              : "Checks run when you accept the proposal."}
        </p>
        <div className="mt-3 flex min-h-72 flex-1 flex-col">
          {transaction?.revalidation ? (
            <ul className="grid flex-1 grid-rows-4 gap-x-4 sm:grid-cols-2">
              {visibleChecks.map((item) => (
                <li
                  key={item.check}
                  className="flex min-w-0 flex-col justify-center gap-1 border-b border-line-muted py-2 text-sm"
                >
                  <span className="break-words">
                    {humanizeCheck(item.check)}
                  </span>
                  <span
                    className={
                      item.status === "PASS" ? "text-success" : "text-danger"
                    }
                  >
                    {mark(item.status)} {humanizeEnum(item.status)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="grid flex-1 grid-rows-2 gap-3 sm:grid-cols-2">
              {["Price", "Inventory", "Delivery", "Merchant policy"].map(
                (label) => (
                  <div
                    key={label}
                    className="flex flex-col justify-center border-b border-line-muted text-sm"
                  >
                    <p>{label}</p>
                    <p className="mt-1 text-muted">
                      {mark(revalidated)}{" "}
                      {busy ? "In progress" : "Pending execution"}
                    </p>
                  </div>
                ),
              )}
            </div>
          )}
          <nav
            className="mt-3 flex min-h-9 items-center justify-between gap-2 text-xs"
            aria-label="Revalidation pages"
          >
            <button
              type="button"
              className="btn-quiet disabled:opacity-40"
              disabled={activeCheckPage === 0}
              onClick={() => setCheckPage(activeCheckPage - 1)}
            >
              Previous
            </button>
            <span className="text-muted">
              {checks.length
                ? `${activeCheckPage * 8 + 1}–${Math.min((activeCheckPage + 1) * 8, checks.length)} of ${checks.length}`
                : "Awaiting checks"}
            </span>
            <button
              type="button"
              className="btn-quiet disabled:opacity-40"
              disabled={activeCheckPage === lastCheckPage}
              onClick={() => setCheckPage(activeCheckPage + 1)}
            >
              Next
            </button>
          </nav>
        </div>
      </AstraPanel>
    </StageSplit>
  );
}

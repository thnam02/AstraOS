import { FitBar } from "@/components/arena/FitBar";
import { AstraStatusBadge } from "@/components/astra";
import {
  bundleLabel,
  deliveryLabel,
  isSelectable,
  offerDiff,
  policyReasons,
  returnsLabel,
  strategyTitle,
  STRATEGY_META,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import { formatUtilityShort } from "@/lib/format";
import { formatAudCents } from "@/lib/money";
import type { ArenaStrategyResponse } from "@/types";

export function StrategyCard({
  response,
  selected,
  reference,
  fitDelta,
  contributionDelta,
}: {
  response: ArenaStrategyResponse;
  selected: boolean;
  reference?: ArenaStrategyResponse | null;
  fitDelta?: string;
  contributionDelta?: string;
}) {
  const meta = STRATEGY_META[response.strategy_name];
  const valid = isSelectable(response);
  const reasons = policyReasons(response.failure_reason);
  const diff = offerDiff(response, reference ?? null);

  return (
    <article
      className={`flex h-full flex-col border bg-surface px-4 py-4 ${
        selected
          ? "border-ink"
          : valid
            ? "border-line"
            : "border-warning/40 bg-canvas"
      }`}
      aria-current={selected ? "true" : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="eyebrow" title={meta?.tooltip}>
            {strategyTitle(response.strategy_name)}
          </p>
          <p className="mt-1 text-[11px] text-muted">{meta?.subtitle}</p>
        </div>
        {selected ? (
          <span className="text-[11px] font-medium tracking-[0.06em] text-success">
            WON
          </span>
        ) : null}
      </div>

      {valid ? (
        <ValidBody
          response={response}
          selected={selected}
          diff={diff}
          fitDelta={fitDelta}
          contributionDelta={contributionDelta}
        />
      ) : (
        <BlockedBody response={response} reasons={reasons} diff={diff} />
      )}
    </article>
  );
}

function ValidBody({
  response,
  selected,
  diff,
  fitDelta,
  contributionDelta,
}: {
  response: ArenaStrategyResponse;
  selected: boolean;
  diff: ReturnType<typeof offerDiff>;
  fitDelta?: string;
  contributionDelta?: string;
}) {
  return (
    <div className="mt-3 flex flex-1 flex-col justify-between gap-4">
      <OfferSchema
        response={response}
        diff={diff}
        emphasizeChanged
      />
      <div className="space-y-3">
        {response.buyer_utility != null ? (
          <div>
            <FitBar value={response.buyer_utility} compact={!selected} />
            {selected && fitDelta ? (
              <p className="mt-1 text-xs text-muted">{fitDelta} vs next best</p>
            ) : null}
          </div>
        ) : null}
        <SchemaEconomics
          response={response}
          contributionDelta={selected ? contributionDelta : undefined}
        />
        <PolicyStatus safe />
      </div>
    </div>
  );
}

function BlockedBody({
  response,
  reasons,
  diff,
}: {
  response: ArenaStrategyResponse;
  reasons: string[];
  diff: ReturnType<typeof offerDiff>;
}) {
  const hasOfferShape =
    response.product_name != null ||
    response.total_customer_price_cents != null ||
    response.delivery != null;

  return (
    <div className="mt-4 flex flex-1 flex-col justify-between gap-4">
      <div className="space-y-3">
        <p className="text-sm font-semibold">No policy-safe offer</p>
        {hasOfferShape ? (
          <OfferSchema response={response} diff={diff} />
        ) : null}
        {response.buyer_utility != null ? (
          <div className="flex justify-between gap-3 text-sm">
            <span className="text-muted">Buyer Utility</span>
            <span className="font-mono tabular-nums">
              {formatUtilityShort(response.buyer_utility)}
            </span>
          </div>
        ) : null}
        <SchemaEconomics response={response} />
        {reasons.length ? (
          <div>
            <p className="text-[11px] text-muted">Blocked by</p>
            <ul className="mt-1 space-y-1 text-sm">
              {reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <div className="space-y-2">
        <PolicyStatus safe={false} />
        <p className="text-xs text-muted">
          This strategy does not enter buyer selection.
        </p>
      </div>
    </div>
  );
}

function OfferSchema({
  response,
  diff,
  emphasizeChanged = false,
}: {
  response: ArenaStrategyResponse;
  diff: ReturnType<typeof offerDiff>;
  emphasizeChanged?: boolean;
}) {
  const rows: {
    label: string;
    value: string | null;
    changed?: boolean;
    mono?: boolean;
  }[] = [
    {
      label: "Product",
      value: response.product_name
        ? response.sku
          ? `${response.product_name} · ${response.sku}`
          : response.product_name
        : response.sku,
      changed: diff.productChanged,
    },
    {
      label: "Price",
      value:
        response.total_customer_price_cents != null
          ? formatAudCents(response.total_customer_price_cents)
          : null,
      changed: diff.priceChanged,
      mono: true,
    },
    {
      label: "Delivery",
      value:
        response.delivery != null || response.delivery_days != null
          ? deliveryLabel(response.delivery, response.delivery_days)
          : null,
      changed: diff.deliveryChanged,
    },
    {
      label: "Warranty",
      value:
        response.warranty != null || response.warranty_months != null
          ? warrantyLabel(response.warranty, response.warranty_months)
          : null,
      changed: diff.warrantyChanged,
    },
    {
      label: "Bundle",
      value:
        response.bundle != null || response.offer_id
          ? bundleLabel(response.bundle)
          : null,
      changed: diff.bundleChanged,
    },
    {
      label: "Returns",
      value: response.returns != null ? returnsLabel(response.returns) : null,
      changed: diff.returnsChanged,
    },
  ];

  return (
    <dl className="space-y-1 text-sm">
      {rows
        .filter((row) => row.value != null)
        .map((row) => {
          const changed = emphasizeChanged && row.changed;
          return (
            <div key={row.label} className="flex justify-between gap-3">
              <dt className="text-muted">{row.label}</dt>
              <dd
                className={`text-right ${row.mono ? "font-mono tabular-nums" : ""} ${
                  changed ? "font-medium" : ""
                }`}
              >
                {row.value}
                {changed ? " ↑" : ""}
              </dd>
            </div>
          );
        })}
    </dl>
  );
}

function SchemaEconomics({
  response,
  contributionDelta,
}: {
  response: ArenaStrategyResponse;
  contributionDelta?: string;
}) {
  return (
    <dl className="space-y-1 text-sm">
      {response.merchant_contribution_cents != null ? (
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Contribution</dt>
          <dd className="text-right">
            <span className="font-mono tabular-nums">
              {formatAudCents(response.merchant_contribution_cents)}
            </span>
            {contributionDelta ? (
              <span className="block text-[11px] text-muted">
                {contributionDelta} vs cheapest valid
              </span>
            ) : null}
          </dd>
        </div>
      ) : null}
      {response.intervention_cost_cents != null ? (
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Intervention</dt>
          <dd className="font-mono tabular-nums">
            {formatAudCents(response.intervention_cost_cents)}
          </dd>
        </div>
      ) : null}
    </dl>
  );
}

function PolicyStatus({ safe }: { safe: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-muted">Policy Status</span>
      <AstraStatusBadge tone={safe ? "positive" : "warning"}>
        {safe ? "Policy safe" : "No safe offer"}
      </AstraStatusBadge>
    </div>
  );
}

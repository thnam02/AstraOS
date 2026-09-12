import { FitBar } from "@/components/arena/FitBar";
import {
  bundleLabel,
  deliveryLabel,
  isSelectable,
  offerDiff,
  policyReasons,
  strategyTitle,
  STRATEGY_META,
  warrantyLabel,
} from "@/lib/arenaDisplay";
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
        <BlockedBody
          response={response}
          reasons={reasons}
        />
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
      <div>
        <h3 className="text-base font-semibold tracking-tight">
          {response.product_name}
        </h3>
        <p className="font-mono text-[11px] text-muted">{response.sku}</p>
        <p className="mt-2 font-mono text-xl font-semibold tabular-nums">
          {formatAudCents(response.total_customer_price_cents ?? 0)}
        </p>
        <ul className="mt-2 space-y-0.5 text-sm">
          <li className={diff.deliveryChanged ? "font-medium" : "text-muted"}>
            {deliveryLabel(response.delivery, response.delivery_days)}
            {diff.deliveryChanged ? " ↑" : ""}
          </li>
          <li className={diff.warrantyChanged ? "font-medium" : "text-muted"}>
            {warrantyLabel(response.warranty, response.warranty_months)}
            {diff.warrantyChanged ? " ↑" : ""}
          </li>
          <li className={diff.bundleChanged ? "font-medium" : "text-muted"}>
            {bundleLabel(response.bundle)}
            {diff.bundleChanged && response.bundle ? " +" : ""}
          </li>
        </ul>
      </div>
      <div className="space-y-3">
        <FitBar value={response.buyer_utility ?? 0} compact={!selected} />
        {selected && fitDelta ? (
          <p className="text-xs text-muted">{fitDelta} vs next best</p>
        ) : null}
        <dl className="space-y-1 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Merchant contribution</dt>
            <dd className="text-right">
              <span className="font-mono tabular-nums">
                {formatAudCents(response.merchant_contribution_cents ?? 0)}
              </span>
              {selected && contributionDelta ? (
                <span className="block text-[11px] text-muted">
                  {contributionDelta} vs cheapest valid
                </span>
              ) : null}
            </dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted">Intervention cost</dt>
            <dd className="font-mono tabular-nums">
              {formatAudCents(response.intervention_cost_cents ?? 0)}
            </dd>
          </div>
        </dl>
        <p className="text-[11px] tracking-[0.06em] text-success">POLICY SAFE</p>
      </div>
    </div>
  );
}

function BlockedBody({
  response,
  reasons,
}: {
  response: ArenaStrategyResponse;
  reasons: string[];
}) {
  return (
    <div className="mt-4 flex flex-1 flex-col justify-between gap-4">
      <div>
        <p className="text-sm font-semibold">No policy-safe offer</p>
        {response.total_customer_price_cents != null ? (
          <p className="mt-2 text-sm">
            Attempted{" "}
            <span className="font-mono tabular-nums">
              {formatAudCents(response.total_customer_price_cents)}
            </span>
          </p>
        ) : null}
        {response.product_name ? (
          <p className="mt-1 text-xs text-muted">{response.product_name}</p>
        ) : null}
        {reasons.length ? (
          <div className="mt-3">
            <p className="text-[11px] text-muted">Blocked by</p>
            <ul className="mt-1 space-y-1 text-sm">
              {reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <p className="text-xs text-muted">
        This strategy does not enter buyer selection.
      </p>
    </div>
  );
}

"use client";

import { formatAudCents, formatRate } from "@/lib/money";
import type { BuyerProfile, OptimisationResponse } from "@/types";

import { ParetoChart } from "./ParetoChart";

const PROFILES: { id: BuyerProfile; label: string }[] = [
  { id: "INTENT_ADAPTED", label: "Intent-adapted" },
  { id: "BALANCED", label: "Balanced" },
  { id: "URGENT_TRAVELLER", label: "Urgent traveller" },
  { id: "BUDGET_SHOPPER", label: "Budget" },
  { id: "ASSURANCE_BUYER", label: "Assurance" },
  { id: "QUALITY_FIRST", label: "Quality first" },
];

const WEIGHT_LABELS: Record<string, string> = {
  product: "Product fit",
  price: "Price",
  delivery: "Delivery",
  warranty: "Warranty",
  bundle: "Bundle",
  returns: "Returns",
};

export function OptimisationPanel({
  optimisation,
  profile,
  onProfile,
  busy,
}: {
  optimisation: OptimisationResponse;
  profile: BuyerProfile;
  onProfile: (profile: BuyerProfile) => void;
  busy: boolean;
}) {
  const rec = optimisation.recommended_offer;
  const weights = optimisation.buyer_model.weights;

  return (
    <section className="space-y-5 border border-line bg-surface px-5 py-5">
      <div>
        <p className="text-[11px] font-medium tracking-[0.14em] text-muted">
          PARETO FRONTIER
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">
          Efficient trade-offs
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          {optimisation.summary.offers_considered.toLocaleString()} constructed
          {" → "}
          {optimisation.summary.policy_safe.toLocaleString()} policy-safe
          {" → "}
          {optimisation.summary.pareto_efficient.toLocaleString()} Pareto-efficient
        </p>
      </div>

      {optimisation.failure && !rec ? (
        <div className="border border-danger px-4 py-3 text-sm">
          <p className="tracking-[0.12em] text-danger">NO POLICY-SAFE OFFER</p>
          <p className="mt-2">{optimisation.failure.message}</p>
          {optimisation.failure.requested_max_price_cents != null ? (
            <p className="mt-2 text-muted">
              Requested ≤{" "}
              {formatAudCents(optimisation.failure.requested_max_price_cents)}
              {optimisation.failure.lowest_constructed_price_cents != null
                ? ` · lowest constructed ${formatAudCents(optimisation.failure.lowest_constructed_price_cents)}`
                : ""}
            </p>
          ) : null}
        </div>
      ) : null}

      <ParetoChart points={optimisation.plot_points} />
      <p className="text-[11px] text-muted">
        Muted = dominated · black = Pareto-efficient · green = AstraOS response.
        Bubble size is intervention cost. Utility is a simulation, not a
        probability.
      </p>

      <div className="grid gap-5 lg:grid-cols-[minmax(260px,0.9fr)_minmax(320px,1.2fr)]">
        <div className="space-y-4">
          <div>
            <p className="text-[11px] tracking-[0.14em] text-muted">
              SIMULATED BUYER MODEL
            </p>
            <p className="mt-1 text-xs text-muted">
              Cold-start simulation — not real agent probability.
            </p>
            <label className="mt-3 block text-xs text-muted">
              Profile
              <select
                value={profile}
                onChange={(event) =>
                  onProfile(event.target.value as BuyerProfile)
                }
                disabled={busy}
                className="mt-1 w-full border border-line bg-surface px-2 py-1 text-sm text-ink"
              >
                {PROFILES.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <dl className="mt-3 space-y-1 text-sm">
              {Object.entries(WEIGHT_LABELS).map(([key, label]) => (
                <div key={key} className="flex justify-between gap-3">
                  <dt className="text-muted">{label}</dt>
                  <dd className="tabular-nums">
                    {Math.round((weights[key] ?? 0) * 100)}%
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          {rec ? (
            <div className="border border-line px-4 py-4">
              <p className="text-[11px] tracking-[0.14em] text-muted">
                ASTRAOS RESPONSE
              </p>
              <h3 className="mt-2 text-lg font-semibold">{rec.product_name}</h3>
              <p className="font-mono text-[11px] text-muted">{rec.sku}</p>
              <p className="mt-2 text-sm">
                {formatAudCents(rec.pricing.total_price_cents)} · {rec.delivery.name} ·{" "}
                {rec.warranty.months} months · {rec.bundle?.name ?? "No bundle"}
              </p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt className="text-[11px] text-muted">SIMULATED UTILITY</dt>
                  <dd className="tabular-nums">{rec.buyer_utility.toFixed(3)}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted">CONTRIBUTION</dt>
                  <dd className="tabular-nums">
                    {formatAudCents(rec.contribution_margin_cents)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted">INTERVENTION</dt>
                  <dd className="tabular-nums">
                    {formatAudCents(rec.incremental_intervention_cost_cents)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted">MARGIN</dt>
                  <dd className="tabular-nums">
                    {formatRate(rec.contribution_margin_rate)}
                  </dd>
                </div>
              </dl>
              <p className="mt-4 text-[11px] tracking-[0.12em] text-muted">
                WHY THIS OFFER?
              </p>
              <ul className="mt-2 space-y-2 text-sm">
                {optimisation.explanation.map((reason) => (
                  <li key={reason}>✓ {reason}</li>
                ))}
              </ul>
              {rec.utility_trace.components.length ? (
                <div className="mt-4">
                  <p className="text-[11px] tracking-[0.12em] text-muted">
                    UTILITY TRACE
                  </p>
                  <ul className="mt-1 space-y-1 text-xs text-muted">
                    {rec.utility_trace.components.map((item) => (
                      <li key={item.component}>
                        {item.component}: {item.fit.toFixed(2)} × {item.weight.toFixed(2)}{" "}
                        = {item.weighted.toFixed(4)}
                      </li>
                    ))}
                    <li>total {rec.utility_trace.total.toFixed(4)}</li>
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <div>
          <p className="text-[11px] tracking-[0.14em] text-muted">
            WHAT SHOULD THE MERCHANT CHANGE?
          </p>
          <p className="mt-1 text-xs text-muted">
            Single-lever counterfactuals from the conceptual baseline. Not a
            recommended ranking.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-xs">
              <thead>
                <tr className="border-b border-line text-[11px] tracking-[0.08em] text-muted">
                  <th className="py-2 font-medium">Intervention</th>
                  <th className="py-2 font-medium">Utility</th>
                  <th className="py-2 font-medium">Δ U</th>
                  <th className="py-2 font-medium">Contribution</th>
                  <th className="py-2 font-medium">Δ C</th>
                  <th className="py-2 font-medium">Cost</th>
                  <th className="py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {optimisation.counterfactuals.map((row) => {
                  const highlight =
                    row.lever === "delivery" && row.delivery_code === "SAME_DAY";
                  return (
                    <tr
                      key={`${row.lever}-${row.label}-${row.offer_id}`}
                      className={`border-b border-line ${highlight ? "bg-canvas" : ""}`}
                    >
                      <td className="py-2">{row.label}</td>
                      <td className="py-2 tabular-nums">{row.buyer_utility.toFixed(3)}</td>
                      <td className="py-2 tabular-nums">
                        {row.delta_utility >= 0 ? "+" : ""}
                        {row.delta_utility.toFixed(3)}
                      </td>
                      <td className="py-2 tabular-nums">
                        {formatAudCents(row.contribution_margin_cents)}
                      </td>
                      <td className="py-2 tabular-nums">
                        {formatAudCents(row.delta_contribution_cents)}
                      </td>
                      <td className="py-2 tabular-nums">
                        {formatAudCents(row.incremental_intervention_cost_cents)}
                      </td>
                      <td className="py-2">
                        {row.policy_safe ? "safe" : "blocked"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[11px] text-muted">
            {optimisation.timing.total_optimisation_ms.toFixed(0)} ms ·
            economics {optimisation.timing.economics_ms.toFixed(0)} ·
            policy {optimisation.timing.policy_filter_ms.toFixed(0)} ·
            utility {optimisation.timing.utility_ms.toFixed(0)} ·
            pareto {optimisation.timing.pareto_ms.toFixed(0)}
          </p>
        </div>
      </div>
    </section>
  );
}

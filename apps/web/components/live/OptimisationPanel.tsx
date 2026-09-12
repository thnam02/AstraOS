"use client";

import { Disclosure } from "@/components/shared/Disclosure";
import { StatStrip } from "@/components/shared/StatStrip";
import { formatAudCents } from "@/lib/money";
import type { BuyerProfile, OptimisationResponse } from "@/types";

import { RecommendedOffer } from "./RecommendedOffer";

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
  showRecommendation = true,
}: {
  optimisation: OptimisationResponse;
  profile: BuyerProfile;
  onProfile: (profile: BuyerProfile) => void;
  busy: boolean;
  showRecommendation?: boolean;
}) {
  const rec = optimisation.recommended_offer;
  const weights = optimisation.buyer_model.weights;

  return (
    <section className="space-y-4">
      <div>
        <p className="eyebrow">Optimise</p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">
          Pareto frontier
        </h2>
        <div className="mt-3">
          <StatStrip
            items={[
              { label: "Constructed", value: optimisation.summary.offers_considered },
              { label: "Policy-safe", value: optimisation.summary.policy_safe },
              { label: "Frontier", value: optimisation.summary.pareto_efficient },
            ]}
          />
        </div>
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
      <p className="text-sm text-muted">
        Offers on the frontier cannot improve buyer fit without sacrificing
        merchant contribution, or improve contribution without sacrificing
        buyer fit.
      </p>
      <p className="text-[11px] text-muted">
        Muted = dominated · black = Pareto-efficient · green = AstraOS response.
        Bubble size is intervention cost. Buyer utility is a cold-start
        simulation, not a purchase probability.
      </p>

      <div className="flex flex-wrap items-end gap-4">
        <label className="text-xs text-muted">
          Simulated buyer profile
          <select
            value={profile}
            onChange={(event) => onProfile(event.target.value as BuyerProfile)}
            disabled={busy}
            className="control mt-1 block px-2 py-1 text-sm"
          >
            {PROFILES.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <Disclosure title="Weight mix">
          <dl className="space-y-1 text-sm">
            {Object.entries(WEIGHT_LABELS).map(([key, label]) => (
              <div key={key} className="flex justify-between gap-3">
                <dt className="text-muted">{label}</dt>
                <dd className="tabular-nums">
                  {Math.round((weights[key] ?? 0) * 100)}%
                </dd>
              </div>
            ))}
          </dl>
        </Disclosure>
      </div>

      {showRecommendation && rec ? (
        <div className="border border-line px-4 py-4">
          <RecommendedOffer offer={rec} explanation={optimisation.explanation} />
        </div>
      ) : null}

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
    </section>
  );
}

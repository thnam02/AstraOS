"use client";

import { Disclosure } from "@/components/shared/Disclosure";
import { StatStrip } from "@/components/shared/StatStrip";
import { counterfactualStory } from "@/lib/decisionNarrative";
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
  selectedOfferId,
  onSelectOffer,
  presentation = false,
  productSummary,
}: {
  optimisation: OptimisationResponse;
  profile: BuyerProfile;
  onProfile: (profile: BuyerProfile) => void;
  busy: boolean;
  showRecommendation?: boolean;
  selectedOfferId?: string | null;
  onSelectOffer?: (offerId: string) => void;
  presentation?: boolean;
  productSummary?: string;
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
        {productSummary ? (
          <p className="mt-1 text-xs text-muted">{productSummary}</p>
        ) : null}
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

      <ParetoChart
        points={optimisation.plot_points}
        selectedOfferId={selectedOfferId}
        onSelect={onSelectOffer}
      />
      <p className="text-sm text-muted">
        Frontier offers cannot improve buyer fit without sacrificing merchant
        contribution, or the reverse.
      </p>

      {!presentation ? (
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
      ) : null}

      {showRecommendation && rec ? (
        <div className="border border-line px-4 py-4">
          <RecommendedOffer offer={rec} explanation={optimisation.explanation} />
        </div>
      ) : null}

      <CounterfactualStory rows={optimisation.counterfactuals} />

      {!presentation ? (
        <Disclosure title="All counterfactual levers">
          <table className="w-full min-w-[640px] text-left text-xs">
            <thead>
              <tr className="border-b border-line text-muted">
                <th className="py-2 font-medium">Intervention</th>
                <th className="py-2 font-medium">Utility</th>
                <th className="py-2 font-medium">Δ U</th>
                <th className="py-2 font-medium">Contribution</th>
                <th className="py-2 font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {optimisation.counterfactuals.map((row) => (
                <tr key={`${row.lever}-${row.label}-${row.offer_id}`} className="border-b border-line">
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
                    {formatAudCents(row.incremental_intervention_cost_cents)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Disclosure>
      ) : null}
    </section>
  );
}

function CounterfactualStory({
  rows,
}: {
  rows: OptimisationResponse["counterfactuals"];
}) {
  const story = counterfactualStory(rows);
  if (!story) return null;
  return (
    <div className="bg-canvas px-4 py-3 text-sm">
      <p className="eyebrow">Discount vs delivery</p>
      <div className="mt-2 grid gap-3 md:grid-cols-3">
        <div>
          <p className="text-xs text-muted">Baseline</p>
          <p className="font-mono tabular-nums">
            {formatAudCents(story.baseline.total_price_cents)} ·{" "}
            {story.baseline.delivery_code.replaceAll("_", " ").toLowerCase()} ·
            fit {story.baseline.buyer_utility.toFixed(2)} ·{" "}
            {formatAudCents(story.baseline.contribution_margin_cents)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">Option A — discount</p>
          <p className="font-mono tabular-nums">
            Fit {story.discount.delta_utility >= 0 ? "+" : ""}
            {story.discount.delta_utility.toFixed(2)} · cost{" "}
            {formatAudCents(story.discount.incremental_intervention_cost_cents)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">Option B — faster delivery</p>
          <p className="font-mono tabular-nums">
            Fit {story.delivery.delta_utility >= 0 ? "+" : ""}
            {story.delivery.delta_utility.toFixed(2)} · cost{" "}
            {formatAudCents(story.delivery.incremental_intervention_cost_cents)}
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm">
        AstraOS chooses {story.choosesDelivery ? "faster delivery" : "discount"}.
        More buyer-fit gain per unit of merchant sacrifice.
      </p>
    </div>
  );
}

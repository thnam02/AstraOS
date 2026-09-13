"use client";

import { useMemo, useState } from "react";

import { StatStrip } from "@/components/shared/StatStrip";
import { getOffer, getOfferRun } from "@/lib/api";
import {
  bundleLabel,
  deliveryLabel,
  feasibilityLabel,
  returnsLabel,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import { constructStory, dimensionLine, expansionSteps } from "@/lib/decisionNarrative";
import { contextLabel, intentPriceCeilingCents } from "@/lib/intent";
import { centsToPlainDollars, formatAudCents } from "@/lib/money";
import type {
  GenerateOffersResponse,
  OfferDetailResponse,
  OfferRunResponse,
  OptimisationResponse,
  PublicOffer,
} from "@/types";

const DEFAULT_STATUS = "FEASIBLE";

export function OfferExplorer({
  construction,
  heroProduct,
  policySafe,
  pareto,
  explorerOnly = false,
}: {
  construction: GenerateOffersResponse;
  heroProduct?: string;
  policySafe?: number;
  pareto?: number;
  explorerOnly?: boolean;
}) {
  const [status, setStatus] = useState(DEFAULT_STATUS);
  const [productId, setProductId] = useState("");
  const [delivery, setDelivery] = useState("");
  const [warranty, setWarranty] = useState("");
  const [bundle, setBundle] = useState("");
  const [returns, setReturns] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [run, setRun] = useState<OfferRunResponse | null>(null);
  const [detail, setDetail] = useState<OfferDetailResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const rows = run?.offers ?? construction.offers;
  const story = constructStory(construction);
  const priceCeiling = intentPriceCeilingCents(construction.intent);
  const steps = expansionSteps(construction, {
    summary: {
      policy_safe: policySafe,
      pareto_efficient: pareto,
    },
  } as OptimisationResponse);

  async function applyFilters() {
    setBusy(true);
    try {
      const dollars = Number.parseFloat(maxPrice);
      setRun(
        await getOfferRun(construction.offer_run_id, {
          status,
          product_id: productId || undefined,
          delivery: delivery || undefined,
          warranty: warranty || undefined,
          bundle: bundle || undefined,
          returns: returns || undefined,
          max_price_cents: Number.isFinite(dollars)
            ? Math.round(dollars * 100)
            : undefined,
          limit: 40,
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  function clearFilters() {
    setStatus(DEFAULT_STATUS);
    setProductId("");
    setDelivery("");
    setWarranty("");
    setBundle("");
    setReturns("");
    setMaxPrice("");
    setRun(null);
  }

  const products = useMemo(() => {
    const seen = new Map<string, string>();
    for (const item of construction.offers) {
      seen.set(item.product.product_id, item.product.name);
    }
    return [...seen.entries()];
  }, [construction.offers]);
  const deliveryOptions = useMemo(
    () => uniqueCodes(construction.offers, (offer) => offer.delivery.code),
    [construction.offers],
  );
  const warrantyOptions = useMemo(
    () => uniqueCodes(construction.offers, (offer) => offer.warranty.code),
    [construction.offers],
  );
  const bundleOptions = useMemo(
    () => uniqueCodes(construction.offers, (offer) => offer.bundle?.code ?? "NONE"),
    [construction.offers],
  );
  const returnsOptions = useMemo(
    () => uniqueCodes(construction.offers, (offer) => offer.returns?.code ?? ""),
    [construction.offers],
  );
  const featured = heroProduct ?? products[0]?.[1] ?? "Matched product";

  const viewProductCount = useMemo(() => {
    const ids = new Set(rows.map((offer) => offer.product.product_id));
    return ids.size;
  }, [rows]);

  const selectedProductName = productId
    ? products.find(([id]) => id === productId)?.[1]
    : undefined;

  const activeFilterChips: string[] = [];
  activeFilterChips.push(
    status === "ALL"
      ? "Status: all"
      : status === "REJECTED"
        ? "Status: rejected"
        : "Status: feasible",
  );
  if (selectedProductName) {
    activeFilterChips.push(selectedProductName);
  }
  if (delivery) {
    activeFilterChips.push(deliveryLabel(delivery));
  }
  if (warranty) {
    activeFilterChips.push(warrantyLabel(warranty));
  }
  if (bundle) {
    activeFilterChips.push(bundleLabel(bundle));
  }
  if (returns) {
    activeFilterChips.push(returnsLabel(returns));
  }
  if (maxPrice.trim()) {
    activeFilterChips.push(`Max A$${maxPrice.trim()}`);
  }

  return (
    <section className="space-y-4">
      {explorerOnly ? (
        <div className="space-y-2 text-sm">
          <p>
            Full offer space: {story.products} products ·{" "}
            {story.generated.toLocaleString()} offers
          </p>
          <p>
            Current view: {viewProductCount} products · {rows.length} offers
            {run != null
              ? ` · ${run.total_offers.toLocaleString()} matching filter`
              : null}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {activeFilterChips.map((chip) => (
              <span key={chip} className="filter-chip">
                {chip}
              </span>
            ))}
            <button type="button" onClick={clearFilters} className="btn-ghost">
              Clear filters
            </button>
          </div>
        </div>
      ) : (
        <>
          <div>
            <p className="eyebrow">Construct</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">
              Product → offer space
            </h2>
            <p className="mt-1 text-sm text-muted">
              Matched products stay fixed. AstraOS enumerates commercial
              configurations — it is not choosing a winner here.
            </p>
          </div>

          <div className="bg-canvas px-4 py-4 text-sm">
            <p className="eyebrow">Commercial expansion</p>
            <p className="mt-2 font-mono text-xl font-semibold tabular-nums">
              {story.products} products
            </p>
            <p className="mt-2 text-xs text-muted">{dimensionLine(construction)}</p>
            <ol className="mt-3 space-y-1">
              {steps.map((step, index) => (
                <li key={step.label} className="flex justify-between gap-3">
                  <span className="text-muted">
                    {index > 0 ? "↓ " : ""}
                    {step.label}
                  </span>
                  <span className="font-mono tabular-nums">{step.value}</span>
                </li>
              ))}
            </ol>
            <p className="mt-2 text-xs text-muted">{featured}</p>
          </div>

          <StatStrip
            items={[
              { label: "Estimated", value: construction.summary.estimated_candidates },
              { label: "Generated", value: construction.summary.generated_candidates },
              { label: "Feasible", value: construction.summary.feasible_candidates },
              { label: "Rejected", value: construction.summary.rejected_candidates },
            ]}
          />
          {construction.summary.pruning_reason ? (
            <p className="text-xs text-muted">
              Pruned: {construction.summary.pruning_reason}
            </p>
          ) : null}
          {Object.keys(construction.summary.rejection_distribution).length ? (
            <p className="text-xs text-muted">
              Rejections:{" "}
              {Object.entries(construction.summary.rejection_distribution)
                .map(([code, count]) => `${code.replace(/_/g, " ").toLowerCase()} ${count}`)
                .join(" · ")}
            </p>
          ) : null}
        </>
      )}

      <div className="flex flex-wrap items-end gap-3 text-xs">
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">STATUS</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="control px-2 py-1"
          >
            <option value="FEASIBLE">Feasible</option>
            <option value="REJECTED">Rejected</option>
            <option value="ALL">All</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">PRODUCT</span>
          <select
            value={productId}
            onChange={(event) => setProductId(event.target.value)}
            className="control px-2 py-1"
          >
            <option value="">All</option>
            {products.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">MAX PRICE A$</span>
          <input
            value={maxPrice}
            onChange={(event) => setMaxPrice(event.target.value)}
            placeholder={
              priceCeiling != null ? centsToPlainDollars(priceCeiling) : "Max"
            }
            className="control w-20 px-2 py-1"
          />
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">DELIVERY</span>
          <select
            value={delivery}
            onChange={(event) => setDelivery(event.target.value)}
            className="control px-2 py-1"
          >
            <option value="">All</option>
            {deliveryOptions.map((code) => (
              <option key={code} value={code}>
                {deliveryLabel(code)}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">WARRANTY</span>
          <select
            value={warranty}
            onChange={(event) => setWarranty(event.target.value)}
            className="control px-2 py-1"
          >
            <option value="">All</option>
            {warrantyOptions.map((code) => (
              <option key={code} value={code}>
                {warrantyLabel(code)}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">BUNDLE</span>
          <select
            value={bundle}
            onChange={(event) => setBundle(event.target.value)}
            className="control px-2 py-1"
          >
            <option value="">All</option>
            {bundleOptions.map((code) => (
              <option key={code} value={code}>
                {bundleLabel(code)}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">RETURNS</span>
          <select
            value={returns}
            onChange={(event) => setReturns(event.target.value)}
            className="control px-2 py-1"
          >
            <option value="">All</option>
            {returnsOptions.map((code) => (
              <option key={code} value={code}>
                {returnsLabel(code)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => void applyFilters()}
          disabled={busy}
          className="btn-ghost"
        >
          {busy ? "FILTERING…" : "FILTER"}
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="table-dense w-full min-w-[720px] text-left text-xs">
          <thead className="sticky top-0 z-[1] bg-surface">
            <tr className="border-b border-line text-[11px] tracking-[0.08em] text-muted">
              <th className="py-2 font-medium">Product</th>
              <th className="py-2 font-medium">Product price</th>
              <th className="py-2 font-medium">Delivery</th>
              <th className="py-2 font-medium">Warranty</th>
              <th className="py-2 font-medium">Bundle</th>
              <th className="py-2 font-medium">Returns</th>
              <th className="py-2 font-medium">Customer total</th>
              <th className="py-2 font-medium">Merchant intervention</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map((offer) => (
              <tr
                key={offer.offer_id}
                className="cursor-pointer border-b border-line hover:bg-canvas"
                onClick={() => void openDetail(offer, setDetail)}
              >
                <td className="py-2">{offer.product.name}</td>
                <td className="py-2 tabular-nums">
                  {formatAudCents(offer.pricing.product_price_cents)}
                </td>
                <td className="py-2">
                  {deliveryLabel(offer.delivery.code, offer.delivery.days)}
                </td>
                <td className="py-2">
                  {warrantyLabel(offer.warranty.code, offer.warranty.months)}
                </td>
                <td className="py-2">{bundleLabel(offer.bundle?.code ?? null)}</td>
                <td className="py-2">
                  {returnsLabel(
                    offer.returns?.code ?? null,
                    offer.returns?.window_days ?? null,
                  )}
                </td>
                <td className="py-2 tabular-nums">
                  {formatAudCents(offer.pricing.total_price_cents)}
                </td>
                <td className="py-2 tabular-nums">
                  {formatAudCents(offer.direct_intervention_cost_cents)}
                </td>
                <td className="py-2">{feasibilityLabel(offer.feasibility_status)}</td>
              </tr>
              ))
            ) : (
              <tr>
                <td colSpan={9} className="py-6 text-sm text-muted">
                  No offers match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">
        Showing {rows.length} of {run?.total_offers ?? construction.offers.length}.
        Click a row for configuration detail. No offer is recommended.
      </p>

      {detail ? <OfferDetail detail={detail} onClose={() => setDetail(null)} /> : null}
    </section>
  );
}

function uniqueCodes(
  offers: PublicOffer[],
  pick: (offer: PublicOffer) => string,
): string[] {
  return [...new Set(offers.map(pick).filter(Boolean))].sort();
}

async function openDetail(
  offer: PublicOffer,
  setDetail: (value: OfferDetailResponse) => void,
) {
  setDetail(await getOffer(offer.offer_id));
}

function OfferDetail({
  detail,
  onClose,
}: {
  detail: OfferDetailResponse;
  onClose: () => void;
}) {
  const offer = detail.public;
  return (
    <div className="border border-line px-4 py-4">
      <div className="flex items-baseline justify-between">
        <p className="text-[11px] tracking-[0.14em] text-muted">OFFER DETAIL</p>
        <button type="button" onClick={onClose} className="text-xs text-muted">
          Close
        </button>
      </div>
      <h3 className="mt-2 text-lg font-semibold">{offer.product.name}</h3>
      <p className="font-mono text-[11px] text-muted">{offer.product.sku}</p>
      <dl className="mt-4 grid gap-2 text-sm md:grid-cols-2">
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">PRICE</dt>
          <dd>{formatAudCents(offer.pricing.product_price_cents)}</dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">DELIVERY</dt>
          <dd>
            {offer.delivery.name} ({offer.delivery.days}d)
          </dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">WARRANTY</dt>
          <dd>{offer.warranty.months} months</dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">BUNDLE</dt>
          <dd>{offer.bundle?.name ?? "None"}</dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">RETURNS</dt>
          <dd>{offer.returns ? `${offer.returns.window_days} days` : "—"}</dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">
            TOTAL BUYER COST
          </dt>
          <dd className="tabular-nums">
            {formatAudCents(offer.pricing.total_price_cents)}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">
            DIRECT MERCHANT INTERVENTION
          </dt>
          <dd className="tabular-nums">
            {formatAudCents(offer.direct_intervention_cost_cents)}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] tracking-[0.12em] text-muted">EXPIRES</dt>
          <dd className="text-xs">
            {offer.expires_at
              ? new Date(offer.expires_at).toLocaleString()
              : "—"}
          </dd>
        </div>
      </dl>
      {offer.bundle_relevance ? (
        <div className="mt-4 text-sm">
          <p className="text-[11px] tracking-[0.12em] text-muted">
            CONTEXT-RELEVANT BUNDLE CANDIDATE
          </p>
          <p className="mt-1">{offer.bundle_relevance.name}</p>
          <p className="text-xs text-muted">
            Triggered by:{" "}
            {offer.bundle_relevance.triggered_by.map(contextLabel).join(", ") || "—"}
          </p>
          <p className="text-xs text-muted">
            Variant compatible: {offer.bundle_relevance.variant_compatible ? "yes" : "no"}
            {" · "}
            Merchant available: {offer.bundle_relevance.merchant_available ? "yes" : "no"}
          </p>
        </div>
      ) : null}
      <div className="mt-4">
        <p className="text-[11px] tracking-[0.12em] text-muted">PROOF</p>
        <ul className="mt-2 space-y-1 text-xs text-muted">
          {offer.proof.map((item) => (
            <li key={`${item.type}-${item.source}`}>
              {item.type}: {String(item.value)} · {item.source}
              {item.source_name ? ` / ${item.source_name}` : ""}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

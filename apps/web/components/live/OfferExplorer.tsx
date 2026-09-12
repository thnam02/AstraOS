"use client";

import { useMemo, useState } from "react";

import { StatStrip } from "@/components/shared/StatStrip";
import { getOffer, getOfferRun } from "@/lib/api";
import { contextLabel } from "@/lib/intent";
import { formatAudCents } from "@/lib/money";
import type {
  GenerateOffersResponse,
  OfferDetailResponse,
  OfferRunResponse,
  PublicOffer,
} from "@/types";

export function OfferExplorer({
  construction,
  heroProduct,
}: {
  construction: GenerateOffersResponse;
  heroProduct?: string;
}) {
  const [status, setStatus] = useState("FEASIBLE");
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
  const dims = construction.dimensions;
  const perSku =
    dims.price_options *
    dims.delivery_options *
    dims.warranty_options *
    dims.bundle_options *
    dims.return_options;

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

  const products = useMemo(() => {
    const seen = new Map<string, string>();
    for (const item of construction.offers) {
      seen.set(item.product.product_id, item.product.name);
    }
    return [...seen.entries()];
  }, [construction.offers]);
  const featured = heroProduct ?? products[0]?.[1] ?? "Matched product";

  const matched = construction.input.matched_products || products.length;

  return (
    <section className="space-y-4">
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

      <div className="space-y-2 border border-line px-4 py-3 text-sm">
        <p>
          <span className="font-mono font-semibold tabular-nums">{matched}</span>{" "}
          matched products
        </p>
        <p className="text-muted">↓</p>
        <p>
          <span className="font-mono font-semibold tabular-nums">
            {construction.summary.generated_candidates.toLocaleString()}
          </span>{" "}
          commercial configurations
        </p>
        <p className="text-xs text-muted">
          Price {dims.price_options} · Delivery {dims.delivery_options} · Warranty{" "}
          {dims.warranty_options} · Bundle {dims.bundle_options} · Returns{" "}
          {dims.return_options}
          {perSku ? ` · ${perSku.toLocaleString()} / SKU` : ""}
        </p>
        <p className="text-muted">↓</p>
        <p>
          <span className="font-mono font-semibold tabular-nums">
            {construction.summary.feasible_candidates.toLocaleString()}
          </span>{" "}
          feasible offers
        </p>
        <p className="text-xs text-muted">Example matched product: {featured}</p>
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

      <div className="flex flex-wrap items-end gap-3 text-xs">
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">STATUS</span>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="border border-line bg-surface px-2 py-1"
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
            className="border border-line bg-surface px-2 py-1"
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
            placeholder="350"
            className="w-20 border border-line bg-surface px-2 py-1"
          />
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">DELIVERY</span>
          <input
            value={delivery}
            onChange={(event) => setDelivery(event.target.value)}
            placeholder="SAME_DAY"
            className="border border-line bg-surface px-2 py-1"
          />
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">WARRANTY</span>
          <input
            value={warranty}
            onChange={(event) => setWarranty(event.target.value)}
            placeholder="STANDARD_12"
            className="border border-line bg-surface px-2 py-1"
          />
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">BUNDLE</span>
          <input
            value={bundle}
            onChange={(event) => setBundle(event.target.value)}
            placeholder="NONE or TRAVEL_ADAPTER"
            className="border border-line bg-surface px-2 py-1"
          />
        </label>
        <label className="space-y-1">
          <span className="block tracking-[0.08em] text-muted">RETURNS</span>
          <input
            value={returns}
            onChange={(event) => setReturns(event.target.value)}
            placeholder="STANDARD_30"
            className="border border-line bg-surface px-2 py-1"
          />
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
          <thead>
            <tr className="border-b border-line text-[11px] tracking-[0.08em] text-muted">
              <th className="py-2 font-medium">Product</th>
              <th className="py-2 font-medium">Product price</th>
              <th className="py-2 font-medium">Delivery</th>
              <th className="py-2 font-medium">Warranty</th>
              <th className="py-2 font-medium">Bundle</th>
              <th className="py-2 font-medium">Returns</th>
              <th className="py-2 font-medium">Total</th>
              <th className="py-2 font-medium">Intervention</th>
              <th className="py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((offer) => (
              <tr
                key={offer.offer_id}
                className="cursor-pointer border-b border-line hover:bg-canvas"
                onClick={() => void openDetail(offer, setDetail)}
              >
                <td className="py-2">{offer.product.name}</td>
                <td className="py-2 tabular-nums">
                  {formatAudCents(offer.pricing.product_price_cents)}
                </td>
                <td className="py-2">{offer.delivery.code}</td>
                <td className="py-2">{offer.warranty.months} mo</td>
                <td className="py-2">{offer.bundle?.code ?? "NONE"}</td>
                <td className="py-2">
                  {offer.returns?.window_days ?? "—"}d
                </td>
                <td className="py-2 tabular-nums">
                  {formatAudCents(offer.pricing.total_price_cents)}
                </td>
                <td className="py-2 tabular-nums">
                  {formatAudCents(offer.direct_intervention_cost_cents)}
                </td>
                <td className="py-2">{offer.feasibility_status}</td>
              </tr>
            ))}
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

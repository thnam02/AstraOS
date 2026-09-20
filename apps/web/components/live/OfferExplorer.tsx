"use client";

import { useEffect, useId, useMemo, useState, type ReactNode } from "react";

import {
  AstraEmptyState,
  AstraErrorState,
  AstraPanel,
  AstraStatusBadge,
  type AstraTone,
} from "@/components/astra";
import { StageDisclosure } from "@/components/live/StageShell";
import { getOfferRun } from "@/lib/api";
import {
  bundleLabel,
  deliveryLabel,
  feasibilityLabel,
  returnsLabel,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import { constructStory } from "@/lib/decisionNarrative";
import { formatCount } from "@/lib/format";
import { centsToPlainDollars, formatAudCents } from "@/lib/money";
import {
  filterChipLabel,
  groupOffersByProduct,
  MERCHANT_INTERVENTION_TOOLTIP,
  offerExplorerColumns,
  offerGroupConstants,
  offerPricingBreakdown,
  sortOfferConfigurations,
  type OfferExplorerSortKey,
} from "@/lib/offerExplorerDisplay";
import { cn } from "@/lib/utils";
import { intentPriceCeilingCents } from "@/lib/intent";
import type {
  GenerateOffersResponse,
  OfferRunResponse,
  PublicOffer,
} from "@/types";

const DEFAULT_STATUS = "FEASIBLE";
const PAGE_LIMIT = 120;

function feasibilityTone(status: string): AstraTone {
  const upper = status.toUpperCase();
  if (upper === "FEASIBLE" || upper === "POLICY_SAFE") return "positive";
  if (upper === "REJECTED" || upper.includes("VIOLAT")) return "negative";
  return "neutral";
}

export function OfferExplorer({
  construction,
  explorerOnly = false,
  embedded = false,
  onConfigurationSelect,
}: {
  construction: GenerateOffersResponse;
  heroProduct?: string;
  policySafe?: number;
  pareto?: number;
  explorerOnly?: boolean;
  embedded?: boolean;
  onConfigurationSelect?: (offer: PublicOffer | null) => void;
}) {
  const sortId = useId();
  const [previewPage, setPreviewPage] = useState(0);
  const products = useMemo(
    () => groupOffersByProduct(construction.offers),
    [construction.offers],
  );
  const story = constructStory(construction);
  const priceCeiling = intentPriceCeilingCents(construction.intent);
  const fallbackProductId = products[0]?.productId ?? "";

  const [productId, setProductId] = useState(fallbackProductId);
  const resolvedProductId =
    products.find((item) => item.productId === productId)?.productId ??
    fallbackProductId;

  const [status, setStatus] = useState(DEFAULT_STATUS);
  const [delivery, setDelivery] = useState("");
  const [warranty, setWarranty] = useState("");
  const [bundle, setBundle] = useState("");
  const [returns, setReturns] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [sortKey, setSortKey] = useState<OfferExplorerSortKey>("default");
  const [run, setRun] = useState<OfferRunResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filterState = useMemo(
    () => ({
      status,
      delivery,
      warranty,
      bundle,
      returns,
      maxPrice,
    }),
    [bundle, delivery, maxPrice, returns, status, warranty],
  );

  const deliveryOptions = useMemo(
    () => uniqueCodes(construction.offers, (offer) => offer.delivery.code),
    [construction.offers],
  );
  const warrantyOptions = useMemo(
    () => uniqueCodes(construction.offers, (offer) => offer.warranty.code),
    [construction.offers],
  );
  const bundleOptions = useMemo(
    () =>
      uniqueCodes(construction.offers, (offer) => offer.bundle?.code ?? "NONE"),
    [construction.offers],
  );
  const returnsOptions = useMemo(
    () =>
      uniqueCodes(construction.offers, (offer) => offer.returns?.code ?? ""),
    [construction.offers],
  );

  async function load(
    nextProductId: string,
    filters: {
      status: string;
      delivery: string;
      warranty: string;
      bundle: string;
      returns: string;
      maxPrice: string;
    },
  ) {
    if (!nextProductId) return;
    setBusy(true);
    setError(null);
    try {
      const dollars = Number.parseFloat(filters.maxPrice);
      const result = await getOfferRun(construction.offer_run_id, {
        status: filters.status,
        product_id: nextProductId,
        delivery: filters.delivery || undefined,
        warranty: filters.warranty || undefined,
        bundle: filters.bundle || undefined,
        returns: filters.returns || undefined,
        max_price_cents: Number.isFinite(dollars)
          ? Math.round(dollars * 100)
          : undefined,
        limit: PAGE_LIMIT,
      });
      setRun(result);
      setSelectedId((current) => {
        if (current && result.offers.some((o) => o.offer_id === current)) {
          return current;
        }
        return result.offers[0]?.offer_id ?? null;
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to load offer configurations.",
      );
      setRun(null);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!resolvedProductId) return;
    let cancelled = false;
    void (async () => {
      setBusy(true);
      setError(null);
      try {
        const dollars = Number.parseFloat(filterState.maxPrice);
        const result = await getOfferRun(construction.offer_run_id, {
          status: filterState.status,
          product_id: resolvedProductId,
          delivery: filterState.delivery || undefined,
          warranty: filterState.warranty || undefined,
          bundle: filterState.bundle || undefined,
          returns: filterState.returns || undefined,
          max_price_cents: Number.isFinite(dollars)
            ? Math.round(dollars * 100)
            : undefined,
          limit: PAGE_LIMIT,
        });
        if (cancelled) return;
        setRun(result);
        setSelectedId(result.offers[0]?.offer_id ?? null);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load offer configurations.",
        );
        setRun(null);
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // Product switches reload with the filters that were applied at selection time.
    // Filter edits require Apply filters / chip clear.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [construction.offer_run_id, resolvedProductId]);

  const rows = useMemo(() => {
    const source = run?.offers ?? [];
    return sortOfferConfigurations(source, sortKey, "asc");
  }, [run?.offers, sortKey]);

  const columns = useMemo(
    () => offerExplorerColumns(rows, status),
    [rows, status],
  );
  const constants = useMemo(() => offerGroupConstants(rows), [rows]);
  const selected = rows.find((offer) => offer.offer_id === selectedId) ?? null;
  useEffect(() => {
    onConfigurationSelect?.(selected);
  }, [selected, onConfigurationSelect]);
  const matchingTotal = run?.total_offers ?? rows.length;
  const activeProduct = products.find(
    (item) => item.productId === resolvedProductId,
  );

  const hasExtraFilters = Boolean(
    delivery ||
    warranty ||
    bundle ||
    returns ||
    maxPrice.trim() ||
    status !== DEFAULT_STATUS,
  );

  function clearFilters() {
    const next = {
      status: DEFAULT_STATUS,
      delivery: "",
      warranty: "",
      bundle: "",
      returns: "",
      maxPrice: "",
    };
    setStatus(next.status);
    setDelivery(next.delivery);
    setWarranty(next.warranty);
    setBundle(next.bundle);
    setReturns(next.returns);
    setMaxPrice(next.maxPrice);
    setSortKey("default");
    void load(resolvedProductId, next);
  }

  function applyCurrentFilters(overrides: Partial<typeof filterState> = {}) {
    const next = { ...filterState, ...overrides };
    if (overrides.status != null) setStatus(overrides.status);
    if (overrides.delivery != null) setDelivery(overrides.delivery);
    if (overrides.warranty != null) setWarranty(overrides.warranty);
    if (overrides.bundle != null) setBundle(overrides.bundle);
    if (overrides.returns != null) setReturns(overrides.returns);
    if (overrides.maxPrice != null) setMaxPrice(overrides.maxPrice);
    void load(resolvedProductId, next);
  }

  const lastPreviewPage = Math.max(0, Math.ceil(rows.length / 3) - 1);
  const activePreviewPage = Math.min(previewPage, lastPreviewPage);
  const displayedRows = embedded
    ? rows.slice(activePreviewPage * 3, (activePreviewPage + 1) * 3)
    : rows;

  return (
    <section
      className={embedded ? "embedded-offer-explorer space-y-2" : "space-y-4"}
    >
      {!embedded ? (
        <div className="border border-line bg-canvas px-4 py-3">
          <p className="eyebrow">Offer space</p>
          <dl className="mt-2 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-muted">Matched products</dt>
              <dd className="mt-0.5 font-mono text-lg font-semibold tabular-nums">
                {formatCount(story.products)}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Generated offers</dt>
              <dd className="mt-0.5 font-mono text-lg font-semibold tabular-nums">
                {formatCount(story.generated)}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Feasible</dt>
              <dd className="mt-0.5 font-mono text-lg font-semibold tabular-nums">
                {formatCount(construction.summary.feasible_candidates)}
              </dd>
            </div>
            <div>
              <dt className="text-muted">Rejected</dt>
              <dd className="mt-0.5 font-mono text-lg font-semibold tabular-nums">
                {formatCount(construction.summary.rejected_candidates)}
              </dd>
            </div>
          </dl>
          <p className="mt-2 type-small text-muted">
            Construct enumerates commercial configurations. It does not select a
            winning offer — Optimise does that later.
          </p>
        </div>
      ) : null}

      {embedded ? (
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs text-muted" htmlFor={`${sortId}-product`}>
            Product
          </label>
          <select
            id={`${sortId}-product`}
            className="control min-w-0 max-w-full px-2 py-1 text-sm"
            value={resolvedProductId}
            onChange={(event) => {
              setProductId(event.target.value);
              setPreviewPage(0);
            }}
          >
            {products.map((product) => (
              <option key={product.productId} value={product.productId}>
                {product.name}
              </option>
            ))}
          </select>
        </div>
      ) : products.length > 1 ? (
        <div
          className="flex gap-1 overflow-x-auto border-b border-line pb-2"
          role="tablist"
          aria-label="Matched products"
        >
          {products.map((product) => {
            const active = product.productId === resolvedProductId;
            const count = active && run ? matchingTotal : product.count;
            return (
              <button
                key={product.productId}
                type="button"
                role="tab"
                aria-selected={active}
                className={cn(
                  "shrink-0 border px-3 py-1.5 text-left text-sm",
                  "rounded-[var(--radius-control)]",
                  active
                    ? "border-ink bg-ink text-surface"
                    : "border-line bg-surface text-ink hover:border-ink",
                )}
                onClick={() => setProductId(product.productId)}
              >
                <span className="block font-medium">{product.name}</span>
                <span
                  className={cn(
                    "type-small tabular-nums",
                    active ? "text-surface/80" : "text-muted",
                  )}
                >
                  {formatCount(count)} configs
                </span>
              </button>
            );
          })}
        </div>
      ) : null}

      <StageDisclosure title="Filters and sorting">
        <form
          className="border border-line bg-surface px-3 py-3"
          onSubmit={(event) => {
            event.preventDefault();
            void load(resolvedProductId, filterState);
          }}
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <FilterField label="Status">
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                className="control w-full px-2 py-1.5"
              >
                <option value="FEASIBLE">Feasible</option>
                <option value="REJECTED">Rejected</option>
                <option value="ALL">All</option>
              </select>
            </FilterField>
            <FilterField label="Warranty">
              <select
                value={warranty}
                onChange={(event) => setWarranty(event.target.value)}
                className="control w-full px-2 py-1.5"
              >
                <option value="">All</option>
                {warrantyOptions.map((code) => (
                  <option key={code} value={code}>
                    {warrantyLabel(code)}
                  </option>
                ))}
              </select>
            </FilterField>
            <FilterField label="Bundle">
              <select
                value={bundle}
                onChange={(event) => setBundle(event.target.value)}
                className="control w-full px-2 py-1.5"
              >
                <option value="">All</option>
                {bundleOptions.map((code) => (
                  <option key={code} value={code}>
                    {bundleLabel(code)}
                  </option>
                ))}
              </select>
            </FilterField>
            <FilterField label="Returns">
              <select
                value={returns}
                onChange={(event) => setReturns(event.target.value)}
                className="control w-full px-2 py-1.5"
              >
                <option value="">All</option>
                {returnsOptions.map((code) => (
                  <option key={code} value={code}>
                    {returnsLabel(code)}
                  </option>
                ))}
              </select>
            </FilterField>
            {deliveryOptions.length > 1 ? (
              <FilterField label="Delivery">
                <select
                  value={delivery}
                  onChange={(event) => setDelivery(event.target.value)}
                  className="control w-full px-2 py-1.5"
                >
                  <option value="">All</option>
                  {deliveryOptions.map((code) => (
                    <option key={code} value={code}>
                      {deliveryLabel(code)}
                    </option>
                  ))}
                </select>
              </FilterField>
            ) : null}
            <FilterField label="Max price (A$)">
              <input
                value={maxPrice}
                onChange={(event) => setMaxPrice(event.target.value)}
                inputMode="decimal"
                placeholder={
                  priceCeiling != null
                    ? centsToPlainDollars(priceCeiling)
                    : "Any"
                }
                className="control w-full px-2 py-1.5"
              />
            </FilterField>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
            <div className="flex flex-wrap items-center gap-2">
              {status === DEFAULT_STATUS ? (
                <span className="filter-chip">
                  {filterChipLabel("status", status)}
                </span>
              ) : (
                <button
                  type="button"
                  className="filter-chip"
                  onClick={() =>
                    applyCurrentFilters({ status: DEFAULT_STATUS })
                  }
                >
                  {filterChipLabel("status", status)} ×
                </button>
              )}
              {delivery ? (
                <button
                  type="button"
                  className="filter-chip"
                  onClick={() => applyCurrentFilters({ delivery: "" })}
                >
                  {filterChipLabel("delivery", delivery)} ×
                </button>
              ) : null}
              {warranty ? (
                <button
                  type="button"
                  className="filter-chip"
                  onClick={() => applyCurrentFilters({ warranty: "" })}
                >
                  {filterChipLabel("warranty", warranty)} ×
                </button>
              ) : null}
              {bundle ? (
                <button
                  type="button"
                  className="filter-chip"
                  onClick={() => applyCurrentFilters({ bundle: "" })}
                >
                  {filterChipLabel("bundle", bundle)} ×
                </button>
              ) : null}
              {returns ? (
                <button
                  type="button"
                  className="filter-chip"
                  onClick={() => applyCurrentFilters({ returns: "" })}
                >
                  {filterChipLabel("returns", returns)} ×
                </button>
              ) : null}
              {maxPrice.trim() ? (
                <button
                  type="button"
                  className="filter-chip"
                  onClick={() => applyCurrentFilters({ maxPrice: "" })}
                >
                  {filterChipLabel("maxPrice", maxPrice.trim())} ×
                </button>
              ) : null}
              {hasExtraFilters ? (
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={clearFilters}
                >
                  Clear filters
                </button>
              ) : null}
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <label className="block text-xs text-muted" htmlFor={sortId}>
                Sort
                <select
                  id={sortId}
                  value={sortKey}
                  onChange={(event) =>
                    setSortKey(event.target.value as OfferExplorerSortKey)
                  }
                  className="control mt-1 block min-w-[10rem] px-2 py-1.5"
                >
                  <option value="default">Default order</option>
                  <option value="total">Customer total</option>
                  <option value="intervention">Merchant intervention</option>
                  <option value="warranty">Warranty</option>
                  <option value="returns">Returns</option>
                </select>
              </label>
              <button type="submit" className="btn-primary" disabled={busy}>
                {busy ? "Loading…" : "Apply filters"}
              </button>
            </div>
          </div>
        </form>
      </StageDisclosure>

      {error ? (
        <AstraErrorState
          title="Failed to load offers"
          message={error}
          next="Retry apply filters once the API is available."
        />
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(16rem,32%)]">
        <AstraPanel className="min-w-0">
          {!embedded ? (
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="eyebrow">Current product</p>
                <h3 className="mt-1 type-section text-ink">
                  {constants?.name ?? activeProduct?.name ?? "Product"}
                </h3>
                <p className="type-small text-muted">
                  {constants?.sku ?? activeProduct?.sku}
                </p>
              </div>
              <p className="text-sm tabular-nums">
                {busy ? (
                  <span className="text-muted">Loading configurations…</span>
                ) : rows.length === matchingTotal ? (
                  <>
                    <span className="font-medium">
                      {formatCount(rows.length)}
                    </span>{" "}
                    configurations
                  </>
                ) : (
                  <>
                    Showing{" "}
                    <span className="font-medium">
                      {formatCount(rows.length)}
                    </span>{" "}
                    of {formatCount(matchingTotal)} configurations
                  </>
                )}
              </p>
            </div>
          ) : null}

          {constants && !embedded ? (
            <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-2 border-t border-line pt-3 text-sm">
              {constants.productPriceCents != null ? (
                <div>
                  <dt className="text-muted">Base product price</dt>
                  <dd className="mt-0.5 tabular-nums">
                    {formatAudCents(constants.productPriceCents)}
                  </dd>
                </div>
              ) : null}
              {constants.delivery ? (
                <div>
                  <dt className="text-muted">Delivery</dt>
                  <dd className="mt-0.5">{constants.delivery}</dd>
                </div>
              ) : null}
              {constants.status && constants.statusLabel ? (
                <div>
                  <dt className="text-muted">Status</dt>
                  <dd className="mt-0.5">
                    <AstraStatusBadge tone={feasibilityTone(constants.status)}>
                      {constants.statusLabel}
                    </AstraStatusBadge>
                  </dd>
                </div>
              ) : null}
            </dl>
          ) : null}

          <div
            className={
              embedded
                ? "mt-3 overflow-x-auto border border-line"
                : "mt-4 max-h-[min(64vh,40rem)] overflow-auto border border-line"
            }
          >
            {busy && !rows.length ? (
              <div className="px-3 py-8" role="status" aria-live="polite">
                <p className="text-sm font-medium">Loading configurations</p>
                <p className="mt-1 type-small text-muted">
                  Fetching commercial configurations for this product.
                </p>
              </div>
            ) : !rows.length ? (
              <div className="p-3">
                <AstraEmptyState
                  title="No configurations match filters"
                  body="Adjust warranty, bundle, returns, or status filters, then apply again."
                  action={
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={clearFilters}
                    >
                      Clear filters
                    </button>
                  }
                />
              </div>
            ) : (
              <table className="table-dense w-full border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-line bg-surface text-[11px] text-muted">
                    {columns.productPrice ? (
                      <th className="sticky top-0 z-[1] whitespace-nowrap bg-surface px-3 py-2 text-right font-medium">
                        Product price
                      </th>
                    ) : null}
                    {columns.delivery ? (
                      <th className="sticky top-0 z-[1] whitespace-nowrap bg-surface px-3 py-2 font-medium">
                        Delivery
                      </th>
                    ) : null}
                    <SortableTh
                      label="Warranty"
                      active={sortKey === "warranty"}
                      onClick={() => setSortKey("warranty")}
                    />
                    <th className="sticky top-0 z-[1] whitespace-nowrap bg-surface px-3 py-2 font-medium">
                      Bundle
                    </th>
                    <SortableTh
                      label="Returns"
                      active={sortKey === "returns"}
                      onClick={() => setSortKey("returns")}
                    />
                    <SortableTh
                      label="Customer total"
                      active={sortKey === "total"}
                      align="right"
                      onClick={() => setSortKey("total")}
                    />
                    <SortableTh
                      label="Merchant intervention"
                      active={sortKey === "intervention"}
                      align="right"
                      title={MERCHANT_INTERVENTION_TOOLTIP}
                      onClick={() => setSortKey("intervention")}
                    />
                    {columns.status ? (
                      <th className="sticky top-0 z-[1] whitespace-nowrap bg-surface px-3 py-2 font-medium">
                        Status
                      </th>
                    ) : null}
                  </tr>
                </thead>
                <tbody>
                  {displayedRows.map((offer) => {
                    const selectedRow = offer.offer_id === selectedId;
                    return (
                      <tr
                        key={offer.offer_id}
                        role="row"
                        aria-selected={selectedRow}
                        tabIndex={0}
                        className={cn(
                          "cursor-pointer border-b border-line outline-none",
                          "hover:bg-canvas focus-visible:bg-canvas",
                          selectedRow &&
                            "border-l-2 border-l-mark bg-mark/5 hover:bg-mark/5",
                        )}
                        onClick={() => setSelectedId(offer.offer_id)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setSelectedId(offer.offer_id);
                          }
                        }}
                      >
                        {columns.productPrice ? (
                          <td className="whitespace-nowrap px-3 py-2 text-right tabular-nums">
                            {formatAudCents(offer.pricing.product_price_cents)}
                          </td>
                        ) : null}
                        {columns.delivery ? (
                          <td className="whitespace-nowrap px-3 py-2">
                            {deliveryLabel(
                              offer.delivery.code,
                              offer.delivery.days,
                            )}
                          </td>
                        ) : null}
                        <td className="whitespace-nowrap px-3 py-2">
                          {warrantyLabel(
                            offer.warranty.code,
                            offer.warranty.months,
                          )}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2">
                          {bundleLabel(offer.bundle?.code ?? null)}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2">
                          {returnsLabel(
                            offer.returns?.code ?? null,
                            offer.returns?.window_days ?? null,
                          )}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right font-medium tabular-nums">
                          {formatAudCents(offer.pricing.total_price_cents)}
                        </td>
                        <td
                          className="whitespace-nowrap px-3 py-2 text-right tabular-nums text-muted"
                          title={MERCHANT_INTERVENTION_TOOLTIP}
                        >
                          {formatAudCents(offer.direct_intervention_cost_cents)}
                        </td>
                        {columns.status ? (
                          <td className="whitespace-nowrap px-3 py-2">
                            <AstraStatusBadge
                              tone={feasibilityTone(offer.feasibility_status)}
                            >
                              {feasibilityLabel(offer.feasibility_status)}
                            </AstraStatusBadge>
                          </td>
                        ) : null}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </AstraPanel>

        {embedded ? (
          <AstraPanel className="min-w-0">
            <p className="eyebrow">Viewed configuration</p>
            {selected ? (
              <>
                <p className="mt-2 font-semibold">{selected.product.name}</p>
                <p className="mt-1 font-mono text-xl">
                  {formatAudCents(selected.pricing.total_price_cents)}
                </p>
                <p className="mt-2 text-sm text-muted">
                  {deliveryLabel(
                    selected.delivery.code,
                    selected.delivery.days,
                  )}{" "}
                  ·{" "}
                  {warrantyLabel(
                    selected.warranty.code,
                    selected.warranty.months,
                  )}
                </p>
                <StageDisclosure title="Configuration details">
                  <ConfigurationInspector offer={selected} />
                </StageDisclosure>
              </>
            ) : (
              <p className="mt-2 text-sm text-muted">
                Select a configuration to inspect.
              </p>
            )}
          </AstraPanel>
        ) : (
          <AstraPanel className="min-w-0 xl:sticky xl:top-4 xl:self-start">
            <ConfigurationInspector offer={selected} />
          </AstraPanel>
        )}
      </div>

      {embedded ? (
        <nav
          className="flex items-center justify-between text-xs"
          aria-label="Configuration pages"
        >
          <button
            type="button"
            className="btn-quiet disabled:opacity-40"
            disabled={activePreviewPage === 0}
            onClick={() => setPreviewPage(activePreviewPage - 1)}
          >
            Previous
          </button>
          <span>
            {activePreviewPage + 1} / {lastPreviewPage + 1} · {rows.length}{" "}
            loaded configurations
          </span>
          <button
            type="button"
            className="btn-quiet disabled:opacity-40"
            disabled={activePreviewPage === lastPreviewPage}
            onClick={() => setPreviewPage(activePreviewPage + 1)}
          >
            Next
          </button>
        </nav>
      ) : null}
      {explorerOnly && !embedded ? (
        <div className="border border-line bg-canvas px-4 py-3 text-sm">
          <p className="eyebrow">Construct → Optimise</p>
          <p className="mt-1 text-muted">
            Construct generates the policy-safe commercial possibilities.
            Optimise selects among the efficient complete offers.
          </p>
        </div>
      ) : null}
    </section>
  );
}

function ConfigurationInspector({ offer }: { offer: PublicOffer | null }) {
  if (!offer) {
    return (
      <AstraEmptyState
        title="No configuration selected"
        body="Select a row to inspect one commercial configuration. Construct does not recommend an offer."
      />
    );
  }

  const breakdown = offerPricingBreakdown(offer);

  return (
    <div>
      <p className="eyebrow">Selected configuration</p>
      <h3 className="mt-1 text-base font-semibold text-ink">
        {offer.product.name}
      </h3>
      <p className="type-small text-muted">{offer.product.sku}</p>

      <p className="mt-4 font-mono text-2xl font-semibold tabular-nums">
        {formatAudCents(offer.pricing.total_price_cents)}
      </p>
      <p className="type-small text-muted">Customer total</p>

      <div className="mt-3">
        <AstraStatusBadge tone={feasibilityTone(offer.feasibility_status)}>
          {feasibilityLabel(offer.feasibility_status)}
        </AstraStatusBadge>
      </div>

      <dl className="mt-4 space-y-2 border-t border-line pt-3 text-sm">
        <InspectorRow
          label="Product price"
          value={formatAudCents(offer.pricing.product_price_cents)}
        />
        <InspectorRow
          label="Delivery"
          value={deliveryLabel(offer.delivery.code, offer.delivery.days)}
        />
        <InspectorRow
          label="Warranty"
          value={warrantyLabel(offer.warranty.code, offer.warranty.months)}
        />
        <InspectorRow
          label="Bundle"
          value={bundleLabel(offer.bundle?.code ?? null)}
        />
        <InspectorRow
          label="Returns"
          value={returnsLabel(
            offer.returns?.code ?? null,
            offer.returns?.window_days ?? null,
          )}
        />
        <InspectorRow
          label="Merchant intervention"
          value={formatAudCents(offer.direct_intervention_cost_cents)}
          hint={MERCHANT_INTERVENTION_TOOLTIP}
        />
      </dl>

      {breakdown.length > 1 ? (
        <div className="mt-4 border-t border-line pt-3">
          <p className="text-xs tracking-[0.08em] text-muted">
            CUSTOMER TOTAL BREAKDOWN
          </p>
          <dl className="mt-2 space-y-1.5 text-sm">
            {breakdown.map((row) => (
              <div key={row.label} className="flex justify-between gap-3">
                <dt className="text-muted">{row.label}</dt>
                <dd className="tabular-nums">{formatAudCents(row.cents)}</dd>
              </div>
            ))}
            <div className="flex justify-between gap-3 border-t border-line pt-1.5 font-medium">
              <dt>Customer total</dt>
              <dd className="tabular-nums">
                {formatAudCents(offer.pricing.total_price_cents)}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      {offer.rejection_reasons.length ? (
        <div className="mt-4 border-t border-line pt-3">
          <p className="text-xs tracking-[0.08em] text-muted">
            REJECTION REASONS
          </p>
          <ul className="mt-2 space-y-1 text-sm text-muted">
            {offer.rejection_reasons.map((reason) => (
              <li key={`${reason.code}-${reason.message}`}>
                {reason.message || reason.code}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mt-4 type-small text-muted">
        Inspection only — not a recommended or selected merchant response.
      </p>
    </div>
  );
}

function InspectorRow({
  label,
  value,
  hint,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted" title={hint}>
        {label}
      </dt>
      <dd className="text-right font-medium" title={hint}>
        {value}
      </dd>
    </div>
  );
}

function SortableTh({
  label,
  active,
  align = "left",
  title,
  onClick,
}: {
  label: string;
  active: boolean;
  align?: "left" | "right";
  title?: string;
  onClick: () => void;
}) {
  return (
    <th
      className={cn(
        "sticky top-0 z-[1] whitespace-nowrap bg-surface px-3 py-2 font-medium",
        align === "right" ? "text-right" : "text-left",
      )}
      title={title}
    >
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-1 hover:text-ink",
          active ? "text-ink" : "text-muted",
        )}
        onClick={onClick}
      >
        {label}
        {active ? <span aria-hidden>↑</span> : null}
      </button>
    </th>
  );
}

function FilterField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block min-w-0 space-y-1">
      <span className="block text-xs text-muted">{label}</span>
      {children}
    </label>
  );
}

function uniqueCodes(
  offers: PublicOffer[],
  pick: (offer: PublicOffer) => string,
): string[] {
  return [...new Set(offers.map(pick).filter(Boolean))].sort();
}

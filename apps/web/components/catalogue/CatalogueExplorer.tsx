"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  AstraDataTable,
  AstraEmptyState,
  AstraErrorState,
  AstraLoadingState,
} from "@/components/astra";
import { IngestionPanel } from "@/components/catalogue/IngestionPanel";
import { DataBadge } from "@/components/shared/DataBadge";
import { getCatalogueStats, listProducts } from "@/lib/api";
import { formatAudCents } from "@/lib/money";
import type { CatalogueStatsResponse, ProductSummary } from "@/types";

function boolLabel(value: boolean | null): string {
  if (value === null) return "—";
  return value ? "Yes" : "No";
}

export function CatalogueExplorer() {
  const [stats, setStats] = useState<CatalogueStatsResponse | null>(null);
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [query, setQuery] = useState("");
  const [brand, setBrand] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      getCatalogueStats(),
      listProducts({ activeOnly: false, limit: 200 }),
    ])
      .then(([nextStats, listing]) => {
        setStats(nextStats);
        setProducts(listing.items);
      })
      .catch(() => {
        setError("Unable to load merchant catalogue. Is the API running?");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      getCatalogueStats(),
      listProducts({ activeOnly: false, limit: 200 }),
    ])
      .then(([nextStats, listing]) => {
        if (cancelled) return;
        setStats(nextStats);
        setProducts(listing.items);
      })
      .catch(() => {
        if (cancelled) return;
        setError("Unable to load merchant catalogue. Is the API running?");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const brands = useMemo(
    () => Array.from(new Set(products.map((product) => product.brand))).sort(),
    [products],
  );

  const rows = useMemo(() => {
    return products.flatMap((product) =>
      product.variants
        .filter((variant) => {
          const haystack = `${product.name} ${product.brand} ${variant.sku}`.toLowerCase();
          const matchesQuery = haystack.includes(query.toLowerCase());
          const matchesBrand = brand === "all" || product.brand === brand;
          return matchesQuery && matchesBrand;
        })
        .map((variant) => ({ product, variant })),
    );
  }, [brand, products, query]);

  return (
    <div className="space-y-6">
      <IngestionPanel onImported={load} />
      {error ? (
        <AstraErrorState
          title="Catalogue unavailable"
          message={error}
          next="Confirm the API is running, then refresh."
        />
      ) : null}
      {loading && !error ? (
        <AstraLoadingState
          title="Loading catalogue"
          steps={[
            "Fetching product stats",
            "Listing variants",
            "Ready to browse",
          ]}
        />
      ) : null}
      {!loading && !error ? (
        <>
          {stats?.evidence_quality ? (
            <section className="border border-line bg-surface px-4 py-3">
              <p className="eyebrow">Evidence quality</p>
              <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Product facts</dt>
                  <dd className="tabular-nums">
                    {stats.evidence_quality.product_facts_pct}% covered
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Pricing</dt>
                  <dd className="tabular-nums">
                    {stats.evidence_quality.pricing_current_pct}% current
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Inventory</dt>
                  <dd className="tabular-nums">
                    {stats.evidence_quality.inventory_current_pct}% current
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Fulfilment</dt>
                  <dd className="tabular-nums">
                    {stats.evidence_quality.fulfilment_current_pct}% current
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Warranty</dt>
                  <dd className="tabular-nums">
                    {stats.evidence_quality.warranty_configured_pct}% configured
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted">Synthetic claims</dt>
                  <dd className="tabular-nums">
                    {stats.evidence_quality.synthetic_pct}%
                  </dd>
                </div>
              </dl>
            </section>
          ) : null}

          <section className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
              ["Products", stats?.products],
              ["Variants", stats?.variants],
              ["In stock", stats?.in_stock_variants],
              ["Same-day", stats?.same_day_capable],
              ["Missing attrs", stats?.missing_attribute_variants],
            ].map(([label, value]) => (
              <div key={String(label)} className="border border-line bg-surface px-3 py-3">
                <p className="text-[11px] tracking-[0.12em] text-muted uppercase">{label}</p>
                <p className="mt-1 text-xl font-semibold tabular-nums text-ink">
                  {value ?? "—"}
                </p>
              </div>
            ))}
          </section>

          <div className="flex flex-wrap gap-3">
            <label className="flex min-w-64 flex-1 flex-col gap-1.5">
              <span className="text-xs font-medium text-muted">Search catalogue</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search product, brand, SKU"
                className="control w-full px-3 py-2 text-sm"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-muted">Brand</span>
              <select
                value={brand}
                onChange={(event) => setBrand(event.target.value)}
                className="control px-3 py-2 text-sm"
              >
                <option value="all">All brands</option>
                {brands.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {rows.length === 0 ? (
            <AstraEmptyState
              title="No SKUs match"
              body="Try a different search or brand filter, or import a product feed."
            />
          ) : (
            <AstraDataTable>
              <thead className="border-b border-line bg-surface text-[11px] tracking-[0.08em] text-muted uppercase">
                <tr>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Product</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Brand</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">SKU</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Base</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">COGS</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Stock</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Same day</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">ANC</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Battery</th>
                  <th className="sticky top-0 bg-surface px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ product, variant }) => {
                  const sellable = Math.max(
                    variant.units_available - variant.units_reserved,
                    0,
                  );
                  return (
                    <tr key={variant.id} className="border-b border-line last:border-b-0">
                      <td className="px-3 py-2">
                        <Link
                          href={`/catalogue/${product.id}`}
                          className="text-ink hover:underline"
                        >
                          {product.name}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-muted">{product.brand}</td>
                      <td className="px-3 py-2 font-mono text-xs">{variant.sku}</td>
                      <td className="px-3 py-2 tabular-nums">
                        {formatAudCents(variant.base_price_cents)}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-muted">
                        {formatAudCents(variant.cogs_cents)}
                      </td>
                      <td className="px-3 py-2 tabular-nums">{sellable}</td>
                      <td className="px-3 py-2">
                        {variant.same_day_available ? "Yes" : "No"}
                      </td>
                      <td className="px-3 py-2">{boolLabel(variant.anc)}</td>
                      <td className="px-3 py-2 tabular-nums">
                        {variant.battery_hours ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1">
                          <DataBadge tone={variant.is_active ? "success" : "neutral"}>
                            {variant.is_active ? "Active" : "Inactive"}
                          </DataBadge>
                          {sellable === 0 ? (
                            <DataBadge tone="danger">OOS</DataBadge>
                          ) : null}
                          {variant.has_missing_attributes ? (
                            <DataBadge tone="warning">Missing</DataBadge>
                          ) : null}
                          {product.source_system ? (
                            <DataBadge tone="uncertain">Imported</DataBadge>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </AstraDataTable>
          )}
          <p className="text-xs text-muted">{rows.length} SKUs shown.</p>
        </>
      ) : null}
    </div>
  );
}

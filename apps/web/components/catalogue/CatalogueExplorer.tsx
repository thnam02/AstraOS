"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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

  useEffect(() => {
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
      });
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
      {error ? <p className="text-sm text-danger">{error}</p> : null}
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
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search product, brand, SKU"
          className="min-w-64 flex-1 rounded-[6px] border border-line bg-surface px-3 py-2 text-sm"
        />
        <select
          value={brand}
          onChange={(event) => setBrand(event.target.value)}
          className="rounded-[6px] border border-line bg-surface px-3 py-2 text-sm"
        >
          <option value="all">All brands</option>
          {brands.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto border border-line bg-surface">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-line bg-canvas text-[11px] tracking-[0.08em] text-muted uppercase">
            <tr>
              <th className="px-3 py-2 font-medium">Product</th>
              <th className="px-3 py-2 font-medium">Brand</th>
              <th className="px-3 py-2 font-medium">SKU</th>
              <th className="px-3 py-2 font-medium">Base</th>
              <th className="px-3 py-2 font-medium">COGS</th>
              <th className="px-3 py-2 font-medium">Stock</th>
              <th className="px-3 py-2 font-medium">Same day</th>
              <th className="px-3 py-2 font-medium">ANC</th>
              <th className="px-3 py-2 font-medium">Battery</th>
              <th className="px-3 py-2 font-medium">Status</th>
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
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">{rows.length} SKUs shown.</p>
    </div>
  );
}

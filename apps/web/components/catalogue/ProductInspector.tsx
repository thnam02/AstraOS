"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AstraErrorState, AstraLoadingState } from "@/components/astra";
import { DataBadge } from "@/components/shared/DataBadge";
import { deliveryLabel, titleCaseCode, warrantyLabel } from "@/lib/arenaDisplay";
import { getProduct } from "@/lib/api";
import { formatAudCents } from "@/lib/money";
import type { ProductDetail } from "@/types";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <h2 className="text-[11px] font-medium tracking-[0.14em] text-muted">
        {title}
      </h2>
      {children}
    </section>
  );
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "null") return "—";
  return String(value);
}

export function ProductInspector({ productId }: { productId: string }) {
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getProduct(productId)
      .then((next) => {
        if (!cancelled) {
          setDetail(next);
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
          setError("Product could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [productId]);

  if (error) {
    return (
      <AstraErrorState
        title="Product unavailable"
        message={error}
        next="Return to the catalogue and try another product."
      />
    );
  }
  if (!detail) {
    return (
      <AstraLoadingState
        title="Loading product"
        steps={[
          "Fetching merchant record",
          "Loading variants and evidence",
          "Ready to inspect",
        ]}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <Link href="/catalogue" className="text-xs text-muted hover:text-ink">
          ← Catalogue
        </Link>
        <h1 className="mt-3 text-2xl font-semibold text-ink">
          {detail.product.name}
        </h1>
        <p className="text-sm text-muted">
          {detail.product.brand} · {detail.product.model_number ?? "No model"}
        </p>
        {detail.product.source_system ? (
          <div className="mt-2">
            <DataBadge tone="uncertain">
              {detail.product.source_system === "merchant_json"
                ? "PRODUCT FEED"
                : detail.product.source_system.toUpperCase()}
            </DataBadge>
          </div>
        ) : null}
      </div>

      <Section title="PRODUCT">
        <p className="max-w-2xl text-sm leading-6 text-ink">
          {detail.product.description ?? "No description."}
        </p>
      </Section>

      {detail.variants.map((variant) => {
        const stock = variant.inventory
          ? Math.max(
              variant.inventory.units_available - variant.inventory.units_reserved,
              0,
            )
          : 0;
        return (
          <article key={variant.id} className="space-y-5 border-t border-line pt-6">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div>
                <p className="font-medium text-ink">{variant.variant_name}</p>
                <p className="font-mono text-xs text-muted">{variant.sku}</p>
              </div>
              <p className="text-sm tabular-nums">
                {formatAudCents(variant.base_price_cents)} · COGS{" "}
                {formatAudCents(variant.cogs_cents)}
              </p>
            </div>

            <Section title="ATTRIBUTES">
              <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm md:grid-cols-3">
                {Object.entries(variant.attributes).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <dt className="text-muted">{titleCaseCode(key)}</dt>
                    <dd className="tabular-nums text-ink">{displayValue(value)}</dd>
                  </div>
                ))}
              </dl>
            </Section>

            <Section title="INVENTORY">
              <p className="text-sm">
                {variant.inventory
                  ? `${stock} sellable · ${variant.inventory.units_available} on hand · ${variant.inventory.units_reserved} reserved · ${variant.inventory.warehouse_code}`
                  : "No inventory record."}
              </p>
            </Section>

            <Section title="DELIVERY OPTIONS">
              <ul className="space-y-1 text-sm">
                {variant.delivery_options.map((option) => (
                  <li key={option.id} className="flex justify-between gap-4">
                    <span>
                      {deliveryLabel(option.code)}
                      {option.name && option.name !== option.code
                        ? ` · ${option.name}`
                        : ""}
                    </span>
                    <DataBadge tone={option.available ? "success" : "neutral"}>
                      {option.available ? "Available" : "Unavailable"}
                    </DataBadge>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="WARRANTY OPTIONS">
              <ul className="space-y-1 text-sm">
                {variant.warranty_options.map((option) => (
                  <li key={option.id} className="flex justify-between gap-4">
                    <span>{warrantyLabel(option.code, option.months)}</span>
                    <span className="text-muted">
                      {formatAudCents(option.customer_price_cents)}
                    </span>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="BUNDLES">
              <ul className="space-y-1 text-sm">
                {variant.bundle_options.map((option) => (
                  <li key={option.id} className="flex justify-between gap-4">
                    <span>
                      <span className="font-mono text-xs">{option.code}</span>{" "}
                      {option.name}
                    </span>
                    <DataBadge tone={option.available ? "success" : "neutral"}>
                      {option.available ? "Available" : "Unavailable"}
                    </DataBadge>
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="RETURN POLICY">
              <ul className="space-y-1 text-sm">
                {variant.return_policies.map((option) => (
                  <li key={option.id}>
                    <span className="font-mono text-xs">{option.code}</span>{" "}
                    {option.return_window_days}-day
                    {option.available ? "" : " · unavailable"}
                  </li>
                ))}
              </ul>
            </Section>

            <Section title="PROVENANCE">
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-xs">
                  <thead className="text-muted">
                    <tr>
                      <th className="py-1 pr-3 font-medium">Attribute</th>
                      <th className="py-1 pr-3 font-medium">Value</th>
                      <th className="py-1 pr-3 font-medium">Source</th>
                      <th className="py-1 pr-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {variant.evidence.map((row) => (
                      <tr key={row.id} className="border-t border-line">
                        <td className="py-1 pr-3 font-mono">{row.attribute_name}</td>
                        <td className="py-1 pr-3">
                          {row.value === null || row.value === "null"
                            ? "—"
                            : JSON.stringify(row.value)}
                        </td>
                        <td className="py-1 pr-3">{row.source.name}</td>
                        <td className="py-1 pr-3">
                          {row.verification_status}
                          {row.is_stale ? " · stale" : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>
          </article>
        );
      })}
    </div>
  );
}

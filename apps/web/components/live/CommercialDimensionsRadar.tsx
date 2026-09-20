import { useEffect, useState } from "react";
import { getOfferRun } from "@/lib/api";
import type { PublicOffer, GenerateOffersResponse } from "@/types";

export function CommercialDimensionsRadar({
  dimensions,
  configuration,
  runId,
}: {
  dimensions: GenerateOffersResponse["dimensions"];
  configuration: PublicOffer | null;
  runId: string;
}) {
  const [catalog, setCatalog] = useState<{
    key: string;
    offers: PublicOffer[];
  } | null>(null);
  const [loadError, setLoadError] = useState(false);
  const productId = configuration?.product.product_id;
  const catalogKey = `${runId}:${productId}`;
  useEffect(() => {
    if (!productId) return;
    let cancelled = false;
    setLoadError(false);
    async function load() {
      const offers: PublicOffer[] = [];
      let total = Infinity;
      while (offers.length < total) {
        const page = await getOfferRun(runId, {
          product_id: productId,
          status: "ALL",
          limit: 200,
          offset: offers.length,
        });
        if (cancelled) return;
        total = page.total_offers;
        if (!page.offers.length && offers.length < total)
          throw new Error("Incomplete option set");
        offers.push(...page.offers);
      }
      if (!cancelled) setCatalog({ key: catalogKey, offers });
    }
    void load().catch(() => {
      if (!cancelled) setLoadError(true);
    });
    return () => {
      cancelled = true;
    };
  }, [runId, productId, catalogKey]);
  const peers =
    catalog?.key === catalogKey
      ? catalog.offers.filter(
          (offer) =>
            offer.product.variant_id === configuration?.product.variant_id,
        )
      : [];
  const selectors: {
    key: (offer: PublicOffer) => string;
    order: (offer: PublicOffer) => number | string;
  }[] = [
    {
      key: (offer) => String(offer.pricing.product_price_cents),
      order: (offer) => offer.pricing.product_price_cents,
    },
    {
      key: (offer) => offer.delivery.code,
      order: (offer) => offer.delivery.days,
    },
    {
      key: (offer) => offer.warranty.code,
      order: (offer) => offer.warranty.months,
    },
    {
      key: (offer) => offer.bundle?.code ?? "NONE",
      order: (offer) => offer.bundle?.code ?? "NONE",
    },
    {
      key: (offer) => offer.returns?.code ?? "STANDARD",
      order: (offer) => offer.returns?.window_days ?? 0,
    },
  ];
  const ordinals = selectors.map(({ key, order }) => {
    const options = [
      ...new Map(peers.map((offer) => [key(offer), offer])).values(),
    ].sort((a, b) => {
      const left = order(a),
        right = order(b);
      return (
        (typeof left === "number" && typeof right === "number"
          ? left - right
          : String(left).localeCompare(String(right))) ||
        key(a).localeCompare(key(b))
      );
    });
    const index = configuration
      ? options.findIndex((offer) => key(offer) === key(configuration))
      : -1;
    return index < 0 ? null : { position: index + 1, count: options.length };
  });
  const axes = [
    { label: "Price", count: dimensions.price_options },
    { label: "Delivery", count: dimensions.delivery_options },
    { label: "Warranty", count: dimensions.warranty_options },
    { label: "Bundle", count: dimensions.bundle_options },
    { label: "Returns", count: dimensions.return_options },
  ].map((axis, index) => ({ ...axis, ordinal: ordinals[index] }));
  const point = (index: number, radius: number) => {
    const angle = (index * 2 * Math.PI) / axes.length - Math.PI / 2;
    return {
      x: 220 + radius * Math.cos(angle),
      y: 145 + radius * Math.sin(angle),
    };
  };
  const polygon = (radius: number) =>
    axes
      .map((_, index) => {
        const { x, y } = point(index, radius);
        return `${x},${y}`;
      })
      .join(" ");

  return (
    <figure className="grid items-center gap-3 sm:grid-cols-[minmax(0,1fr)_10rem]">
      <svg
        viewBox="55 5 330 270"
        className="mx-auto h-[210px] w-full min-w-0"
        role="img"
        aria-label={`Available options by commercial dimension: ${axes.map((axis) => `${axis.label}: ${axis.ordinal ? `${axis.ordinal.position} of ${axis.ordinal.count}` : `${axis.count} options`}, viewed position ${axis.ordinal?.position ?? "unavailable"}`).join(", ")}. Each axis spans zero to its available option count.`}
      >
        {[1, 2, 3, 4].map((ring) => (
          <polygon
            key={ring}
            points={polygon((98 * ring) / 4)}
            fill="none"
            stroke="var(--color-chart-grid)"
          />
        ))}
        {axes.map((axis, index) => {
          const end = point(index, 98);
          const label = point(index, 123);
          return (
            <g key={axis.label}>
              <line
                x1="220"
                y1="145"
                x2={end.x}
                y2={end.y}
                stroke="var(--color-chart-grid)"
              />
              <text
                x={label.x}
                y={label.y}
                textAnchor="middle"
                fill="var(--color-ink)"
                fontSize="12"
              >
                {axis.label}
                <tspan x={label.x} dy="16" fontWeight="600">
                  {axis.ordinal
                    ? `${axis.ordinal.position} of ${axis.ordinal.count}`
                    : `${axis.count} options`}
                </tspan>
              </text>
            </g>
          );
        })}
        {ordinals.every((item) => item !== null) ? (
          <polygon
            points={ordinals
              .map((item, index) => {
                const { x, y } = point(
                  index,
                  (98 * item!.position) / item!.count,
                );
                return `${x},${y}`;
              })
              .join(" ")}
            fill="var(--color-uncertain)"
            fillOpacity="0.18"
            stroke="var(--color-uncertain)"
            strokeWidth="2"
            strokeDasharray="5 3"
          />
        ) : null}
      </svg>
      <figcaption className="min-w-0 text-xs leading-4 text-muted">
        <div className="flex items-center gap-2 text-uncertain">
          <svg
            width="24"
            height="12"
            viewBox="0 0 24 12"
            aria-hidden="true"
            className="shrink-0"
          >
            <path
              d="M0 6H24"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray="5 3"
            />
          </svg>
          <span className="font-medium">Viewed option</span>
        </div>
        <p className="mt-3">Axis range: 0 to option count.</p>
        <p className="mt-3 font-medium text-ink">Option order</p>
        <dl className="mt-1 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1">
          <dt>Price</dt>
          <dd>Low to high</dd>
          <dt>Delivery</dt>
          <dd>Fewest days first</dd>
          <dt>Warranty</dt>
          <dd>Shortest first</dd>
          <dt>Returns</dt>
          <dd>Shortest first</dd>
          <dt>Bundle</dt>
          <dd>By code (A–Z)</dd>
        </dl>
        {loadError ? (
          <p className="sr-only" role="status">
            Option positions unavailable.
          </p>
        ) : null}
      </figcaption>
    </figure>
  );
}

import {
  bundleLabel,
  deliveryLabel,
  feasibilityLabel,
  returnsLabel,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import type { PublicOffer } from "@/types";

export type OfferExplorerSortKey =
  | "total"
  | "intervention"
  | "warranty"
  | "returns"
  | "default";

export type OfferExplorerColumns = {
  productPrice: boolean;
  delivery: boolean;
  status: boolean;
};

export type PricingBreakdownRow = {
  label: string;
  cents: number;
};

/** Column visibility for one product's configurations. */
export function offerExplorerColumns(
  offers: PublicOffer[],
  statusFilter: string,
): OfferExplorerColumns {
  if (!offers.length) {
    return { productPrice: false, delivery: false, status: false };
  }
  const prices = new Set(offers.map((o) => o.pricing.product_price_cents));
  const deliveries = new Set(offers.map((o) => o.delivery.code));
  const statuses = new Set(offers.map((o) => o.feasibility_status));
  return {
    productPrice: prices.size > 1,
    delivery: deliveries.size > 1,
    status: statusFilter === "ALL" || statuses.size > 1,
  };
}

export function offerGroupConstants(offers: PublicOffer[]) {
  if (!offers.length) return null;
  const first = offers[0]!;
  const samePrice = offers.every(
    (o) => o.pricing.product_price_cents === first.pricing.product_price_cents,
  );
  const sameDelivery = offers.every(
    (o) => o.delivery.code === first.delivery.code,
  );
  const sameStatus = offers.every(
    (o) => o.feasibility_status === first.feasibility_status,
  );
  return {
    name: first.product.name,
    sku: first.product.sku,
    productPriceCents: samePrice ? first.pricing.product_price_cents : null,
    delivery: sameDelivery
      ? deliveryLabel(first.delivery.code, first.delivery.days)
      : null,
    status: sameStatus ? first.feasibility_status : null,
    statusLabel: sameStatus
      ? feasibilityLabel(first.feasibility_status)
      : null,
  };
}

/** Presentation-only sort. Does not change construction ranking. */
export function sortOfferConfigurations(
  offers: PublicOffer[],
  key: OfferExplorerSortKey,
  direction: "asc" | "desc" = "asc",
): PublicOffer[] {
  if (key === "default") return [...offers];
  const sign = direction === "asc" ? 1 : -1;
  return [...offers].sort((a, b) => {
    let delta = 0;
    switch (key) {
      case "total":
        delta = a.pricing.total_price_cents - b.pricing.total_price_cents;
        break;
      case "intervention":
        delta =
          a.direct_intervention_cost_cents - b.direct_intervention_cost_cents;
        break;
      case "warranty":
        delta = a.warranty.months - b.warranty.months;
        break;
      case "returns":
        delta =
          (a.returns?.window_days ?? 0) - (b.returns?.window_days ?? 0);
        break;
      default:
        delta = 0;
    }
    if (delta !== 0) return delta * sign;
    return a.offer_id.localeCompare(b.offer_id);
  });
}

/** Customer-facing total components from PublicOffer pricing only. */
export function offerPricingBreakdown(
  offer: PublicOffer,
): PricingBreakdownRow[] {
  const rows: PricingBreakdownRow[] = [
    { label: "Product", cents: offer.pricing.product_price_cents },
  ];
  if (offer.pricing.delivery_charge_cents) {
    rows.push({
      label: "Delivery",
      cents: offer.pricing.delivery_charge_cents,
    });
  }
  if (offer.pricing.warranty_price_cents) {
    rows.push({
      label: "Warranty",
      cents: offer.pricing.warranty_price_cents,
    });
  }
  if (offer.pricing.bundle_price_cents) {
    rows.push({
      label: "Bundle",
      cents: offer.pricing.bundle_price_cents,
    });
  }
  if (offer.pricing.adjustment_cents) {
    rows.push({
      label: "Price adjustment",
      cents: offer.pricing.adjustment_cents,
    });
  }
  return rows;
}

export function groupOffersByProduct(offers: PublicOffer[]) {
  const map = new Map<
    string,
    {
      productId: string;
      name: string;
      sku: string;
      count: number;
    }
  >();
  for (const offer of offers) {
    const id = offer.product.product_id;
    const existing = map.get(id);
    if (existing) {
      existing.count += 1;
    } else {
      map.set(id, {
        productId: id,
        name: offer.product.name,
        sku: offer.product.sku,
        count: 1,
      });
    }
  }
  return [...map.values()];
}

export const MERCHANT_INTERVENTION_TOOLTIP =
  "Direct merchant cost of commercial terms for this configuration (price adjustment, delivery, warranty, bundle, and expected returns cost). Not a contribution margin and not a recommended score.";

export function filterChipLabel(
  kind: "status" | "warranty" | "bundle" | "returns" | "delivery" | "maxPrice",
  value: string,
): string {
  switch (kind) {
    case "status":
      if (value === "ALL") return "Status: all";
      if (value === "REJECTED") return "Status: rejected";
      return "Status: feasible";
    case "warranty":
      return warrantyLabel(value);
    case "bundle":
      return bundleLabel(value);
    case "returns":
      return returnsLabel(value);
    case "delivery":
      return deliveryLabel(value);
    case "maxPrice":
      return `Max A$${value}`;
    default:
      return value;
  }
}

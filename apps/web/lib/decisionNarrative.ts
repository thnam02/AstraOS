import { deliveryLabel, bundleLabel, warrantyLabel } from "./arenaDisplay";
import type {
  CounterfactualRow,
  GenerateOffersResponse,
  OptimisationResponse,
  PublicScoredOffer,
  RankedProductMatch,
} from "../types";

export function matchScoreDisplay(
  value: number,
  peers: number[] = [],
): { value: string; suffix: string } {
  const rounded = Math.round(value * 100);
  const peerRounds = peers.map((item) => Math.round(item * 100));
  const tied = peerRounds.filter((item) => item === rounded).length > 1;
  return {
    value: tied ? (value * 100).toFixed(1) : String(rounded),
    suffix: "/ 100",
  };
}

export function productsDiffer(
  top: RankedProductMatch | null | undefined,
  offer: PublicScoredOffer | null | undefined,
): boolean {
  if (!top || !offer) return false;
  if (top.sku && offer.sku) return top.sku !== offer.sku;
  return top.product_name !== offer.product_name;
}

export function bestPointForProduct(
  optimisation: OptimisationResponse | null | undefined,
  product: RankedProductMatch | null | undefined,
) {
  if (!optimisation || !product) return null;
  const points = optimisation.plot_points.filter(
    (item) => item.sku === product.sku || item.product_name === product.product_name,
  );
  if (!points.length) return null;
  return points.reduce((best, item) =>
    item.buyer_utility > best.buyer_utility ? item : best,
  );
}

export function commercialLevers(offer: PublicScoredOffer) {
  return [
    deliveryLabel(offer.delivery.code, offer.delivery.days),
    warrantyLabel(offer.warranty.code, offer.warranty.months),
    bundleLabel(offer.bundle?.code ?? null),
  ];
}

export function conciseOfferReasons(lines: string[]): string[] {
  const mapped = lines
    .map((line) => {
      if (/probability|cold-start/i.test(line)) return null;
      if (/mandatory/i.test(line)) return "All mandatory requirements satisfied";
      if (/same-day|urgency/i.test(line)) return "Same-day delivery addresses urgency";
      if (/semantic|product fit/i.test(line)) return "Strong travel-context product fit";
      if (/warranty/i.test(line)) return "Extended warranty supports reliability";
      if (/pareto|frontier/i.test(line)) return "Pareto efficient";
      if (/margin/i.test(line)) return "Above merchant margin floor";
      return line.length > 88 ? `${line.slice(0, 85)}…` : line;
    })
    .filter((item): item is string => Boolean(item));
  return [...new Set(mapped)].slice(0, 5);
}

export function strengthHint(attribute: string): string | null {
  const key = attribute.toLowerCase();
  if (key.includes("battery")) return "Very strong endurance";
  if (key.includes("weight")) return "Lightweight for extended wear";
  if (key === "anc") return "Supports long-haul travel";
  if (key.includes("fold")) return "Travel convenience";
  if (key.includes("same_day") || key.includes("delivery")) return "Fulfils urgency";
  if (key.includes("comfort")) return "Supports extended wear";
  return null;
}

export function constructStory(construction: GenerateOffersResponse) {
  const dims = construction.dimensions;
  return {
    products: construction.input.matched_products,
    price: dims.price_options,
    delivery: dims.delivery_options,
    warranty: dims.warranty_options,
    bundle: dims.bundle_options,
    returns: dims.return_options,
    generated: construction.summary.generated_candidates,
    feasible: construction.summary.feasible_candidates,
    estimated: construction.summary.estimated_candidates,
  };
}

export function offerVsProductCopy(differ: boolean): string {
  return differ
    ? "Product ranking identifies the best products. Offer optimisation identifies the best commercial response."
    : "Top product remained strongest after offer optimisation.";
}

export function counterfactualStory(rows: CounterfactualRow[]) {
  const baseline =
    rows.find((row) => /baseline|conceptual|default/i.test(row.label)) ??
    rows.find((row) => row.lever === "none" || row.delta_utility === 0);
  const discount = [...rows]
    .filter((row) => row.lever === "price" || row.lever === "discount")
    .sort((a, b) => b.delta_utility - a.delta_utility)[0];
  const delivery =
    rows.find((row) => row.lever === "delivery" && row.delivery_code === "SAME_DAY") ??
    [...rows]
      .filter((row) => row.lever === "delivery")
      .sort((a, b) => b.delta_utility - a.delta_utility)[0];
  if (!baseline || !discount || !delivery) return null;
  const deliveryEff =
    delivery.delta_utility /
    Math.max(1, Math.abs(delivery.incremental_intervention_cost_cents));
  const discountEff =
    discount.delta_utility /
    Math.max(1, Math.abs(discount.incremental_intervention_cost_cents));
  return {
    baseline,
    discount,
    delivery,
    choosesDelivery: deliveryEff >= discountEff,
  };
}

export function negotiationConstraint(
  payload: Record<string, unknown> | null | undefined,
): string | null {
  if (!payload) return null;
  const nested =
    payload.constraints && typeof payload.constraints === "object"
      ? (payload.constraints as Record<string, unknown>)
      : {};
  const cents =
    nested.max_total_price_cents ??
    nested.max_price_cents ??
    payload.max_total_price_cents ??
    payload.max_price_cents;
  if (typeof cents === "number") {
    return `TOTAL PRICE ≤ A$${(cents / 100).toFixed(cents % 100 === 0 ? 0 : 2)}`;
  }
  const delivery = nested.delivery ?? payload.delivery;
  if (typeof delivery === "string") return `DELIVERY = ${delivery}`;
  return null;
}

export function isPresentationMode(value: string | null | undefined): boolean {
  return value === "1";
}

export const LEARN_STORY = [
  { id: "observe", label: "Observe", body: "Intent → Offer → Outcome" },
  { id: "learn", label: "Learn", body: "Response model" },
  { id: "improve", label: "Improve", body: "Future offer decisions" },
] as const;

export const SCENARIOS = [
  {
    id: "urgent",
    label: "Urgent traveller",
    profile: "URGENT_TRAVELLER" as const,
    intent:
      "I need ANC headphones under A$350 for a long-haul flight. Delivered today. Comfort and reliability matter more than getting the cheapest option.",
  },
  {
    id: "budget",
    label: "Budget buyer",
    profile: "BUDGET_SHOPPER" as const,
    intent:
      "I need wireless ANC headphones under A$260. Cheapest option that still works is fine. Two-day delivery is ok.",
  },
  {
    id: "assurance",
    label: "Assurance buyer",
    profile: "ASSURANCE_BUYER" as const,
    intent:
      "I want reliable ANC headphones under A$350. A long warranty matters more than getting the cheapest pair.",
  },
] as const;

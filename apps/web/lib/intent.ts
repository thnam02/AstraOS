import { centsToPlainDollars, formatAudCents } from "@/lib/money";
import type { HardConstraint, ShoppingIntent } from "@/types";

export const HERO_INTENT = `I'm flying from Sydney to Singapore tomorrow and need wireless noise-cancelling headphones under A$350. I need them delivered today. I'll wear them for hours, so comfort and reliability matter more than getting the absolute cheapest option.`;

export function fieldLabel(field: string): string {
  const labels: Record<string, string> = {
    anc: "ANC",
    price: "Price",
    delivery_days: "Delivery",
    same_day_delivery: "Same-day delivery",
    battery_hours: "Battery",
    weight_g: "Weight",
    foldable: "Foldable",
    wireless: "Wireless",
    microphone: "Microphone",
    in_stock: "In stock",
    category: "Category",
    brand: "Brand",
    unsupported: "Unsupported",
    comfort: "Comfort",
    reliability: "Reliability",
    travel: "Travel suitability",
    battery: "Battery",
    weight: "Weight",
    delivery: "Delivery",
    warranty: "Warranty",
    durability: "Durability",
    repairability: "Repairability",
    sustainability: "Sustainability",
  };
  return labels[field] ?? field.replace(/_/g, " ");
}

export function contextLabel(tag: string): string {
  return tag
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatConstraint(
  operator: string,
  value: unknown,
  unit: string | null,
): string {
  if (unit === "AUD_CENTS" && typeof value === "number") {
    const symbol = operator === "LT" ? "<" : operator === "LTE" ? "≤" : operator;
    return `${symbol} ${formatAudCents(value)}`;
  }
  if (unit === "DAYS" && value === 0) return "today";
  if (operator === "EQ" && value === true) return "";
  if (operator === "EQ" && value === false) return "must be false";
  return `${operator} ${String(value)}`;
}

export function constraintLabel(item: HardConstraint): string {
  const name =
    item.field === "price" && item.applies_to === "PRODUCT_BASE"
      ? "Base price"
      : item.field === "price"
        ? "Total"
        : fieldLabel(item.field);
  return `${name} ${formatConstraint(
    item.operator,
    item.normalized_value ?? item.value,
    item.unit,
  )}`.trim();
}

export function buyerRequestHighlights(intent: ShoppingIntent): string[] {
  const chips: string[] = [];
  if (intent.category) chips.push(contextLabel(intent.category));
  for (const item of intent.hard_constraints) {
    const label = constraintLabel(item);
    if (label && !chips.includes(label)) chips.push(label);
    if (chips.length >= 4) break;
  }
  const priorities = intent.soft_preferences
    .filter((item) => item.importance >= 0.5)
    .slice(0, 2)
    .map((item) => fieldLabel(item.field));
  if (priorities.length) {
    chips.push(`${priorities.join(" + ")} prioritised`);
  }
  return chips.slice(0, 5);
}

type PriceConstraintSource = {
  hard_constraints?: Array<{
    field: string;
    value?: unknown;
    normalized_value?: unknown;
  }>;
};

export function intentPriceCeilingCents(
  intent?: PriceConstraintSource | null,
): number | null {
  const prices = (intent?.hard_constraints ?? [])
    .filter((item) => item.field === "price")
    .map((item) => item.normalized_value ?? item.value)
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
  if (!prices.length) return null;
  return Math.min(...prices);
}

export function defaultBuyerCounter(
  intent?: PriceConstraintSource | null,
  offerCents?: number | null,
): string {
  const cents = intentPriceCeilingCents(intent) ?? offerCents ?? null;
  if (cents == null) return "Can you adjust the commercial terms?";
  return `Can you get this below A$${centsToPlainDollars(cents)}?`;
}

export function importanceLabel(value: number): string {
  if (value >= 0.75) return "High";
  if (value <= 0.25) return "Low";
  return "Medium";
}

export function intentNarrative(intent: ShoppingIntent): string {
  const category = intent.category
    ? contextLabel(intent.category).toLowerCase()
    : "the requested products";
  const mandatory = intent.hard_constraints
    .slice(0, 4)
    .map((item) => constraintLabel(item))
    .filter(Boolean);
  const priorities = intent.soft_preferences
    .filter((item) => item.importance >= 0.5)
    .slice(0, 2)
    .map((item) => fieldLabel(item.field).toLowerCase());
  const trade = intent.tradeoffs[0];
  const parts: string[] = [];
  parts.push(
    mandatory.length
      ? `The buyer needs ${category} with ${mandatory.join(", ")}.`
      : `The buyer needs ${category}.`,
  );
  if (priorities.length) {
    const joined = priorities.join(" and ");
    parts.push(
      `${joined.charAt(0).toUpperCase()}${joined.slice(1)} ${
        priorities.length > 1 ? "are" : "is"
      } prioritised.`,
    );
  }
  if (trade) {
    const over =
      trade.over_dimension === "price"
        ? "minimising price"
        : fieldLabel(trade.over_dimension).toLowerCase();
    parts.push(
      `${fieldLabel(trade.preferred_dimension)} matters more than ${over}.`,
    );
  }
  return parts.join(" ");
}

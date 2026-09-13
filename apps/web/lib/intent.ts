import { formatAudCents } from "@/lib/money";
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
  return `${fieldLabel(item.field)} ${formatConstraint(
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

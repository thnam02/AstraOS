import { formatAudCents, formatRate } from "@/lib/money";

export { formatAudCents, formatRate };

export function formatScore100(value: number, peers: number[] = []): string {
  const rounded = Math.round(value * 100);
  const tied = peers.filter((item) => Math.round(item * 100) === rounded).length > 1;
  const shown = tied ? (value * 100).toFixed(1) : String(rounded);
  return `${shown} / 100`;
}

export function formatUtility(value: number): string {
  return `${value.toFixed(2)} utility`;
}

/** Compact utility for dense table cells (no " utility" suffix). */
export function formatUtilityShort(value: number): string {
  return value.toFixed(2);
}

/** Sentence-case enum labels: "NO_POLICY_SAFE" → "No policy safe". */
export function humanizeEnum(value: string): string {
  const spaced = value.replaceAll("_", " ").toLowerCase();
  return spaced.replace(/^\w/, (char) => char.toUpperCase());
}

export function formatHours(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(0)}h`;
}

export function formatGrams(value: number): string {
  return `${Number.isInteger(value) ? value : value.toFixed(0)}g`;
}

export function formatMonths(value: number): string {
  return value === 1 ? "1 month" : `${value} months`;
}

export function formatCount(value: number): string {
  return value.toLocaleString("en-AU");
}

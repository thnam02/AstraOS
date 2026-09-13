import { fieldLabel } from "@/lib/intent";
import { formatAudCents } from "@/lib/money";
import type { QualifyResponse, VariantQualificationCard } from "@/types";

export const QUALIFY_LIST_PREVIEW = 10;

export function sharedExclusionReason(
  items: VariantQualificationCard[],
): string | null {
  const first = items[0]?.exclusion_reasons[0];
  if (!first) return null;
  return items.every((item) => item.exclusion_reasons[0] === first)
    ? first
    : null;
}

const VIOLATED =
  /^(\w+)\s+VIOLATED:\s+expected\s+(\w+)\s+(.+),\s+observed\s+(.+)$/;
const UNKNOWN = /^(\w+)\s+UNKNOWN:\s+(.+)$/;

export function exclusionGroupKey(reason: string): string {
  const violated = VIOLATED.exec(reason);
  if (violated) {
    return `${violated[1]}|VIOLATED|${violated[2]}|${violated[3]}`;
  }
  const unknown = UNKNOWN.exec(reason);
  if (unknown) return `${unknown[1]}|UNKNOWN|${unknown[2]}`;
  return reason;
}

export function humanizeExclusionReason(
  reason: string,
  options: { includeObserved?: boolean } = {},
): string {
  if (reason.includes("NO_MANDATORY_CONSTRAINTS")) {
    return "No mandatory constraints were provided for this request.";
  }
  if (reason === "Unspecified constraint") return "Unspecified constraint";

  const violated = VIOLATED.exec(reason);
  if (violated) {
    return humanizeViolated(
      violated[1] ?? "",
      violated[2] ?? "",
      violated[3] ?? "",
      violated[4] ?? "",
      Boolean(options.includeObserved),
    );
  }
  const unknown = UNKNOWN.exec(reason);
  if (unknown) {
    return humanizeUnknown(unknown[1] ?? "", unknown[2] ?? "");
  }
  return reason;
}

export function qualificationReasonCopy(reason: string): string {
  return humanizeExclusionReason(reason);
}

export function exclusionSummary(detail: QualifyResponse | null) {
  if (!detail) return [];
  const counts = new Map<string, { label: string; count: number }>();
  for (const item of detail.rejected_products) {
    const reasons = item.exclusion_reasons.length
      ? item.exclusion_reasons
      : ["Unspecified constraint"];
    for (const reason of reasons) {
      const key = exclusionGroupKey(reason);
      const current = counts.get(key);
      if (current) current.count += 1;
      else {
        counts.set(key, {
          label: humanizeExclusionReason(reason),
          count: 1,
        });
      }
    }
  }
  return [...counts.values()].sort((a, b) => b.count - a.count);
}

function formatConstraintValue(field: string, raw: string): string {
  const value = raw.trim();
  if (value === "True") return "yes";
  if (value === "False") return "no";
  if (value === "missing") return "missing";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  if (field === "price") return formatAudCents(numeric);
  if (field === "delivery_days") {
    if (numeric === 0) return "same-day";
    return `${numeric} day${numeric === 1 ? "" : "s"}`;
  }
  if (field === "warranty_months") return `${numeric}-month`;
  return String(numeric);
}

function humanizeViolated(
  field: string,
  operator: string,
  expectedRaw: string,
  observedRaw: string,
  includeObserved: boolean,
): string {
  const label = fieldLabel(field);
  const expected = formatConstraintValue(field, expectedRaw);
  const observed = formatConstraintValue(field, observedRaw);
  if (field === "price" && (operator === "LT" || operator === "LTE")) {
    return includeObserved
      ? `${observed} is over the ${expected} limit`
      : `Price over ${expected}`;
  }
  if (field === "delivery_days" && (operator === "LT" || operator === "LTE")) {
    return includeObserved
      ? `Delivery is ${observed}; ${expected} required`
      : `Delivery slower than ${expected}`;
  }
  if (operator === "EQ") {
    return includeObserved
      ? `${label} is ${observed}, not ${expected}`
      : `${label} is not ${expected}`;
  }
  return includeObserved
    ? `${label}: expected ${expected}, observed ${observed}`
    : `${label} does not meet ${expected}`;
}

function humanizeUnknown(field: string, code: string): string {
  const label = fieldLabel(field);
  if (code === "MISSING_ATTRIBUTE") return `${label} not confirmed in catalogue data`;
  if (code === "STALE_EVIDENCE") return `${label} evidence is stale`;
  if (code === "MISSING_DELIVERY_DATA") return "Delivery data missing";
  if (code === "UNSUPPORTED_OPERATOR") return `${label} could not be evaluated`;
  return `${label}: ${code.replaceAll("_", " ").toLowerCase()}`;
}

export function rowSpecificReasons(
  item: VariantQualificationCard,
  groupReason: string | null,
): string[] {
  return item.exclusion_reasons.filter((reason) => reason !== groupReason);
}

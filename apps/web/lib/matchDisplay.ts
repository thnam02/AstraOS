import { contextLabel, fieldLabel } from "@/lib/intent";
import type { ProofItem, RankedProductMatch } from "@/types";

export type SourceBadge = {
  code:
    | "PRODUCT FEED"
    | "INVENTORY"
    | "PRICING"
    | "FULFILMENT"
    | "WARRANTY"
    | "BUNDLE"
    | "RETURNS"
    | "EXAMPLE IMPORT"
    | "SYNTHETIC";
  title: string;
};

const OPERATIONAL = new Set([
  "units_available",
  "base_price_cents",
  "same_day",
  "same_day_delivery",
]);

export function sourceBadge(
  sourceType: string | null | undefined,
  sourceName: string | null | undefined = null,
): SourceBadge {
  const raw = `${sourceType ?? ""} ${sourceName ?? ""}`.trim() || "Source";
  const text = raw.toLowerCase();
  if (text.includes("synthetic") || text.includes("fixture")) {
    return { code: "SYNTHETIC", title: sourceName || sourceType || raw };
  }
  if (text.includes("example")) {
    return { code: "EXAMPLE IMPORT", title: sourceName || sourceType || raw };
  }
  if (text.includes("inventor")) {
    return { code: "INVENTORY", title: sourceName || sourceType || raw };
  }
  if (text.includes("pric")) {
    return { code: "PRICING", title: sourceName || sourceType || raw };
  }
  if (
    text.includes("fulfil") ||
    text.includes("fulfill") ||
    text.includes("delivery")
  ) {
    return { code: "FULFILMENT", title: sourceName || sourceType || raw };
  }
  if (text.includes("warrant")) {
    return { code: "WARRANTY", title: sourceName || sourceType || raw };
  }
  if (text.includes("bundle")) {
    return { code: "BUNDLE", title: sourceName || sourceType || raw };
  }
  if (text.includes("return")) {
    return { code: "RETURNS", title: sourceName || sourceType || raw };
  }
  return { code: "PRODUCT FEED", title: sourceName || sourceType || raw };
}

export type DisplayFact = {
  attribute: string;
  display: string;
  source_name: string | null;
  source_type: string | null;
  source_record_id: string | null;
  evidence_id: string | null;
  verification_status: string | null;
  freshness: string | null;
  derived: boolean;
  derivation_rule: string | null;
  observed_at: string | null;
  need: string;
  value: unknown;
};

export function isSupportedFact(fact: {
  evidence_id?: string | null;
  derived?: boolean;
  verification_status?: string | null;
  freshness?: string | null;
  attribute: string;
}): boolean {
  if (fact.verification_status === "CONFLICTED") return false;
  if (!fact.evidence_id && !fact.derived) return false;
  if (OPERATIONAL.has(fact.attribute) && fact.freshness === "STALE") {
    return false;
  }
  return true;
}

export function uniqueFacts(match: RankedProductMatch): DisplayFact[] {
  const seen = new Set<string>();
  const facts: DisplayFact[] = [];
  for (const reason of match.reasons) {
    for (const fact of reason.facts) {
      if (!isSupportedFact(fact)) continue;
      const key = fact.display.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      facts.push({
        attribute: fact.attribute,
        display: fact.display,
        source_name: fact.source_name,
        source_type: fact.source_type ?? null,
        source_record_id: fact.source_record_id ?? null,
        evidence_id: fact.evidence_id,
        verification_status: fact.verification_status ?? null,
        freshness: fact.freshness ?? null,
        derived: Boolean(fact.derived),
        derivation_rule: fact.derivation_rule ?? null,
        observed_at: fact.observed_at ?? null,
        need: reason.need,
        value: fact.value,
      });
    }
  }
  return facts;
}

export function primaryReasons(match: RankedProductMatch, limit = 5) {
  return uniqueFacts(match).slice(0, limit);
}

export function groupedRationale(match: RankedProductMatch, limit = 3) {
  const groups: { label: string; facts: string[] }[] = [];
  const used = new Set<string>();
  for (const reason of match.reasons) {
    const facts: string[] = [];
    for (const fact of reason.facts) {
      if (!isSupportedFact(fact)) continue;
      const key = fact.display.toLowerCase();
      if (used.has(key)) continue;
      used.add(key);
      facts.push(fact.display);
    }
    if (!facts.length) continue;
    groups.push({ label: contextLabel(reason.need), facts });
    if (groups.length >= limit) break;
  }
  return groups;
}

export function prettyFactDisplay(
  attribute: string,
  display: string,
): string {
  if (/:\s*true$/i.test(display)) return fieldLabel(attribute);
  if (/:\s*false$/i.test(display)) return `No ${fieldLabel(attribute)}`;
  const hours = display.match(/battery hours:\s*(\d+)/i);
  if (hours) return `${hours[1]}h battery`;
  const weight = display.match(/weight:\s*(\d+)/i);
  if (weight) return `${weight[1]}g`;
  const score = display.match(/^(?:comfort|travel) score:\s*([\d.]+)/i);
  if (score) return `${fieldLabel(attribute)} ${score[1]}`;
  return display;
}

export function remainingSignalCount(match: RankedProductMatch) {
  const total = uniqueFacts(match).length;
  return Math.max(0, total - 5);
}

export function factValue(
  match: RankedProductMatch,
  attributes: string[],
): string | null {
  for (const fact of match.evidence) {
    if (!isSupportedFact(fact)) continue;
    if (attributes.includes(fact.attribute) && fact.display) {
      return fact.display;
    }
  }
  for (const fact of uniqueFacts(match)) {
    if (attributes.includes(fact.attribute) && fact.display) {
      return fact.display;
    }
  }
  return null;
}

export function displayedCoverage(match: RankedProductMatch): number | null {
  const rate = match.proof_coverage?.match_rationale_proof_rate;
  if (typeof rate === "number") return rate;
  const facts = uniqueFacts(match);
  if (!facts.length) return null;
  return 1;
}

export function proofItems(match: RankedProductMatch): ProofItem[] {
  if (match.proof?.length) return match.proof.filter((item) => !item.incomplete);
  return uniqueFacts(match).map((fact) => ({
    claim_key: fact.attribute,
    display_claim: prettyFactDisplay(fact.attribute, fact.display),
    value: fact.value,
    evidence_id: fact.evidence_id,
    source_type: fact.source_type ?? "MERCHANT_PRODUCT_FEED",
    source_name: fact.source_name,
    source_record_id: fact.source_record_id,
    verification_status: fact.verification_status ?? "UNKNOWN",
    freshness_status: fact.freshness ?? "UNKNOWN",
    observed_at: fact.observed_at,
    derived: fact.derived,
    derivation_rule: fact.derivation_rule,
    group: "PRODUCT",
  }));
}

export function tradeOffLine(
  match: RankedProductMatch,
  peers: RankedProductMatch[],
): string | null {
  if (match.unsupported_needs.length) {
    return `Limited evidence for ${match.unsupported_needs
      .slice(0, 2)
      .map(contextLabel)
      .join(", ")}.`;
  }
  const leader = peers[0];
  if (!leader || match.variant_id === leader.variant_id) return null;
  if (match.preference_fit + 0.04 < leader.preference_fit) {
    return `Lower preference fit than ${leader.product_name}.`;
  }
  if (match.context_fit + 0.04 < leader.context_fit) {
    return `Weaker travel-context fit than the top match.`;
  }
  return null;
}

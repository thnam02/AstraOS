import { contextLabel, fieldLabel } from "@/lib/intent";
import type { RankedProductMatch } from "@/types";

export type SourceBadge = {
  code: "SPEC" | "SYNTHETIC" | "FULFILMENT" | "INVENTORY" | "PRICING";
  title: string;
};

export function sourceBadge(sourceName: string | null): SourceBadge {
  const raw = sourceName ?? "Source";
  const text = raw.toLowerCase();
  if (text.includes("synthetic") || text.includes("fixture")) {
    return { code: "SYNTHETIC", title: raw };
  }
  if (
    text.includes("fulfil") ||
    text.includes("fulfill") ||
    text.includes("delivery")
  ) {
    return { code: "FULFILMENT", title: raw };
  }
  if (text.includes("inventor")) {
    return { code: "INVENTORY", title: raw };
  }
  if (text.includes("price") || text.includes("pricing")) {
    return { code: "PRICING", title: raw };
  }
  return { code: "SPEC", title: raw };
}

export function uniqueFacts(match: RankedProductMatch) {
  const seen = new Set<string>();
  const facts: {
    attribute: string;
    display: string;
    source_name: string | null;
    need: string;
  }[] = [];
  for (const reason of match.reasons) {
    for (const fact of reason.facts) {
      const key = fact.display.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      facts.push({
        attribute: fact.attribute,
        display: fact.display,
        source_name: fact.source_name,
        need: reason.need,
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

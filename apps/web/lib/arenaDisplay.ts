import { formatUtilityShort } from "@/lib/format";
import { formatAudCents } from "./money";
import type {
  ArenaRunResponse,
  ArenaStrategyResponse,
  BuyerProfile,
} from "@/types";

export const STRATEGY_META: Record<
  string,
  { title: string; subtitle: string; tooltip: string }
> = {
  DEFAULT: {
    title: "Default Merchant",
    subtitle: "Standard product + standard terms",
    tooltip: "What happens if the retailer simply exposes its standard offer?",
  },
  ALWAYS_DISCOUNT: {
    title: "Always Discount",
    subtitle: "Price-first merchant strategy",
    tooltip: "What happens if the retailer's primary lever is price?",
  },
  CHEAPEST_ELIGIBLE: {
    title: "Cheapest Eligible",
    subtitle: "Lowest valid total price",
    tooltip:
      "What happens if the retailer optimises for the lowest valid buyer price?",
  },
  SEMANTIC_ONLY: {
    title: "Semantic Only",
    subtitle: "Best semantic product + standard terms",
    tooltip:
      "What happens if the retailer only improves product matching and keeps default terms?",
  },
  ASTRAOS: {
    title: "AstraOS",
    subtitle: "Whole-offer commercial optimisation",
    tooltip:
      "What happens if the retailer optimises across the entire offer vector?",
  },
};

export const WEIGHT_LABELS: Record<string, string> = {
  product: "Product fit",
  price: "Price",
  delivery: "Delivery",
  warranty: "Warranty",
  bundle: "Bundle",
  returns: "Returns",
};

export const POLICY_REASON_LABELS: Record<string, string> = {
  MARGIN_BELOW_FLOOR: "Minimum margin policy",
  DISCOUNT_EXCEEDS_LIMIT: "Discount exceeds policy limit",
  INTENT_DELIVERY_INCOMPATIBLE: "Same-day delivery is mandatory",
  OUT_OF_STOCK: "Inventory unavailable",
  DELIVERY_DISABLED: "Delivery option disabled",
  WARRANTY_DISABLED: "Warranty option disabled",
  BUNDLE_DISABLED: "Bundle option disabled",
  RETURNS_DISABLED: "Returns option disabled",
  PRODUCT_INACTIVE: "Product inactive",
  NO_POLICY_SAFE_OFFER: "No policy-safe offer in this space",
  NO_ELIGIBLE_PRODUCT: "No eligible product",
  NO_BASELINE_CONFIGURATION: "No baseline configuration",
  NO_DISCOUNT_CONFIGURATION: "No discount configuration",
};

const TIE_EPSILON = 0.01;

export function strategyTitle(name: string): string {
  return STRATEGY_META[name]?.title ?? name.replaceAll("_", " ");
}

export function isSelectable(response: ArenaStrategyResponse): boolean {
  return Boolean(
    response.policy_safe &&
      response.hard_constraints_satisfied &&
      response.offer_id,
  );
}

export function titleCaseCode(code: string): string {
  return code
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function deliveryLabel(
  code: string | null,
  days: number | null = null,
): string {
  if (!code) return "No delivery";
  if (code === "SAME_DAY" || days === 0) return "Same-day delivery";
  if (code === "STANDARD") return "Standard delivery";
  if (code === "EXPRESS") return "Express delivery";
  if (code === "TWO_DAY") return "Two-day delivery";
  return titleCaseCode(code);
}

export function warrantyLabel(
  code: string | null,
  months: number | null = null,
): string {
  if (months != null) return `${months}-month warranty`;
  if (!code) return "No warranty";
  if (code === "STANDARD_12") return "12-month warranty";
  const extended = /^EXTENDED_(\d+)$/.exec(code);
  if (extended) return `${extended[1]}-month warranty`;
  return titleCaseCode(code);
}

export function bundleLabel(code: string | null): string {
  if (!code || code === "NONE") return "No bundle";
  if (code === "HARD_CASE") return "Hard case";
  if (code === "TRAVEL_ADAPTER") return "Travel adapter";
  return titleCaseCode(code);
}

export function returnsLabel(
  code: string | null,
  days: number | null = null,
): string {
  if (days != null) return `${days}-day returns`;
  if (!code) return "No returns";
  if (code === "STANDARD_30") return "30-day returns";
  const flex = /^(?:FLEX|STANDARD)_(\d+)$/.exec(code);
  if (flex) return `${flex[1]}-day returns`;
  return titleCaseCode(code);
}

export function feasibilityLabel(status: string | null): string {
  if (!status) return "Unknown";
  if (status === "FEASIBLE") return "Feasible";
  if (status === "REJECTED") return "Rejected";
  return titleCaseCode(status);
}

export function policyReasons(failure: string | null): string[] {
  if (!failure) return [];
  return failure
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((code) => POLICY_REASON_LABELS[code] ?? titleCaseCode(code));
}

export type StrategyValidity = "POLICY_SAFE" | "NO_SAFE_OFFER";

export function strategyValidity(
  response: ArenaStrategyResponse,
): StrategyValidity {
  return isSelectable(response) ? "POLICY_SAFE" : "NO_SAFE_OFFER";
}

export function selectedStrategy(
  duel: ArenaRunResponse,
): ArenaStrategyResponse | null {
  if (duel.buyer_selection.no_purchase) return null;
  const name = duel.buyer_selection.selected_strategy;
  return (
    duel.strategies.find((item) => item.response.strategy_name === name)
      ?.response ?? null
  );
}

export function validResponses(
  duel: ArenaRunResponse,
): ArenaStrategyResponse[] {
  return duel.strategies
    .map((item) => item.response)
    .filter(isSelectable)
    .sort((a, b) => (b.buyer_utility ?? 0) - (a.buyer_utility ?? 0));
}

export function strongestBaseline(
  duel: ArenaRunResponse,
): ArenaStrategyResponse | null {
  const winner = selectedStrategy(duel);
  return (
    validResponses(duel).find(
      (item) => item.strategy_name !== winner?.strategy_name,
    ) ?? null
  );
}

export function signedDelta(value: number, digits = 2): string {
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}`;
}

export function moneyDelta(cents: number): string {
  const formatted = formatAudCents(Math.abs(cents));
  if (cents > 0) return `+${formatted}`;
  if (cents < 0) return `−${formatted}`;
  return formatted;
}

export function nearTie(duel: ArenaRunResponse): boolean {
  const valid = validResponses(duel);
  if (valid.length < 2) return false;
  const top = valid[0]?.buyer_utility ?? 0;
  const next = valid[1]?.buyer_utility ?? 0;
  return Math.abs(top - next) < TIE_EPSILON;
}

export type OfferDiff = {
  deliveryChanged: boolean;
  warrantyChanged: boolean;
  bundleChanged: boolean;
  priceChanged: boolean;
  productChanged: boolean;
  returnsChanged: boolean;
};

export function offerDiff(
  current: ArenaStrategyResponse,
  reference: ArenaStrategyResponse | null,
): OfferDiff {
  if (!reference) {
    return {
      deliveryChanged: false,
      warrantyChanged: false,
      bundleChanged: false,
      priceChanged: false,
      productChanged: false,
      returnsChanged: false,
    };
  }
  return {
    deliveryChanged: current.delivery !== reference.delivery,
    warrantyChanged: current.warranty !== reference.warranty,
    bundleChanged: (current.bundle ?? "NONE") !== (reference.bundle ?? "NONE"),
    priceChanged:
      current.total_customer_price_cents !==
      reference.total_customer_price_cents,
    productChanged: current.sku !== reference.sku,
    returnsChanged: (current.returns ?? "") !== (reference.returns ?? ""),
  };
}

export function findStrategy(
  duel: ArenaRunResponse,
  name: string,
): ArenaStrategyResponse | null {
  return (
    duel.strategies.find((item) => item.response.strategy_name === name)
      ?.response ?? null
  );
}

export function componentDeltaLines(
  duel: ArenaRunResponse,
): { component: string; delta: number; signed: string }[] {
  const rows = duel.explanation.component_deltas ?? [];
  return rows.map((row) => ({
    component: row.component,
    delta: row.delta,
    signed: signedDelta(row.delta, 2),
  }));
}

export function commercialDifference(
  left: ArenaStrategyResponse,
  right: ArenaStrategyResponse,
): { label: string; from: string; to: string; changed: boolean; delta?: string }[] {
  const priceDeltaCents =
    left.total_customer_price_cents != null &&
    right.total_customer_price_cents != null
      ? right.total_customer_price_cents - left.total_customer_price_cents
      : null;
  const utilityDelta =
    left.buyer_utility != null && right.buyer_utility != null
      ? right.buyer_utility - left.buyer_utility
      : null;
  const contributionDeltaCents =
    left.merchant_contribution_cents != null &&
    right.merchant_contribution_cents != null
      ? right.merchant_contribution_cents - left.merchant_contribution_cents
      : null;
  const interventionDeltaCents =
    left.intervention_cost_cents != null &&
    right.intervention_cost_cents != null
      ? right.intervention_cost_cents - left.intervention_cost_cents
      : null;

  return [
    {
      label: "Product",
      from: left.product_name ?? "—",
      to: right.product_name ?? "—",
      changed: left.sku !== right.sku,
    },
    {
      label: "Price",
      from:
        left.total_customer_price_cents != null
          ? formatAudCents(left.total_customer_price_cents)
          : "—",
      to:
        right.total_customer_price_cents != null
          ? formatAudCents(right.total_customer_price_cents)
          : "—",
      changed:
        left.total_customer_price_cents !== right.total_customer_price_cents,
      delta: priceDeltaCents != null ? moneyDelta(priceDeltaCents) : undefined,
    },
    {
      label: "Delivery",
      from: deliveryLabel(left.delivery, left.delivery_days),
      to: deliveryLabel(right.delivery, right.delivery_days),
      changed: left.delivery !== right.delivery,
    },
    {
      label: "Warranty",
      from: warrantyLabel(left.warranty, left.warranty_months),
      to: warrantyLabel(right.warranty, right.warranty_months),
      changed: left.warranty !== right.warranty,
    },
    {
      label: "Bundle",
      from: bundleLabel(left.bundle),
      to: bundleLabel(right.bundle),
      changed: (left.bundle ?? "NONE") !== (right.bundle ?? "NONE"),
    },
    {
      label: "Returns",
      from: returnsLabel(left.returns),
      to: returnsLabel(right.returns),
      changed: (left.returns ?? "") !== (right.returns ?? ""),
    },
    {
      label: "Buyer Utility",
      from:
        left.buyer_utility != null
          ? formatUtilityShort(left.buyer_utility)
          : "—",
      to:
        right.buyer_utility != null
          ? formatUtilityShort(right.buyer_utility)
          : "—",
      changed: left.buyer_utility !== right.buyer_utility,
      delta: utilityDelta != null ? signedDelta(utilityDelta) : undefined,
    },
    {
      label: "Contribution",
      from:
        left.merchant_contribution_cents != null
          ? formatAudCents(left.merchant_contribution_cents)
          : "—",
      to:
        right.merchant_contribution_cents != null
          ? formatAudCents(right.merchant_contribution_cents)
          : "—",
      changed:
        left.merchant_contribution_cents !== right.merchant_contribution_cents,
      delta:
        contributionDeltaCents != null
          ? moneyDelta(contributionDeltaCents)
          : undefined,
    },
    {
      label: "Intervention",
      from:
        left.intervention_cost_cents != null
          ? formatAudCents(left.intervention_cost_cents)
          : "—",
      to:
        right.intervention_cost_cents != null
          ? formatAudCents(right.intervention_cost_cents)
          : "—",
      changed: left.intervention_cost_cents !== right.intervention_cost_cents,
      delta:
        interventionDeltaCents != null
          ? moneyDelta(interventionDeltaCents)
          : undefined,
    },
  ];
}

export function merchantEconomicsLine(
  winner: ArenaStrategyResponse,
  baseline: ArenaStrategyResponse,
): string {
  const fit = (winner.buyer_utility ?? 0) - (baseline.buyer_utility ?? 0);
  const contrib =
    (winner.merchant_contribution_cents ?? 0) -
    (baseline.merchant_contribution_cents ?? 0);
  const winnerName = strategyTitle(winner.strategy_name);
  const baseName = strategyTitle(baseline.strategy_name);
  if (contrib >= 0) {
    return `${winnerName} gained ${signedDelta(fit)} simulated buyer utility while preserving ${moneyDelta(contrib)} contribution vs ${baseName}.`;
  }
  return `${winnerName} sacrificed ${moneyDelta(contrib)} contribution for ${signedDelta(fit)} simulated buyer utility vs ${baseName}.`;
}

export function winnerReasons(
  duel: ArenaRunResponse,
): string[] {
  const winner = selectedStrategy(duel);
  const baseline = strongestBaseline(duel);
  if (!winner) return [];
  const lines: string[] = [];
  const valid = validResponses(duel);
  if (valid[0]?.strategy_name === winner.strategy_name) {
    lines.push("Strongest overall buyer fit");
  }
  if (winner.delivery_days === 0) {
    lines.push("Same-day fulfilment matched urgency");
  }
  if (
    baseline &&
    (winner.warranty_months ?? 0) > (baseline.warranty_months ?? 0)
  ) {
    lines.push("Reliability improved through extended warranty");
  }
  if (winner.policy_safe) {
    lines.push("Remained policy-safe");
  }
  if (
    baseline &&
    (winner.merchant_contribution_cents ?? 0) >
      (baseline.merchant_contribution_cents ?? 0)
  ) {
    lines.push("Preserved stronger merchant contribution");
  }
  for (const reason of duel.explanation.reasons ?? []) {
    if (!lines.some((line) => reason.toLowerCase().includes(line.toLowerCase().slice(0, 12)))) {
      lines.push(reason);
    }
  }
  return lines.slice(0, 5);
}

export function primaryDecisionSentence(duel: ArenaRunResponse): string {
  if (duel.buyer_selection.no_purchase) {
    return (
      duel.explanation.reasons?.[0] ??
      "No merchant response exceeded the simulated buyer's acceptance threshold."
    );
  }
  const winner = selectedStrategy(duel);
  const baseline = strongestBaseline(duel);
  if (
    winner &&
    baseline &&
    winner.delivery_days === 0 &&
    (baseline.delivery_days ?? 99) > 0
  ) {
    if ((winner.warranty_months ?? 0) > (baseline.warranty_months ?? 0)) {
      return "Same-day delivery and stronger assurance outweighed the cheaper baseline price.";
    }
    return "Same-day fulfilment outweighed the cheaper baseline price.";
  }
  return (
    duel.explanation.reasons?.[0] ??
    "The simulated buyer chose the highest transparent utility under the declared weights."
  );
}

export function comparisonRows(
  left: ArenaStrategyResponse,
  right: ArenaStrategyResponse,
) {
  return [
    {
      label: "Product",
      left: left.product_name ?? "—",
      right: right.product_name ?? "—",
    },
    {
      label: "Price",
      left:
        left.total_customer_price_cents != null
          ? formatAudCents(left.total_customer_price_cents)
          : "—",
      right:
        right.total_customer_price_cents != null
          ? formatAudCents(right.total_customer_price_cents)
          : "—",
    },
    {
      label: "Delivery",
      left: deliveryLabel(left.delivery, left.delivery_days),
      right: deliveryLabel(right.delivery, right.delivery_days),
    },
    {
      label: "Warranty",
      left: warrantyLabel(left.warranty, left.warranty_months),
      right: warrantyLabel(right.warranty, right.warranty_months),
    },
    {
      label: "Bundle",
      left: bundleLabel(left.bundle),
      right: bundleLabel(right.bundle),
    },
    {
      label: "Returns",
      left: returnsLabel(left.returns),
      right: returnsLabel(right.returns),
    },
    {
      label: "Buyer Utility",
      left:
        left.buyer_utility != null
          ? formatUtilityShort(left.buyer_utility)
          : "—",
      right:
        right.buyer_utility != null
          ? formatUtilityShort(right.buyer_utility)
          : "—",
    },
    {
      label: "Contribution",
      left:
        left.merchant_contribution_cents != null
          ? formatAudCents(left.merchant_contribution_cents)
          : "—",
      right:
        right.merchant_contribution_cents != null
          ? formatAudCents(right.merchant_contribution_cents)
          : "—",
    },
    {
      label: "Intervention",
      left:
        left.intervention_cost_cents != null
          ? formatAudCents(left.intervention_cost_cents)
          : "—",
      right:
        right.intervention_cost_cents != null
          ? formatAudCents(right.intervention_cost_cents)
          : "—",
    },
    {
      label: "Policy Status",
      left: isSelectable(left) ? "Policy safe" : "No safe offer",
      right: isSelectable(right) ? "Policy safe" : "No safe offer",
    },
  ];
}

export function tradeOffSummary(
  winner: ArenaStrategyResponse,
  baseline: ArenaStrategyResponse,
) {
  const fit = (winner.buyer_utility ?? 0) - (baseline.buyer_utility ?? 0);
  const contrib =
    (winner.merchant_contribution_cents ?? 0) -
    (baseline.merchant_contribution_cents ?? 0);
  return {
    fitDelta: signedDelta(fit),
    contributionDelta: moneyDelta(contrib),
    baselineName: strategyTitle(baseline.strategy_name),
  };
}

export function headline(duel: ArenaRunResponse): {
  title: string;
  body: string;
} {
  if (duel.buyer_selection.no_purchase) {
    return {
      title: "No purchase",
      body: "No merchant response exceeded the simulated buyer's acceptance threshold.",
    };
  }
  const winner = selectedStrategy(duel);
  const baseline = strongestBaseline(duel);
  const name = winner ? strategyTitle(winner.strategy_name) : "A strategy";
  const changed =
    winner &&
    baseline &&
    (winner.delivery !== baseline.delivery ||
      winner.warranty !== baseline.warranty ||
      (winner.bundle ?? "NONE") !== (baseline.bundle ?? "NONE"));
  return {
    title: `${name} won this simulated mission`,
    body: changed
      ? "Rather than competing only on price, AstraOS changed delivery, warranty and bundle configuration."
      : "The simulated buyer selected the highest transparent utility under the declared weights.",
  };
}

export function profileLabel(profile: string): string {
  const labels: Record<string, string> = {
    URGENT_TRAVELLER: "Urgent traveller",
    BUDGET_SHOPPER: "Budget shopper",
    ASSURANCE_BUYER: "Assurance",
    QUALITY_FIRST: "Quality first",
    BALANCED: "Balanced",
    INTENT_ADAPTED: "Intent-adapted",
  };
  return labels[profile] ?? profile.replaceAll("_", " ");
}

export function qualitativePriorities(
  profile: BuyerProfile,
): { label: string; level: string }[] {
  if (profile === "URGENT_TRAVELLER") {
    return [
      { label: "Delivery", level: "High" },
      { label: "Comfort", level: "High" },
      { label: "Reliability", level: "High" },
      { label: "Price", level: "Low–medium" },
    ];
  }
  if (profile === "BUDGET_SHOPPER") {
    return [
      { label: "Price", level: "High" },
      { label: "Product fit", level: "Medium" },
      { label: "Delivery", level: "Low–medium" },
    ];
  }
  if (profile === "ASSURANCE_BUYER") {
    return [
      { label: "Warranty", level: "High" },
      { label: "Reliability", level: "High" },
      { label: "Price", level: "Low–medium" },
    ];
  }
  return [
    { label: "Product fit", level: "Medium" },
    { label: "Price", level: "Medium" },
    { label: "Delivery", level: "Medium" },
  ];
}

export function weightRows(
  weights: Record<string, number> | undefined,
): { key: string; label: string; pct: number }[] {
  return Object.entries(WEIGHT_LABELS).map(([key, label]) => ({
    key,
    label,
    pct: Math.round((weights?.[key] ?? 0) * 100),
  }));
}

export function componentNote(
  key: string,
  winner: ArenaStrategyResponse | null,
  baseline: ArenaStrategyResponse | null,
): string {
  if (!winner) return "";
  if (key === "delivery" && winner.delivery_days === 0) {
    return "AstraOS strongest";
  }
  if (key === "warranty" && (winner.warranty_months ?? 0) >= 36) {
    return "36-month coverage";
  }
  if (key === "price" && winner.total_customer_price_cents != null) {
    return "Within budget";
  }
  if (key === "bundle" && winner.bundle) return "Relevant travel protection";
  if (key === "product") return "Strong";
  if (key === "returns") return "Comparable";
  if (baseline && key === "delivery") return "Differed";
  return "";
}

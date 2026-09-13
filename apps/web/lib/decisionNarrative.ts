import {
  deliveryLabel,
  bundleLabel,
  warrantyLabel,
  returnsLabel,
} from "./arenaDisplay";
import { HERO_INTENT } from "./intent";
import { formatAudCents } from "./money";
import type {
  CounterfactualRow,
  GenerateOffersResponse,
  OptimisationResponse,
  PublicOffer,
  PublicScoredOffer,
  RankedProductMatch,
} from "../types";

export const METRIC_HELP = {
  productMatch:
    "How strongly the product itself aligns with the buyer’s validated intent.",
  buyerUtility:
    "Transparent cold-start score for the complete commercial offer. Not purchase probability.",
  contribution:
    "Merchant contribution after product and commercial intervention costs.",
  pareto:
    "No other available offer improves buyer utility without reducing merchant contribution, or vice versa.",
} as const;

export type OfferTerms = {
  product_name: string;
  sku?: string;
  price_cents?: number;
  delivery_code: string | null;
  delivery_name?: string;
  delivery_days?: number | null;
  warranty_code: string | null;
  warranty_months?: number | null;
  bundle_code: string | null;
  bundle_name?: string | null;
  return_code: string | null;
  return_days?: number | null;
};

export type CommercialDelta = {
  field: "Price" | "Delivery" | "Warranty" | "Bundle" | "Returns";
  from: string;
  to: string;
};

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
    offer.returns?.window_days
      ? `${offer.returns.window_days}-day returns`
      : "Standard returns",
  ];
}

function isBaselineCodes(
  delivery: string | null | undefined,
  warranty: string | null | undefined,
  bundle: string | null | undefined,
  returns: string | null | undefined,
  adjustment?: string | null,
) {
  if (adjustment && adjustment !== "BASE") return false;
  return (
    delivery === "STANDARD" &&
    warranty === "STANDARD_12" &&
    (bundle == null || bundle === "NONE") &&
    (returns == null || returns === "STANDARD_30")
  );
}

export function termsFromScored(offer: PublicScoredOffer): OfferTerms {
  return {
    product_name: offer.product_name,
    sku: offer.sku,
    price_cents: offer.pricing.total_price_cents,
    delivery_code: offer.delivery.code,
    delivery_name: offer.delivery.name,
    delivery_days: offer.delivery.days,
    warranty_code: offer.warranty.code,
    warranty_months: offer.warranty.months,
    bundle_code: offer.bundle?.code ?? null,
    bundle_name: offer.bundle?.name ?? null,
    return_code: offer.returns?.code ?? null,
    return_days: offer.returns?.window_days ?? null,
  };
}

function sameProduct(
  product: RankedProductMatch,
  sku: string | null | undefined,
  name: string | null | undefined,
) {
  if (product.sku && sku) return product.sku === sku;
  return Boolean(name) && product.product_name === name;
}

export function baselineTermsForProduct(
  product: RankedProductMatch | null | undefined,
  optimisation: OptimisationResponse | null | undefined,
  construction: GenerateOffersResponse | null | undefined,
): OfferTerms | null {
  if (!product) return null;
  const listed = construction?.product_baselines?.find((item: PublicOffer) =>
    sameProduct(product, item.product.sku, item.product.name),
  );
  if (listed) {
    return {
      product_name: listed.product.name,
      sku: listed.product.sku,
      price_cents: listed.pricing.total_price_cents,
      delivery_code: listed.delivery.code,
      delivery_name: listed.delivery.name,
      delivery_days: listed.delivery.days,
      warranty_code: listed.warranty.code,
      warranty_months: listed.warranty.months,
      bundle_code: listed.bundle?.code ?? null,
      bundle_name: listed.bundle?.name ?? null,
      return_code: listed.returns?.code ?? null,
      return_days: listed.returns?.window_days ?? null,
    };
  }
  const scored = [
    optimisation?.recommended_offer,
    ...(optimisation?.pareto_offers ?? []),
    ...(optimisation?.alternative_pareto_offers ?? []),
  ].filter((item): item is PublicScoredOffer => Boolean(item));
  const scoredBaseline = scored.find(
    (item) => item.is_baseline && sameProduct(product, item.sku, item.product_name),
  );
  if (scoredBaseline) return termsFromScored(scoredBaseline);

  const constructed = construction?.offers.find((item: PublicOffer) => {
    if (!sameProduct(product, item.product.sku, item.product.name)) return false;
    return isBaselineCodes(
      item.delivery.code,
      item.warranty.code,
      item.bundle?.code,
      item.returns?.code,
      item.pricing.adjustment_type,
    );
  });
  if (constructed) {
    return {
      product_name: constructed.product.name,
      sku: constructed.product.sku,
      price_cents: constructed.pricing.total_price_cents,
      delivery_code: constructed.delivery.code,
      delivery_name: constructed.delivery.name,
      delivery_days: constructed.delivery.days,
      warranty_code: constructed.warranty.code,
      warranty_months: constructed.warranty.months,
      bundle_code: constructed.bundle?.code ?? null,
      bundle_name: constructed.bundle?.name ?? null,
      return_code: constructed.returns?.code ?? null,
      return_days: constructed.returns?.window_days ?? null,
    };
  }

  const point = optimisation?.plot_points.find(
    (item) =>
      sameProduct(product, item.sku, item.product_name) &&
      isBaselineCodes(
        item.delivery_code,
        item.warranty_code,
        item.bundle_code,
        item.return_policy_code,
      ),
  );
  if (!point) return null;
  return {
    product_name: point.product_name,
    sku: point.sku,
    price_cents: point.total_price_cents,
    delivery_code: point.delivery_code,
    warranty_code: point.warranty_code,
    bundle_code: point.bundle_code,
    return_code: point.return_policy_code,
  };
}

function termLabel(
  field: CommercialDelta["field"],
  terms: OfferTerms,
): string | null {
  if (field === "Price") {
    if (terms.price_cents == null) return null;
    return formatAudCents(terms.price_cents);
  }
  if (field === "Delivery") {
    if (!terms.delivery_code && !terms.delivery_name) return null;
    return (
      terms.delivery_name ||
      deliveryLabel(terms.delivery_code, terms.delivery_days ?? null)
    );
  }
  if (field === "Warranty") {
    if (!terms.warranty_code && terms.warranty_months == null) return null;
    return warrantyLabel(terms.warranty_code, terms.warranty_months ?? null);
  }
  if (field === "Bundle") {
    if (terms.bundle_name) return terms.bundle_name;
    return bundleLabel(terms.bundle_code);
  }
  if (!terms.return_code && terms.return_days == null) return null;
  return returnsLabel(terms.return_code, terms.return_days ?? null);
}

export function commercialDeltas(
  from: OfferTerms | null,
  to: OfferTerms | null,
): CommercialDelta[] {
  if (!from || !to) return [];
  const fields: CommercialDelta["field"][] = [
    "Price",
    "Delivery",
    "Warranty",
    "Bundle",
    "Returns",
  ];
  const rows: CommercialDelta[] = [];
  for (const field of fields) {
    const left = termLabel(field, from);
    const right = termLabel(field, to);
    if (!left || !right || left === right) continue;
    rows.push({ field, from: left, to: right });
  }
  return rows;
}

function joinDimensions(items: string[]): string {
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

export function winnerChangeSummary(
  topName: string,
  selectedName: string,
  deltas: CommercialDelta[],
): string {
  const dims = deltas.filter((item) => item.field !== "Price");
  if (!dims.length) {
    return `${topName} is the stronger standalone product match. ${selectedName} is the stronger complete offer once merchant economics are considered.`;
  }
  return `${topName} is the stronger standalone product match. ${selectedName} wins the complete offer because it supports ${joinDimensions(dims.map((item) => item.to.toLowerCase()))} and a better buyer/merchant trade-off.`;
}

export function sameProductOfferSummary(
  name: string,
  deltas: CommercialDelta[],
): string {
  const dims = deltas.map((item) => item.field.toLowerCase());
  if (!dims.length) {
    return `${name} remained the strongest product. AstraOS selected its complete commercial configuration.`;
  }
  return `${name} remained the strongest product. AstraOS configured ${joinDimensions(dims)}.`;
}

const BUYER_PRICE_CODES = new Set([
  "BUYER_MAX_TOTAL_EXCEEDED",
  "BUYER_MAX_PRODUCT_PRICE_EXCEEDED",
]);

function compareBound(operator: string, observed: number, expected: number): boolean {
  if (operator === "LT") return observed < expected;
  if (operator === "LTE") return observed <= expected;
  if (operator === "GT") return observed > expected;
  if (operator === "GTE") return observed >= expected;
  if (operator === "EQ") return observed === expected;
  if (operator === "NE") return observed !== expected;
  return true;
}

export function completeOfferMandatorySatisfied(
  offer: Pick<
    PublicScoredOffer,
    | "policy_safe"
    | "policy_rejection_codes"
    | "pricing"
    | "all_mandatory_buyer_constraints_satisfied"
  >,
  intent?: {
    hard_constraints?: Array<{
      field: string;
      operator: string;
      value?: unknown;
      normalized_value?: unknown;
      applies_to?: "CUSTOMER_TOTAL" | "PRODUCT_BASE" | null;
    }>;
  } | null,
): boolean {
  if (offer.all_mandatory_buyer_constraints_satisfied === false) {
    return false;
  }
  if (!offer.policy_safe) return false;
  if (offer.policy_rejection_codes.some((code) => BUYER_PRICE_CODES.has(code))) {
    return false;
  }
  for (const item of intent?.hard_constraints ?? []) {
    if (item.field !== "price") continue;
    const expected = item.normalized_value ?? item.value;
    if (typeof expected !== "number" || !Number.isFinite(expected)) continue;
    const observed =
      item.applies_to === "PRODUCT_BASE"
        ? offer.pricing.product_price_cents
        : offer.pricing.total_price_cents;
    if (!compareBound(item.operator, observed, expected)) return false;
  }
  return true;
}

export function selectableCompleteOffer(
  offer: PublicScoredOffer | null | undefined,
  optimisation?: OptimisationResponse | null,
  intent?: Parameters<typeof completeOfferMandatorySatisfied>[1],
): PublicScoredOffer | null {
  if (!offer) return null;
  if (optimisation?.failure?.code === "NO_COMPLIANT_OFFER") return null;
  if (offer.selectable === false || offer.proposal_eligible === false) return null;
  if (!completeOfferMandatorySatisfied(offer, intent)) return null;
  return offer;
}

export function mandatoryRequirementsCopy(ok: boolean): string {
  return ok
    ? "All mandatory requirements satisfied"
    : "Mandatory requirements not fully satisfied";
}

export function noCompliantOfferCopy(
  optimisation: OptimisationResponse | null | undefined,
): {
  title: string;
  body: string;
  budget: string | null;
  closest: string | null;
  gap: string | null;
} {
  const failure = optimisation?.failure ?? null;
  const near = optimisation?.near_miss ?? null;
  const budgetCents =
    near?.requested_max_price_cents ?? failure?.requested_max_price_cents ?? null;
  const closestCents =
    near?.total_customer_price_cents ??
    failure?.lowest_policy_safe_price_cents ??
    null;
  const gapCents = near?.gap_cents ?? (
    budgetCents != null && closestCents != null
      ? Math.max(0, closestCents - budgetCents)
      : null
  );
  return {
    title: "No complete commercial configuration satisfies the buyer's mandatory total budget.",
    body:
      failure?.message ??
      "No complete offer satisfies the buyer's mandatory constraints.",
    budget: budgetCents != null ? formatAudCents(budgetCents) : null,
    closest: closestCents != null ? formatAudCents(closestCents) : null,
    gap: gapCents != null ? `+${formatAudCents(gapCents)}` : null,
  };
}

export function conciseOfferReasons(lines: string[]): string[] {
  const mapped = lines
    .map((line) => {
      if (/probability|cold-start/i.test(line)) return null;
      if (/mandatory/i.test(line)) return "All mandatory requirements satisfied";
      if (/same-day|urgency/i.test(line)) return "Same-day delivery addresses urgency";
      if (/semantic|product fit/i.test(line)) return "Strong product match";
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
  if (key === "anc") return "Active noise cancellation";
  if (key.includes("fold")) return "Folds for packing";
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

export function expansionSteps(
  construction: GenerateOffersResponse,
  optimisation?: OptimisationResponse | null,
): { label: string; value: string }[] {
  const story = constructStory(construction);
  const steps = [
    { label: "Matched products", value: String(story.products) },
    {
      label: "Candidate offers",
      value: story.generated.toLocaleString(),
    },
    {
      label: "Feasible",
      value: story.feasible.toLocaleString(),
    },
  ];
  if (optimisation?.summary.buyer_compliant != null) {
    steps.push({
      label: "Buyer-compliant",
      value: optimisation.summary.buyer_compliant.toLocaleString(),
    });
  }
  if (optimisation?.summary.policy_safe != null) {
    steps.push({
      label: "Policy-safe",
      value: optimisation.summary.policy_safe.toLocaleString(),
    });
  }
  if (optimisation?.summary.pareto_efficient != null) {
    steps.push({
      label: "Pareto-efficient",
      value: String(optimisation.summary.pareto_efficient),
    });
  }
  if (optimisation?.recommended_offer) {
    steps.push({ label: "Selected response", value: "1" });
  }
  return steps;
}

export function dimensionLine(construction: GenerateOffersResponse): string {
  const story = constructStory(construction);
  return `${story.products} products × ${story.price} price × ${story.delivery} delivery × ${story.warranty} warranty × ${story.bundle} bundle × ${story.returns} returns`;
}

export const PIPELINE_LOADING = [
  "Understanding buyer intent",
  "Checking mandatory constraints",
  "Matching merchant catalogue",
  "Constructing commercial offers",
  "Applying merchant policy",
  "Computing efficient frontier",
  "Creating merchant response",
] as const;

export const STAGE_LABELS: Record<string, string> = {
  understand: "Understand",
  qualify: "Qualify",
  match: "Match",
  construct: "Construct",
  optimise: "Optimise",
  negotiate: "Negotiate",
  transact: "Transact",
  learn: "Learn",
};

export function humanizeCheck(code: string): string {
  const labels: Record<string, string> = {
    PRICE: "Price",
    INVENTORY: "Inventory",
    DELIVERY: "Delivery",
    MERCHANT_POLICY: "Merchant policy",
    POLICY: "Merchant policy",
    WARRANTY: "Warranty",
    BUNDLE: "Bundle",
    RETURNS: "Returns",
    PROPOSAL_EXPIRED: "Proposal expired",
    OUT_OF_STOCK: "Out of stock",
    INSUFFICIENT_STOCK: "Insufficient stock",
    DELIVERY_NO_LONGER_AVAILABLE: "Delivery capacity changed",
    MARGIN_POLICY_VIOLATION: "Merchant policy",
    MERCHANT_POLICY_CHANGED: "Merchant policy changed",
    NO_POLICY_SAFE_OFFER: "No policy-safe offer",
    NO_COMPLIANT_OFFER: "No compliant offer",
    REQUIRES_BUYER_RELAXATION: "Requires buyer relaxation",
    BUYER_MAX_TOTAL_EXCEEDED: "Buyer max total exceeded",
    BUYER_MAX_PRODUCT_PRICE_EXCEEDED: "Buyer max product price exceeded",
    NO_ELIGIBLE_PRODUCT: "No eligible product",
    RESERVATION_FAILED: "Reservation conflict",
    ALREADY_TRANSACTED: "Already transacted",
    TRANSACTION_CONFLICT: "Transaction conflict",
  };
  return labels[code] ?? code.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

export function offerVsProductCopy(differ: boolean): string {
  return differ
    ? "AstraOS optimises the complete merchant response, not the SKU alone."
    : "Top product remained the best complete offer after commercial optimisation.";
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

export const LEARN_STORY = [
  { id: "intent", label: "Intent", body: "What the buyer asked" },
  { id: "offer", label: "Offer", body: "Merchant response sent" },
  { id: "outcome", label: "Outcome", body: "Selected, rejected, or no purchase" },
  { id: "record", label: "Learning record", body: "Intent → Offer → Outcome" },
  { id: "model", label: "Response model", body: "Experimental, synthetic only" },
  { id: "future", label: "Future support", body: "After real B2A outcomes exist" },
] as const;

export const LEARN_STATUS = [
  { label: "Rule-based / deterministic eligibility", state: "ACTIVE" },
  { label: "Real semantic matching", state: "ACTIVE" },
  { label: "Transparent buyer utility", state: "PRIMARY" },
  { label: "Learned response model", state: "EXPERIMENTAL" },
  { label: "Real observed response model", state: "FUTURE" },
] as const;

export const SCENARIOS = [
  {
    id: "headphones",
    label: "Headphones sample",
    profile: "URGENT_TRAVELLER" as const,
    intent: HERO_INTENT,
  },
] as const;

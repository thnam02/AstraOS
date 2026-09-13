import { constraintLabel } from "@/lib/intent";
import { formatAudCents } from "@/lib/money";
import type {
  HardConstraint,
  MerchantProposal,
  NegotiationResponse,
  NegotiationTurn,
  PublicScoredOffer,
  ShoppingIntent,
} from "@/types";

export type ParsedRequestRow = {
  field: string;
  label: string;
  value: string;
};

export type OfferTerms = {
  productName: string | null;
  sku: string | null;
  totalCents: number | null;
  total: string | null;
  delivery: string | null;
  deliveryCode: string | null;
  warranty: string | null;
  warrantyMonths: number | null;
  bundle: string | null;
  returns: string | null;
  utility: number | null;
  contributionCents: number | null;
  contribution: string | null;
};

export type TermDeltaRow = {
  term: string;
  previous: string;
  requested: string;
  counter: string;
  changed: boolean;
};

export type CommercialChange = {
  label: string;
  from: string;
  to: string;
  delta?: string;
};

export type ConstraintChange = {
  kind: "RELAXED" | "ADDED" | "REMOVED" | "UPDATED";
  field: string;
  from: string | null;
  to: string | null;
};

export type WhyNotCopy = {
  title: string;
  requested: string | null;
  closest: string | null;
  gap: string | null;
  reasons: string[];
};

export type TimelineEvent = {
  id: string;
  round: number | null;
  actor: "ASTRAOS" | "BUYER";
  kind:
    | "INITIAL_PROPOSAL"
    | "BUYER_COUNTER"
    | "BUYER_ASK"
    | "COUNTEROFFER"
    | "NO_SAFE_COUNTER"
    | "BUYER_ACCEPTED"
    | "BUYER_REJECTED"
    | "CLARIFY";
  title: string;
  subtitle: string;
  message: string | null;
  parsed: ParsedRequestRow[];
  terms: OfferTerms | null;
  explanation: string[];
  reasonCodes: string[];
  createdAt: string | null;
  inspectPayload: Record<string, unknown> | null;
};

export type StatusPresentation = {
  code: string;
  label: string;
  tone: "positive" | "warning" | "negative" | "neutral" | "info";
};

const STATUS: Record<string, StatusPresentation> = {
  CREATED: { code: "CREATED", label: "Session created", tone: "neutral" },
  BUYER_REQUEST_RECEIVED: {
    code: "BUYER_REQUEST_RECEIVED",
    label: "Buyer request received",
    tone: "info",
  },
  MERCHANT_PROPOSAL_CREATED: {
    code: "MERCHANT_PROPOSAL_CREATED",
    label: "Proposal sent",
    tone: "info",
  },
  BUYER_COUNTERED: {
    code: "BUYER_COUNTERED",
    label: "Buyer counter received",
    tone: "info",
  },
  MERCHANT_COUNTER_CREATED: {
    code: "MERCHANT_COUNTER_CREATED",
    label: "Merchant counter created",
    tone: "info",
  },
  BUYER_ACCEPTED: {
    code: "BUYER_ACCEPTED",
    label: "Buyer accepted",
    tone: "positive",
  },
  READY_FOR_CHECKOUT: {
    code: "READY_FOR_CHECKOUT",
    label: "Buyer accepted",
    tone: "positive",
  },
  BUYER_REJECTED: {
    code: "BUYER_REJECTED",
    label: "Buyer rejected",
    tone: "negative",
  },
  NO_POLICY_SAFE_COUNTER: {
    code: "NO_POLICY_SAFE_COUNTER",
    label: "No safe counter",
    tone: "warning",
  },
  NEGOTIATION_LIMIT_REACHED: {
    code: "NEGOTIATION_LIMIT_REACHED",
    label: "Max turns reached",
    tone: "warning",
  },
  EXPIRED: { code: "EXPIRED", label: "Expired", tone: "warning" },
  CANCELLED: { code: "CANCELLED", label: "Cancelled", tone: "neutral" },
  TRANSACTION_CONFIRMED: {
    code: "TRANSACTION_CONFIRMED",
    label: "Buyer accepted",
    tone: "positive",
  },
};

const REASON_COPY: Record<string, string> = {
  REQUESTED_PRICE_BELOW_MARGIN_FLOOR:
    "Would violate merchant minimum-margin policy.",
  DISCOUNT_EXCEEDS_LIMIT: "Discount would exceed merchant authority.",
  NO_POLICY_SAFE_OFFER:
    "No merchant-policy-safe configuration can satisfy this request.",
  NO_COMPLIANT_OFFER:
    "No complete offer satisfies the buyer's mandatory constraints.",
  CLOSEST_POLICY_SAFE_COUNTER:
    "Closest policy-safe configuration is shown. It is not an exact match.",
  REQUIRES_BUYER_RELAXATION: "Requires buyer relaxation before a compliant proposal.",
  REQUESTED_DELIVERY_UNAVAILABLE:
    "Requested delivery is not available on a safe configuration.",
  SAME_PRODUCT_UNAVAILABLE_AT_REQUEST:
    "This product cannot meet the request safely.",
  ALTERNATIVE_PRODUCT_SELECTED: "An alternative product was selected.",
  NEGOTIATION_LIMIT_REACHED: "Negotiation turn limit reached.",
  PROPOSAL_EXPIRED: "The previous proposal expired.",
  AMBIGUOUS_REQUEST:
    "The buyer message is not a commercial change AstraOS can apply.",
  PROMPT_INJECTION_IGNORED:
    "A buyer instruction that tried to override merchant policy was ignored.",
  UNSUPPORTED_INSTRUCTION: "That instruction is not a supported commercial change.",
};

const BUYER_ACTORS = new Set(["BUYER", "BUYER_AGENT"]);
const SKIP_ACTIONS = new Set(["SESSION_OPENED"]);

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function constraintsFrom(payload: Record<string, unknown> | null | undefined) {
  if (!payload) return {};
  return asRecord(payload.constraints ?? payload);
}

export function negotiationStatus(state: string): StatusPresentation {
  return (
    STATUS[state] ?? {
      code: state,
      label: state.replaceAll("_", " ").toLowerCase(),
      tone: "neutral",
    }
  );
}

export function offerTermsFromProposal(
  proposal: MerchantProposal | null | undefined,
): OfferTerms | null {
  const offer = proposal?.offer ?? null;
  if (!offer) return null;
  return offerTermsFromOffer(offer);
}

export function offerTermsFromOffer(offer: PublicScoredOffer): OfferTerms {
  return {
    productName: offer.product_name ?? null,
    sku: offer.sku ?? null,
    totalCents: offer.pricing?.total_price_cents ?? null,
    total:
      offer.pricing?.total_price_cents != null
        ? formatAudCents(offer.pricing.total_price_cents)
        : null,
    delivery: offer.delivery?.name ?? null,
    deliveryCode: offer.delivery?.code ?? null,
    warranty:
      offer.warranty?.months != null
        ? `${offer.warranty.months}-month warranty`
        : (offer.warranty?.name ?? null),
    warrantyMonths: offer.warranty?.months ?? null,
    bundle: offer.bundle?.name ?? "None",
    returns:
      offer.returns?.window_days != null
        ? `${offer.returns.window_days}-day returns`
        : "Standard",
    utility: typeof offer.buyer_utility === "number" ? offer.buyer_utility : null,
    contributionCents: offer.contribution_margin_cents ?? null,
    contribution:
      offer.contribution_margin_cents != null
        ? formatAudCents(offer.contribution_margin_cents)
        : null,
  };
}

export function parseBuyerRequest(
  payload: Record<string, unknown> | null | undefined,
): ParsedRequestRow[] {
  const constraints = constraintsFrom(payload);
  const rows: ParsedRequestRow[] = [];
  const maxTotal = constraints.max_total_price_cents;
  if (typeof maxTotal === "number") {
    rows.push({
      field: "price",
      label: "Maximum total",
      value: `≤ ${formatAudCents(maxTotal)}`,
    });
  }
  const days = constraints.requested_delivery_days;
  if (typeof days === "number") {
    rows.push({
      field: "delivery",
      label: "Delivery",
      value: days === 0 ? "Same-day" : `≤ ${days} day${days === 1 ? "" : "s"}`,
    });
  }
  if (constraints.relax_same_day === true) {
    rows.push({
      field: "delivery",
      label: "Same-day",
      value: "Relaxed",
    });
  }
  const warranty = constraints.requested_warranty_months;
  if (typeof warranty === "number") {
    rows.push({
      field: "warranty",
      label: "Warranty",
      value: `≥ ${warranty} months`,
    });
  }
  const bundle = constraints.requested_bundle;
  if (typeof bundle === "string" && bundle.trim()) {
    rows.push({ field: "bundle", label: "Bundle", value: bundle });
  }
  const returns = constraints.requested_return_window_days;
  if (typeof returns === "number") {
    rows.push({
      field: "returns",
      label: "Returns",
      value: `${returns}-day`,
    });
  }
  if (constraints.foldable_required === true) {
    rows.push({ field: "foldable", label: "Foldable", value: "Required" });
  }
  const prefs = constraints.preference_changes;
  if (Array.isArray(prefs)) {
    for (const item of prefs) {
      if (typeof item === "string" && item.trim()) {
        rows.push({
          field: "preference",
          label: "Preference",
          value: item,
        });
      }
    }
  }
  return rows;
}

export function requestedValue(
  rows: ParsedRequestRow[],
  field: string,
): string | null {
  return rows.find((row) => row.field === field)?.value ?? null;
}

function proposalForTurn(
  turn: NegotiationTurn,
  proposals: MerchantProposal[],
): MerchantProposal | null {
  if (turn.related_proposal_id) {
    return (
      proposals.find((item) => item.proposal_id === turn.related_proposal_id) ??
      null
    );
  }
  if (turn.related_offer_id) {
    return (
      proposals.find((item) => item.offer_id === turn.related_offer_id) ?? null
    );
  }
  return null;
}

function isOpeningRequest(turn: NegotiationTurn, index: number): boolean {
  return index === 0 && turn.structured_action === "REQUEST";
}

function payloadStrings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.trim() !== "")
    : [];
}

function clarifyCopy(payload: Record<string, unknown>): {
  explanation: string[];
  reasonCodes: string[];
} {
  const reasonCodes = payloadStrings(payload.reason_codes);
  const explanation = payloadStrings(payload.explanation);
  const fromCodes = reasonCodes
    .map((code) => REASON_COPY[code])
    .filter((item): item is string => Boolean(item));
  return {
    reasonCodes,
    explanation: explanation.length ? explanation : fromCodes,
  };
}

export function buildNegotiationTimeline(
  negotiation: NegotiationResponse,
): TimelineEvent[] {
  const proposals = [...negotiation.proposals].sort(
    (a, b) => a.version - b.version,
  );
  const turns = negotiation.turns.filter(
    (turn) => !SKIP_ACTIONS.has(turn.structured_action),
  );
  const events: TimelineEvent[] = [];

  for (const [index, turn] of turns.entries()) {
    if (isOpeningRequest(turn, index)) continue;
    const buyer = BUYER_ACTORS.has(turn.actor);
    const proposal = proposalForTurn(turn, proposals);
    const parsed = buyer ? parseBuyerRequest(turn.structured_payload) : [];
    const action = turn.structured_action;

    if (buyer && action === "COUNTER") {
      events.push({
        id: turn.turn_id,
        round: proposal?.version ?? null,
        actor: "BUYER",
        kind: "BUYER_COUNTER",
        title: "Buyer agent counter",
        subtitle: "Counter",
        message: turn.raw_message,
        parsed,
        terms: null,
        explanation: [],
        reasonCodes: [],
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
      continue;
    }
    if (buyer && action === "ASK_CLARIFICATION") {
      events.push({
        id: turn.turn_id,
        round: negotiation.proposal?.version ?? null,
        actor: "BUYER",
        kind: "BUYER_ASK",
        title: "Buyer agent message",
        subtitle: "Not a commercial counter",
        message: turn.raw_message,
        parsed,
        terms: null,
        explanation: [],
        reasonCodes: [],
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
      continue;
    }
    if (buyer && action === "ACCEPT") {
      events.push({
        id: turn.turn_id,
        round: proposal?.version ?? negotiation.proposal?.version ?? null,
        actor: "BUYER",
        kind: "BUYER_ACCEPTED",
        title: "Buyer accepted",
        subtitle: "Accept",
        message: turn.raw_message,
        parsed: [],
        terms: offerTermsFromProposal(proposal ?? negotiation.proposal),
        explanation: [],
        reasonCodes: ["BUYER_ACCEPTED"],
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
      continue;
    }
    if (buyer && action === "REJECT") {
      events.push({
        id: turn.turn_id,
        round: null,
        actor: "BUYER",
        kind: "BUYER_REJECTED",
        title: "Buyer rejected",
        subtitle: "Reject",
        message: turn.raw_message,
        parsed: [],
        terms: null,
        explanation: [],
        reasonCodes: ["BUYER_REJECTED"],
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
      continue;
    }
    if (!buyer && action === "PROPOSE") {
      events.push({
        id: turn.turn_id,
        round: proposal?.version ?? 1,
        actor: "ASTRAOS",
        kind: "INITIAL_PROPOSAL",
        title: "AstraOS initial proposal",
        subtitle: "Initial proposal",
        message: null,
        parsed: [],
        terms: offerTermsFromProposal(proposal),
        explanation: proposal?.explanation ?? [],
        reasonCodes: proposal?.reason_codes ?? [],
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
      continue;
    }
    if (!buyer && (action === "COUNTER" || action === "DECLINE")) {
      const declined = action === "DECLINE" || !proposal?.offer;
      events.push({
        id: turn.turn_id,
        round: proposal?.version ?? negotiation.proposal?.version ?? null,
        actor: "ASTRAOS",
        kind: declined ? "NO_SAFE_COUNTER" : "COUNTEROFFER",
        title: declined ? "No safe counter" : "AstraOS counteroffer",
        subtitle: declined ? "No safe counter" : "Merchant counter",
        message: null,
        parsed: [],
        terms: offerTermsFromProposal(proposal),
        explanation: proposal?.explanation ?? [],
        reasonCodes: proposal?.reason_codes ?? [],
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
      continue;
    }
    if (!buyer && action === "CLARIFY") {
      const payload = asRecord(turn.structured_payload);
      const copy = clarifyCopy(payload);
      events.push({
        id: turn.turn_id,
        round: negotiation.proposal?.version ?? null,
        actor: "ASTRAOS",
        kind: "CLARIFY",
        title: "Clarification required",
        subtitle: "Clarification required",
        message: null,
        parsed: [],
        terms: null,
        explanation: copy.explanation,
        reasonCodes: copy.reasonCodes,
        createdAt: turn.created_at,
        inspectPayload: turn.structured_payload,
      });
    }
  }

  if (!events.some((item) => item.kind === "INITIAL_PROPOSAL")) {
    const initial =
      proposals.find((item) => item.proposal_type === "INITIAL") ??
      proposals[0] ??
      null;
    if (initial) {
      events.unshift({
        id: initial.proposal_id,
        round: initial.version,
        actor: "ASTRAOS",
        kind: "INITIAL_PROPOSAL",
        title: "AstraOS initial proposal",
        subtitle: "Initial proposal",
        message: null,
        parsed: [],
        terms: offerTermsFromProposal(initial),
        explanation: initial.explanation,
        reasonCodes: initial.reason_codes,
        createdAt: initial.created_at,
        inspectPayload: null,
      });
    }
  }
  return events;
}

export function latestBuyerCounter(
  events: TimelineEvent[],
): TimelineEvent | null {
  return (
    [...events].reverse().find((item) => item.kind === "BUYER_COUNTER") ?? null
  );
}

export function currentMerchantEvent(
  events: TimelineEvent[],
): TimelineEvent | null {
  return (
    [...events]
      .reverse()
      .find(
        (item) =>
          item.actor === "ASTRAOS" &&
          (item.kind === "COUNTEROFFER" ||
            item.kind === "INITIAL_PROPOSAL" ||
            item.kind === "NO_SAFE_COUNTER" ||
            item.kind === "CLARIFY"),
      ) ?? null
  );
}

export function previousOfferTerms(
  negotiation: NegotiationResponse,
): OfferTerms | null {
  if (negotiation.previous_proposal?.offer) {
    return offerTermsFromProposal(negotiation.previous_proposal);
  }
  return null;
}

const UNSATISFIED = new Set([
  "CLOSEST_POLICY_SAFE_COUNTER",
  "REQUESTED_PRICE_BELOW_MARGIN_FLOOR",
  "DISCOUNT_EXCEEDS_LIMIT",
  "NO_POLICY_SAFE_OFFER",
  "NO_COMPLIANT_OFFER",
  "REQUIRES_BUYER_RELAXATION",
  "REQUESTED_DELIVERY_UNAVAILABLE",
  "SAME_PRODUCT_UNAVAILABLE_AT_REQUEST",
]);

export function whyNotBuyerRequest(
  proposal: MerchantProposal | null,
  buyer: TimelineEvent | null,
  previous?: MerchantProposal | null,
): WhyNotCopy | null {
  if (!buyer) return null;
  const requestedCents = (() => {
    const constraints = constraintsFrom(buyer.inspectPayload);
    return typeof constraints.max_total_price_cents === "number"
      ? constraints.max_total_price_cents
      : null;
  })();
  const offer = proposal?.offer ?? previous?.offer ?? null;
  const closestCents = offer?.pricing.total_price_cents ?? null;
  const codes = proposal?.reason_codes ?? [];
  const unsatisfied =
    proposal?.outcome === "DECLINE" ||
    proposal?.outcome === "COUNTEROFFER" ||
    codes.some((code) => UNSATISFIED.has(code)) ||
    (requestedCents != null &&
      closestCents != null &&
      closestCents > requestedCents);
  if (!unsatisfied) return null;
  const requested =
    requestedCents != null
      ? formatAudCents(requestedCents)
      : (buyer.parsed[0]?.value ?? null);
  const closest = closestCents != null ? formatAudCents(closestCents) : null;
  const gap =
    requestedCents != null && closestCents != null
      ? `+${formatAudCents(Math.max(0, closestCents - requestedCents))}`
      : null;
  const reasons = [
    ...codes
      .map((code) => REASON_COPY[code])
      .filter((item): item is string => Boolean(item)),
    ...(proposal?.explanation ?? []),
  ];
  const unique = [...new Set(reasons)];
  return {
    title: requested ? `Why not ${requested}?` : "Why not the buyer request?",
    requested,
    closest,
    gap,
    reasons: unique,
  };
}

export function termDeltaRows(
  previous: OfferTerms | null,
  requested: ParsedRequestRow[],
  current: OfferTerms | null,
): TermDeltaRow[] {
  if (!previous && !current) return [];
  const rows: Array<{ term: string; field: string; prev: string; next: string }> =
    [
      {
        term: "Total",
        field: "price",
        prev: previous?.total ?? "—",
        next: current?.total ?? "—",
      },
      {
        term: "Delivery",
        field: "delivery",
        prev: previous?.delivery ?? "—",
        next: current?.delivery ?? "—",
      },
      {
        term: "Warranty",
        field: "warranty",
        prev: previous?.warranty ?? "—",
        next: current?.warranty ?? "—",
      },
      {
        term: "Bundle",
        field: "bundle",
        prev: previous?.bundle ?? "—",
        next: current?.bundle ?? "—",
      },
      {
        term: "Returns",
        field: "returns",
        prev: previous?.returns ?? "—",
        next: current?.returns ?? "—",
      },
    ];
  return rows
    .map((row) => {
      const asked = requestedValue(requested, row.field) ?? "—";
      const changed = row.prev !== row.next || asked !== "—";
      return {
        term: row.term,
        previous: row.prev,
        requested: asked,
        counter: row.next,
        changed,
      };
    })
    .filter(
      (row) =>
        row.term === "Total" ||
        row.previous !== row.counter ||
        row.requested !== "—",
    );
}

export function commercialChanges(
  previous: OfferTerms | null,
  current: OfferTerms | null,
): CommercialChange[] {
  if (!previous || !current) return [];
  const rows: CommercialChange[] = [];
  if (
    previous.totalCents != null &&
    current.totalCents != null &&
    previous.totalCents !== current.totalCents
  ) {
    const delta = current.totalCents - previous.totalCents;
    rows.push({
      label: "Price",
      from: previous.total ?? "—",
      to: current.total ?? "—",
      delta: `${delta < 0 ? "-" : "+"}${formatAudCents(Math.abs(delta))}`,
    });
  }
  if (previous.delivery && current.delivery && previous.delivery !== current.delivery) {
    rows.push({
      label: "Delivery",
      from: previous.delivery,
      to: current.delivery,
    });
  }
  if (
    previous.warranty &&
    current.warranty &&
    previous.warranty !== current.warranty
  ) {
    rows.push({
      label: "Warranty",
      from: previous.warranty,
      to: current.warranty,
    });
  }
  if (
    previous.utility != null &&
    current.utility != null &&
    previous.utility !== current.utility
  ) {
    const from = previous.utility.toFixed(2);
    const to = current.utility.toFixed(2);
    const delta = Number(to) - Number(from);
    rows.push({
      label: "Buyer utility",
      from,
      to,
      delta: `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}`,
    });
  }
  if (
    previous.contributionCents != null &&
    current.contributionCents != null &&
    previous.contributionCents !== current.contributionCents
  ) {
    const delta = current.contributionCents - previous.contributionCents;
    rows.push({
      label: "Merchant contribution",
      from: previous.contribution ?? "—",
      to: current.contribution ?? "—",
      delta: `${delta < 0 ? "-" : "+"}${formatAudCents(Math.abs(delta))}`,
    });
  }
  return rows;
}

function asIntent(
  value: ShoppingIntent | Record<string, unknown> | null | undefined,
): ShoppingIntent | null {
  if (!value || typeof value !== "object") return null;
  if (!("hard_constraints" in value)) return null;
  return value as ShoppingIntent;
}

export function activeConstraintLabels(
  intent: ShoppingIntent | Record<string, unknown> | null | undefined,
): string[] {
  const parsed = asIntent(intent);
  if (!parsed) return [];
  const labels: string[] = [];
  if (parsed.category) {
    labels.push(parsed.category.replace(/_/g, " "));
  }
  for (const item of parsed.hard_constraints ?? []) {
    const label = constraintLabel(item as HardConstraint);
    if (label && !labels.includes(label)) labels.push(label);
  }
  return labels.slice(0, 6);
}

function constraintKey(item: HardConstraint): string {
  return `${item.field}:${item.applies_to ?? ""}`;
}

export function constraintChanges(
  original: ShoppingIntent | Record<string, unknown> | null | undefined,
  working: ShoppingIntent | Record<string, unknown> | null | undefined,
): ConstraintChange[] {
  const before = asIntent(original);
  const after = asIntent(working);
  if (!before || !after) return [];
  const prev = new Map(
    (before.hard_constraints ?? []).map((item) => [constraintKey(item), item]),
  );
  const next = new Map(
    (after.hard_constraints ?? []).map((item) => [constraintKey(item), item]),
  );
  const changes: ConstraintChange[] = [];
  for (const [key, item] of next) {
    const prior = prev.get(key);
    if (!prior) {
      changes.push({
        kind: "ADDED",
        field: item.field,
        from: null,
        to: constraintLabel(item),
      });
      continue;
    }
    const from = constraintLabel(prior);
    const to = constraintLabel(item);
    if (from === to) continue;
    const priorValue = prior.normalized_value ?? prior.value;
    const nextValue = item.normalized_value ?? item.value;
    const relaxed =
      item.field === "price" &&
      typeof priorValue === "number" &&
      typeof nextValue === "number" &&
      nextValue > priorValue;
    changes.push({
      kind: relaxed ? "RELAXED" : "UPDATED",
      field: item.field,
      from,
      to,
    });
  }
  for (const [key, item] of prev) {
    if (!next.has(key)) {
      changes.push({
        kind: "REMOVED",
        field: item.field,
        from: constraintLabel(item),
        to: null,
      });
    }
  }
  return changes;
}

export function merchantGuardrails(
  proposal: MerchantProposal | null,
  commercial: NegotiationResponse["commercial"],
): { label: string; ok: boolean }[] {
  const rows: { label: string; ok: boolean }[] = [];
  if (proposal?.offer) {
    rows.push({ label: "Minimum margin preserved", ok: true });
    rows.push({ label: "Discount within authority", ok: true });
  }
  if (commercial?.inventory_units != null) {
    rows.push({
      label: "Inventory available",
      ok: commercial.inventory_units > 0,
    });
  }
  return rows;
}

export function buyerMayAct(proposal: MerchantProposal | null, state: string) {
  const actions = new Set(proposal?.next_allowed_actions ?? []);
  const terminal = new Set([
    "BUYER_REJECTED",
    "NEGOTIATION_LIMIT_REACHED",
    "EXPIRED",
    "CANCELLED",
    "TRANSACTION_CONFIRMED",
    "READY_FOR_CHECKOUT",
    "BUYER_ACCEPTED",
  ]);
  if (terminal.has(state)) {
    return { counter: false, accept: false, reject: false };
  }
  return {
    counter: actions.has("COUNTER") || actions.size === 0,
    accept: Boolean(proposal?.offer) && (actions.has("ACCEPT") || actions.size === 0),
    reject: actions.has("REJECT") || actions.size === 0,
  };
}

export function currentRoundLabel(negotiation: NegotiationResponse): string {
  const version = negotiation.proposal?.version;
  if (!version) return "Awaiting proposal";
  if (version <= 1) return "Round 1 · Initial proposal";
  return `Round ${version} · Buyer counter → merchant counter`;
}

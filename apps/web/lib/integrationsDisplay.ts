import {
  bundleLabel,
  deliveryLabel,
  returnsLabel,
  warrantyLabel,
} from "@/lib/arenaDisplay";
import { formatAudCents } from "@/lib/money";
import { humanizeEnum } from "@/lib/format";
import type {
  AgentActivityItem,
  MerchantProposal,
  NegotiationResponse,
  NegotiationTurn,
  PublicScoredOffer,
} from "@/types";

export const AGENT_API_REFERENCE = [
  {
    method: "GET",
    path: "/api/v1/agent/capabilities",
    purpose: "Discover supported operations and protocol surface",
  },
  {
    method: "POST",
    path: "/api/v1/agent/offers/request",
    purpose: "Request a merchant proposal for a buyer intent",
  },
  {
    method: "GET",
    path: "/api/v1/agent/offers/{proposal_id}",
    purpose: "Inspect a machine-readable proposal",
  },
  {
    method: "POST",
    path: "/api/v1/agent/offers/counter",
    purpose: "Submit a buyer counter",
  },
  {
    method: "POST",
    path: "/api/v1/agent/offers/accept",
    purpose: "Accept a valid proposal",
  },
  {
    method: "GET",
    path: "/api/v1/agent/orders/{ref}",
    purpose: "Retrieve merchant order",
  },
  {
    method: "GET",
    path: "/api/v1/agent/transactions/{transaction_id}",
    purpose: "Retrieve execution state",
  },
] as const;

export const OPERATION_COPY: Record<
  string,
  { group: string; label: string }
> = {
  capabilities: { group: "Discovery", label: "List capabilities" },
  request_offer: { group: "Offer discovery", label: "Request tailored offer" },
  inspect_offer: {
    group: "Proposal inspection",
    label: "Retrieve machine-readable proposal",
  },
  counter_offer: { group: "Negotiation", label: "Submit buyer counter" },
  accept_offer: { group: "Acceptance", label: "Accept valid proposal" },
  get_order: { group: "Order", label: "Retrieve merchant order" },
  get_transaction: {
    group: "Transaction",
    label: "Retrieve execution state",
  },
};

export function operationPresentation(operations: string[]) {
  return operations.map((op) => {
    const copy = OPERATION_COPY[op];
    return {
      operation: op,
      group: copy?.group ?? "Operation",
      label: copy?.label ?? humanizeEnum(op),
    };
  });
}

export function activityKindLabel(kind: string): string {
  return humanizeEnum(kind);
}

export function channelLabel(channel: AgentActivityItem["channel"]): string {
  if (channel === "AGENT_API") return "Agent API";
  if (channel === "OPERATOR") return "Operator test";
  return "Unknown";
}

export type ExchangeEventKind =
  | "REQUEST"
  | "PROPOSAL"
  | "COUNTER"
  | "COUNTEROFFER"
  | "ACCEPT"
  | "TRANSACTION"
  | "OTHER";

export type ExchangeEvent = {
  id: string;
  kind: ExchangeEventKind;
  actor: "BUYER AGENT" | "ASTRAOS";
  timestamp: string | null;
  title: string;
  summary?: string;
  terms?: CommercialTermsView | null;
  parsed?: string[];
  reasons?: string[];
  refs?: { label: string; value: string }[];
};

export type CommercialTermsView = {
  product: string | null;
  total: string | null;
  delivery: string | null;
  warranty: string | null;
  bundle: string | null;
  returns: string | null;
  proposalId: string | null;
  status: string | null;
};

function offerTerms(
  offer: PublicScoredOffer | null | undefined,
  proposal?: MerchantProposal | null,
): CommercialTermsView | null {
  if (!offer && !proposal) return null;
  return {
    product: offer?.product_name ?? null,
    total: offer ? formatAudCents(offer.pricing.total_price_cents) : null,
    delivery: offer ? deliveryLabel(offer.delivery.code) : null,
    warranty: offer ? warrantyLabel(offer.warranty.code) : null,
    bundle: offer?.bundle ? bundleLabel(offer.bundle.code) : null,
    returns: offer?.returns ? returnsLabel(offer.returns.code) : null,
    proposalId: proposal?.proposal_id ?? null,
    status: proposal?.outcome ? humanizeEnum(proposal.outcome) : null,
  };
}

function parsedFromTurn(turn: NegotiationTurn): string[] {
  const payload = turn.structured_payload ?? {};
  const lines: string[] = [];
  const max =
    typeof payload.max_total_price_cents === "number"
      ? payload.max_total_price_cents
      : typeof payload.max_total_cents === "number"
        ? payload.max_total_cents
        : null;
  if (max != null) {
    lines.push(`MAX TOTAL ≤ ${formatAudCents(max)}`);
  }
  if (payload.same_day_required === true) {
    lines.push("Same-day delivery required");
  }
  if (typeof payload.delivery === "string") {
    lines.push(deliveryLabel(payload.delivery));
  }
  if (typeof payload.warranty === "string") {
    lines.push(warrantyLabel(payload.warranty));
  }
  if (turn.structured_action && turn.structured_action !== "REQUEST") {
    lines.push(humanizeEnum(turn.structured_action));
  }
  return lines;
}

/** Build chronological exchange events from a real negotiation session. */
export function buildExchangeEvents(
  negotiation: NegotiationResponse,
): ExchangeEvent[] {
  const events: ExchangeEvent[] = [];
  const proposalsById = new Map(
    negotiation.proposals.map((item) => [item.proposal_id, item]),
  );

  for (const turn of negotiation.turns) {
    const actor =
      turn.actor === "BUYER_AGENT" || turn.actor === "BUYER"
        ? "BUYER AGENT"
        : "ASTRAOS";
    const action = turn.structured_action.toUpperCase();

    if (action.includes("REQUEST") && actor === "BUYER AGENT") {
      events.push({
        id: turn.turn_id,
        kind: "REQUEST",
        actor,
        timestamp: turn.created_at,
        title: "Request",
        summary: turn.raw_message ?? undefined,
        parsed: parsedFromTurn(turn),
      });
      continue;
    }

    if (
      (action.includes("COUNTER") || action.includes("MESSAGE")) &&
      actor === "BUYER AGENT"
    ) {
      events.push({
        id: turn.turn_id,
        kind: "COUNTER",
        actor,
        timestamp: turn.created_at,
        title: "Buyer counter",
        summary: turn.raw_message ?? undefined,
        parsed: parsedFromTurn(turn),
      });
      continue;
    }

    if (action.includes("ACCEPT") && actor === "BUYER AGENT") {
      events.push({
        id: turn.turn_id,
        kind: "ACCEPT",
        actor,
        timestamp: turn.created_at,
        title: "Buyer accepted",
        summary: turn.raw_message ?? undefined,
      });
      continue;
    }

    if (actor === "ASTRAOS" || turn.actor === "MERCHANT") {
      const proposal =
        (turn.related_proposal_id &&
          proposalsById.get(turn.related_proposal_id)) ||
        null;
      const isInitial =
        proposal?.proposal_type === "INITIAL" ||
        action.includes("PROPOSAL") ||
        action.includes("OPEN");
      events.push({
        id: turn.turn_id,
        kind: isInitial ? "PROPOSAL" : "COUNTEROFFER",
        actor: "ASTRAOS",
        timestamp: turn.created_at,
        title: isInitial ? "Proposal" : "Counteroffer",
        terms: offerTerms(proposal?.offer ?? null, proposal),
        reasons: proposal?.explanation?.length
          ? proposal.explanation
          : proposal?.reason_codes?.map(humanizeEnum),
        refs: proposal
          ? [
              { label: "Proposal", value: proposal.proposal_id },
              { label: "Status", value: humanizeEnum(proposal.outcome) },
            ]
          : undefined,
      });
    }
  }

  // Fallback when turns are sparse: use proposals chronologically.
  if (events.length === 0 && negotiation.proposals.length) {
    for (const proposal of negotiation.proposals) {
      events.push({
        id: proposal.proposal_id,
        kind: proposal.version <= 1 ? "PROPOSAL" : "COUNTEROFFER",
        actor: "ASTRAOS",
        timestamp: proposal.created_at,
        title: proposal.version <= 1 ? "Proposal" : "Counteroffer",
        terms: offerTerms(proposal.offer, proposal),
        reasons: proposal.explanation,
        refs: [
          { label: "Proposal", value: proposal.proposal_id },
          { label: "Status", value: humanizeEnum(proposal.outcome) },
        ],
      });
    }
  }

  return events;
}

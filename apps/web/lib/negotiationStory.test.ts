import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  activeConstraintLabels,
  buildNegotiationTimeline,
  buyerMayAct,
  commercialChanges,
  constraintChanges,
  currentRoundLabel,
  negotiationStatus,
  parseBuyerRequest,
  termDeltaRows,
  whyNotBuyerRequest,
} from "./negotiationStory";
import type { MerchantProposal, NegotiationResponse, PublicScoredOffer } from "@/types";

function offer(partial: Partial<PublicScoredOffer> & { total: number }): PublicScoredOffer {
  return {
    offer_id: "o1",
    product_name: "Orion Mini 106",
    brand: "Orion",
    sku: "ORI-106",
    variant_id: "v1",
    pricing: {
      product_price_cents: 7980,
      total_price_cents: partial.total,
      currency: "AUD",
    },
    delivery: {
      code: partial.delivery?.code ?? "STANDARD",
      name: partial.delivery?.name ?? "Standard Delivery",
      days: partial.delivery?.days ?? 2,
    },
    warranty: {
      code: "STANDARD_12",
      name: "Standard 12-month warranty",
      months: partial.warranty?.months ?? 12,
    },
    bundle: null,
    returns: { code: "STD_30", window_days: 30 },
    contribution_margin_cents: partial.contribution_margin_cents ?? 3543,
    contribution_margin_rate: 0.4,
    incremental_intervention_cost_cents: 0,
    buyer_utility: partial.buyer_utility ?? 0.48,
    utility_trace: {},
    policy_safe: true,
    policy_rejection_codes: [],
    is_pareto_efficient: true,
    dominated_by_offer_id: null,
    is_recommended: true,
    is_baseline: false,
    product_fit: 0.8,
    ...partial,
  } as PublicScoredOffer;
}

function proposal(
  partial: Partial<MerchantProposal> & { version: number; total?: number },
): MerchantProposal {
  return {
    proposal_id: `p${partial.version}`,
    negotiation_session_id: "s1",
    version: partial.version,
    proposal_type: partial.proposal_type ?? (partial.version === 1 ? "INITIAL" : "COUNTER"),
    outcome: partial.outcome ?? (partial.version === 1 ? "INITIAL" : "COUNTEROFFER"),
    offer_id: partial.offer ? "o1" : partial.offer_id ?? "o1",
    offer:
      partial.offer === null
        ? null
        : (partial.offer ?? offer({ total: partial.total ?? 9240 })),
    reason_codes: partial.reason_codes ?? [],
    explanation: partial.explanation ?? [],
    next_allowed_actions: partial.next_allowed_actions ?? ["ACCEPT", "REJECT", "COUNTER"],
    compromise: null,
    expires_at: null,
    created_at: "2026-09-13T00:00:00Z",
    ...partial,
  };
}

function session(partial: Partial<NegotiationResponse>): NegotiationResponse {
  return {
    session_id: "s1",
    state: "MERCHANT_PROPOSAL_CREATED",
    proposal: null,
    previous_proposal: null,
    turns: [],
    proposals: [],
    commercial: null,
    timing: null,
    events: [],
    ...partial,
  };
}

describe("negotiation status", () => {
  it("maps merchant counter to an explicit status", () => {
    assert.equal(
      negotiationStatus("MERCHANT_COUNTER_CREATED").label,
      "Merchant counter created",
    );
  });

  it("treats ready-for-checkout as buyer accepted", () => {
    assert.equal(negotiationStatus("READY_FOR_CHECKOUT").label, "Buyer accepted");
  });

  it("labels no-safe-counter clearly", () => {
    assert.equal(negotiationStatus("NO_POLICY_SAFE_COUNTER").label, "No safe counter");
  });
});

describe("parsed buyer request", () => {
  it("shows structured max total without raw JSON", () => {
    const rows = parseBuyerRequest({
      action: "COUNTER",
      constraints: { max_total_price_cents: 5000 },
    });
    assert.deepEqual(rows, [
      { field: "price", label: "Maximum total", value: "≤ A$50.00" },
    ]);
  });

  it("shows a same-day delivery request", () => {
    const rows = parseBuyerRequest({
      constraints: { requested_delivery_days: 0 },
    });
    assert.equal(rows[0]?.value, "Same-day");
  });
});

describe("timeline cases", () => {
  it("CASE A — initial proposal has no counter history", () => {
    const initial = proposal({ version: 1, total: 9240, proposal_type: "INITIAL" });
    const events = buildNegotiationTimeline(
      session({
        proposal: initial,
        proposals: [initial],
        turns: [
          {
            turn_id: "t0",
            turn_number: 1,
            actor: "BUYER_AGENT",
            raw_message: "headphones under A$100",
            structured_action: "REQUEST",
            structured_payload: {},
            related_offer_id: null,
            created_at: "2026-09-13T00:00:00Z",
          },
          {
            turn_id: "t1",
            turn_number: 2,
            actor: "MERCHANT_AGENT",
            raw_message: null,
            structured_action: "PROPOSE",
            structured_payload: { proposal_id: "p1" },
            related_offer_id: "o1",
            related_proposal_id: "p1",
            created_at: "2026-09-13T00:00:01Z",
          },
        ],
      }),
    );
    assert.equal(events.length, 1);
    assert.equal(events[0]?.kind, "INITIAL_PROPOSAL");
    assert.equal(events[0]?.terms?.total, "A$92.40");
    assert.equal(currentRoundLabel({ proposal: initial } as NegotiationResponse), "Round 1 · Initial proposal");
  });

  it("CASE B — buyer price counter then merchant counter", () => {
    const initial = proposal({ version: 1, total: 9240 });
    const counter = proposal({
      version: 2,
      total: 7980,
      reason_codes: ["CLOSEST_POLICY_SAFE_COUNTER"],
      explanation: ["A$50.00 cannot be reached without violating merchant rules."],
    });
    const events = buildNegotiationTimeline(
      session({
        state: "MERCHANT_COUNTER_CREATED",
        proposal: counter,
        previous_proposal: initial,
        proposals: [initial, counter],
        turns: [
          {
            turn_id: "t1",
            turn_number: 2,
            actor: "MERCHANT_AGENT",
            raw_message: null,
            structured_action: "PROPOSE",
            structured_payload: {},
            related_offer_id: "o1",
            related_proposal_id: "p1",
            created_at: "2026-09-13T00:00:01Z",
          },
          {
            turn_id: "t2",
            turn_number: 3,
            actor: "BUYER_AGENT",
            raw_message: "Can you get this below A$50?",
            structured_action: "COUNTER",
            structured_payload: {
              action: "COUNTER",
              constraints: { max_total_price_cents: 5000 },
            },
            related_offer_id: null,
            created_at: "2026-09-13T00:00:02Z",
          },
          {
            turn_id: "t3",
            turn_number: 4,
            actor: "MERCHANT_AGENT",
            raw_message: null,
            structured_action: "COUNTER",
            structured_payload: { outcome: "COUNTEROFFER" },
            related_offer_id: "o1",
            related_proposal_id: "p2",
            created_at: "2026-09-13T00:00:03Z",
          },
        ],
      }),
    );
    assert.deepEqual(
      events.map((item) => item.kind),
      ["INITIAL_PROPOSAL", "BUYER_COUNTER", "COUNTEROFFER"],
    );
    assert.equal(events[1]?.message, "Can you get this below A$50?");
    assert.equal(events[1]?.parsed[0]?.value, "≤ A$50.00");
    assert.equal(events[2]?.terms?.total, "A$79.80");
  });

  it("CASE C — why-not uses backend reason and closest counter", () => {
    const counter = proposal({
      version: 2,
      total: 7980,
      outcome: "COUNTEROFFER",
      reason_codes: ["REQUESTED_PRICE_BELOW_MARGIN_FLOOR", "CLOSEST_POLICY_SAFE_COUNTER"],
      explanation: ["A$50.00 cannot be reached without violating the margin floor."],
    });
    const why = whyNotBuyerRequest(counter, {
      id: "t",
      round: 2,
      actor: "BUYER",
      kind: "BUYER_COUNTER",
      title: "Buyer agent counter",
      subtitle: "Counter",
      message: "Can you get this below A$50?",
      parsed: parseBuyerRequest({ constraints: { max_total_price_cents: 5000 } }),
      terms: null,
      explanation: [],
      reasonCodes: [],
      createdAt: null,
      inspectPayload: { constraints: { max_total_price_cents: 5000 } },
    });
    assert.equal(why?.title, "Why not A$50.00?");
    assert.equal(why?.requested, "A$50.00");
    assert.equal(why?.closest, "A$79.80");
    assert.equal(why?.gap, "+A$29.80");
    assert.ok(why?.reasons.some((line) => /minimum-margin/i.test(line)));
  });

  it("CASE G — decline is a no-safe-counter event, not a valid proposal", () => {
    const declined = proposal({
      version: 2,
      offer: null,
      offer_id: null,
      outcome: "DECLINE",
      reason_codes: ["NO_POLICY_SAFE_OFFER"],
    });
    const events = buildNegotiationTimeline(
      session({
        state: "NO_POLICY_SAFE_COUNTER",
        proposal: declined,
        proposals: [proposal({ version: 1, total: 7980 }), declined],
        turns: [
          {
            turn_id: "t3",
            turn_number: 4,
            actor: "MERCHANT_AGENT",
            raw_message: null,
            structured_action: "DECLINE",
            structured_payload: { outcome: "DECLINE" },
            related_offer_id: null,
            related_proposal_id: "p2",
            created_at: "2026-09-13T00:00:03Z",
          },
        ],
      }),
    );
    assert.equal(events.at(-1)?.kind, "NO_SAFE_COUNTER");
    assert.equal(events.at(-1)?.terms, null);
  });
});

describe("term delta", () => {
  it("compares previous, requested, and counter totals", () => {
    const rows = termDeltaRows(
      { total: "A$92.40", totalCents: 9240, delivery: "Same Day Delivery", warranty: "36-month warranty", bundle: "None", returns: "30-day returns", productName: "Orion", sku: "x", deliveryCode: "SAME_DAY", warrantyMonths: 36, utility: 0.62, contributionCents: 4810, contribution: "A$48.10" },
      parseBuyerRequest({ constraints: { max_total_price_cents: 5000 } }),
      { total: "A$79.80", totalCents: 7980, delivery: "Standard Delivery", warranty: "12-month warranty", bundle: "None", returns: "30-day returns", productName: "Orion", sku: "x", deliveryCode: "STANDARD", warrantyMonths: 12, utility: 0.48, contributionCents: 3543, contribution: "A$35.43" },
    );
    const total = rows.find((row) => row.term === "Total");
    assert.equal(total?.previous, "A$92.40");
    assert.equal(total?.requested, "≤ A$50.00");
    assert.equal(total?.counter, "A$79.80");
    assert.equal(total?.changed, true);
  });

  it("CASE E — delivery request appears in the requested column", () => {
    const rows = termDeltaRows(
      { total: "A$79.80", totalCents: 7980, delivery: "Standard Delivery", warranty: "12-month warranty", bundle: "None", returns: "30-day returns", productName: "Orion", sku: "x", deliveryCode: "STANDARD", warrantyMonths: 12, utility: 0.48, contributionCents: 3543, contribution: "A$35.43" },
      parseBuyerRequest({ constraints: { requested_delivery_days: 0 } }),
      { total: "A$89.80", totalCents: 8980, delivery: "Same Day Delivery", warranty: "12-month warranty", bundle: "None", returns: "30-day returns", productName: "Orion", sku: "x", deliveryCode: "SAME_DAY", warrantyMonths: 12, utility: 0.51, contributionCents: 3000, contribution: "A$30.00" },
    );
    const delivery = rows.find((row) => row.term === "Delivery");
    assert.equal(delivery?.requested, "Same-day");
    assert.equal(delivery?.counter, "Same Day Delivery");
  });
});

describe("commercial changes", () => {
  it("does not invent a previous utility when missing", () => {
    assert.deepEqual(
      commercialChanges(
        { total: "A$92.40", totalCents: 9240, delivery: "Same-day", warranty: "36-month warranty", bundle: "None", returns: "30-day", productName: "x", sku: "x", deliveryCode: "SAME_DAY", warrantyMonths: 36, utility: null, contributionCents: null, contribution: null },
        { total: "A$79.80", totalCents: 7980, delivery: "Standard", warranty: "12-month warranty", bundle: "None", returns: "30-day", productName: "x", sku: "x", deliveryCode: "STANDARD", warrantyMonths: 12, utility: 0.48, contributionCents: 3543, contribution: "A$35.43" },
      ),
      [
        { label: "Price", from: "A$92.40", to: "A$79.80", delta: "-A$12.60" },
        { label: "Delivery", from: "Same-day", to: "Standard" },
        { label: "Warranty", from: "36-month warranty", to: "12-month warranty" },
      ],
    );
  });
});

describe("constraint evolution", () => {
  it("CASE D — buyer budget relaxation is explicit", () => {
    const changes = constraintChanges(
      {
        hard_constraints: [
          {
            id: "c1",
            field: "price",
            operator: "LTE",
            value: 10000,
            unit: "AUD_CENTS",
            source_phrase: "under A$100",
            normalized_value: 10000,
            importance: "MANDATORY",
            applies_to: "CUSTOMER_TOTAL",
          },
        ],
      } as never,
      {
        hard_constraints: [
          {
            id: "c1",
            field: "price",
            operator: "LTE",
            value: 11000,
            unit: "AUD_CENTS",
            source_phrase: "A$110",
            normalized_value: 11000,
            importance: "MANDATORY",
            applies_to: "CUSTOMER_TOTAL",
          },
        ],
      } as never,
    );
    assert.equal(changes[0]?.kind, "RELAXED");
    assert.match(changes[0]?.from ?? "", /A\$100/);
    assert.match(changes[0]?.to ?? "", /A\$110/);
  });

  it("keeps active hard constraints readable", () => {
    const labels = activeConstraintLabels({
      category: "headphones",
      hard_constraints: [
        {
          id: "c1",
          field: "price",
          operator: "LT",
          value: 10000,
          unit: "AUD_CENTS",
          source_phrase: "under A$100",
          normalized_value: 10000,
          importance: "MANDATORY",
        },
      ],
    } as never);
    assert.ok(labels.some((item) => /headphones/i.test(item)));
    assert.ok(labels.some((item) => /A\$100/.test(item)));
  });
});

describe("buyer actions", () => {
  it("CASE F — max turns is terminal", () => {
    const allowed = buyerMayAct(
      proposal({ version: 3, total: 7980, next_allowed_actions: ["REJECT"] }),
      "NEGOTIATION_LIMIT_REACHED",
    );
    assert.equal(allowed.counter, false);
    assert.equal(allowed.accept, false);
  });
});

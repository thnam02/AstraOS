import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { ArenaRunResponse, ArenaStrategyResponse } from "../types";
import {
  bundleLabel,
  comparisonRows,
  deliveryLabel,
  headline,
  isSelectable,
  nearTie,
  policyReasons,
  primaryDecisionSentence,
  strategyTitle,
  strategyValidity,
  strongestBaseline,
  tradeOffSummary,
  warrantyLabel,
  weightRows,
  winnerReasons,
} from "./arenaDisplay";

function offer(
  name: string,
  overrides: Partial<ArenaStrategyResponse> = {},
): ArenaStrategyResponse {
  return {
    strategy_name: name,
    product_id: "p",
    variant_id: "v",
    offer_id: `${name}-offer`,
    sku: `${name}-sku`,
    product_name: name,
    total_customer_price_cents: 20000,
    currency: "AUD",
    delivery: "STANDARD",
    delivery_days: 2,
    warranty: "STANDARD_12",
    warranty_months: 12,
    bundle: null,
    returns: "STANDARD_30",
    buyer_utility: 0.5,
    merchant_contribution_cents: 4000,
    intervention_cost_cents: 0,
    hard_constraints_satisfied: true,
    policy_safe: true,
    transaction_possible: true,
    failure_reason: null,
    utility_trace: null,
    used_pareto: name === "ASTRAOS",
    used_max_discount: name === "ALWAYS_DISCOUNT",
    is_cheapest_in_space: name === "CHEAPEST_ELIGIBLE",
    ...overrides,
  };
}

const hero: ArenaRunResponse = {
  arena_run_id: "run-1",
  mission_id: "mission-1",
  buyer_profile: "URGENT_TRAVELLER",
  strategies: [
    {
      name: "DEFAULT",
      response: offer("DEFAULT", {
        product_name: "Sonic Cabin 32",
        sku: "SON-T32-SLV",
        total_customer_price_cents: 19488,
        buyer_utility: 0.56,
        merchant_contribution_cents: 4496,
        policy_safe: false,
        hard_constraints_satisfied: false,
        failure_reason: "INTENT_DELIVERY_INCOMPATIBLE",
      }),
    },
    {
      name: "ALWAYS_DISCOUNT",
      response: offer("ALWAYS_DISCOUNT", {
        product_name: "Sonic Cabin 32",
        sku: "SON-T32-SLV",
        total_customer_price_cents: 17539,
        buyer_utility: 0.57,
        merchant_contribution_cents: 2547,
        intervention_cost_cents: 1949,
        policy_safe: false,
        hard_constraints_satisfied: false,
        failure_reason: "MARGIN_BELOW_FLOOR,INTENT_DELIVERY_INCOMPATIBLE",
      }),
    },
    {
      name: "CHEAPEST_ELIGIBLE",
      response: offer("CHEAPEST_ELIGIBLE", {
        product_name: "Sonic Sport 38",
        sku: "SON-S38-BLK",
        total_customer_price_cents: 12953,
        delivery: "SAME_DAY",
        delivery_days: 0,
        buyer_utility: 0.77,
        merchant_contribution_cents: 4377,
        intervention_cost_cents: 2128,
      }),
    },
    {
      name: "ASTRAOS",
      response: offer("ASTRAOS", {
        product_name: "Atlas Cabin 72",
        sku: "ATL-T72-BLK",
        total_customer_price_cents: 23808,
        delivery: "SAME_DAY",
        delivery_days: 0,
        warranty: "EXTENDED_36",
        warranty_months: 36,
        bundle: "HARD_CASE",
        buyer_utility: 0.87,
        merchant_contribution_cents: 10264,
        intervention_cost_cents: 3600,
      }),
    },
  ],
  buyer_selection: {
    selected_strategy: "ASTRAOS",
    selected_offer_id: "ASTRAOS-offer",
    simulated_utility: 0.87,
    no_purchase: false,
    reason: "HIGHEST_SIMULATED_UTILITY",
    tie_break: null,
  },
  explanation: {
    profile_id: "URGENT_TRAVELLER",
    weights: {
      product: 0.3,
      price: 0.1,
      delivery: 0.3,
      warranty: 0.1,
      bundle: 0.1,
      returns: 0.1,
    },
    reasons: [
      "Faster delivery improved simulated delivery fit versus the default catalogue card.",
    ],
  },
  disclaimer: "Synthetic evaluation using transparent simulated buyer utility.",
  created_at: "2026-09-12T00:00:00Z",
};

describe("commercial labels", () => {
  it("maps delivery enums", () => {
    assert.equal(deliveryLabel("STANDARD", 2), "Standard delivery");
    assert.equal(deliveryLabel("SAME_DAY", 0), "Same-day delivery");
  });

  it("maps warranty enums", () => {
    assert.equal(warrantyLabel("STANDARD_12", 12), "12-month warranty");
    assert.equal(warrantyLabel("EXTENDED_36", 36), "36-month warranty");
  });

  it("maps bundle enums", () => {
    assert.equal(bundleLabel(null), "No bundle");
    assert.equal(bundleLabel("HARD_CASE"), "Hard case");
  });
});

describe("policy and validity", () => {
  it("marks a valid strategy card selectable", () => {
    const astra = hero.strategies[3].response;
    assert.equal(isSelectable(astra), true);
    assert.equal(strategyValidity(astra), "POLICY_SAFE");
  });

  it("treats policy-blocked responses as no safe offer", () => {
    const blocked = hero.strategies[1].response;
    assert.equal(isSelectable(blocked), false);
    assert.equal(strategyValidity(blocked), "NO_SAFE_OFFER");
    assert.deepEqual(policyReasons(blocked.failure_reason), [
      "Minimum margin policy",
      "Same-day delivery is mandatory",
    ]);
  });

  it("does not treat blocked offers as the strongest baseline", () => {
    const baseline = strongestBaseline(hero);
    assert.equal(baseline?.strategy_name, "CHEAPEST_ELIGIBLE");
  });
});

describe("winner and comparison", () => {
  it("builds a selected-strategy headline", () => {
    const result = headline(hero);
    assert.match(result.title, /AstraOS won/i);
    assert.match(result.body, /delivery/i);
  });

  it("explains why AstraOS won from real deltas", () => {
    const reasons = winnerReasons(hero);
    assert.ok(reasons.some((line) => /buyer fit/i.test(line)));
    assert.ok(reasons.some((line) => /same-day/i.test(line)));
    assert.ok(reasons.some((line) => /policy-safe/i.test(line)));
  });

  it("compares AstraOS against the strongest valid baseline", () => {
    const baseline = strongestBaseline(hero);
    const winner = hero.strategies[3].response;
    assert.ok(baseline);
    const rows = comparisonRows(baseline, winner);
    assert.equal(rows[0].left, "0.77");
    assert.equal(rows[0].right, "0.87");
    const summary = tradeOffSummary(winner, baseline);
    assert.equal(summary.fitDelta, "+0.10");
    assert.match(summary.contributionDelta, /\+A\$58\.87|\+\$58\.87/);
  });

  it("renders buyer priority weights as compact bars", () => {
    const rows = weightRows(hero.explanation.weights);
    assert.equal(rows.find((row) => row.key === "delivery")?.pct, 30);
    assert.equal(rows.find((row) => row.key === "price")?.pct, 10);
  });

  it("handles no-purchase outcomes", () => {
    const none: ArenaRunResponse = {
      ...hero,
      buyer_selection: {
        selected_strategy: null,
        selected_offer_id: null,
        simulated_utility: 0.3,
        no_purchase: true,
        reason: "OUTSIDE_OPTION",
        tie_break: null,
      },
      explanation: {
        reasons: [
          "No strategy cleared the outside-option utility threshold, so the simulated buyer made no purchase.",
        ],
      },
    };
    assert.equal(headline(none).title, "No purchase");
    assert.match(primaryDecisionSentence(none), /acceptance threshold|no purchase/i);
  });

  it("detects near-equivalent utilities for the inspector", () => {
    const tied: ArenaRunResponse = {
      ...hero,
      strategies: [
        {
          name: "CHEAPEST_ELIGIBLE",
          response: offer("CHEAPEST_ELIGIBLE", { buyer_utility: 0.87 }),
        },
        {
          name: "ASTRAOS",
          response: offer("ASTRAOS", { buyer_utility: 0.871 }),
        },
      ],
    };
    assert.equal(nearTie(tied), true);
  });
});

describe("strategy titles", () => {
  it("uses human-readable names", () => {
    assert.equal(strategyTitle("DEFAULT"), "Default Merchant");
    assert.equal(strategyTitle("ALWAYS_DISCOUNT"), "Always Discount");
    assert.equal(strategyTitle("CHEAPEST_ELIGIBLE"), "Cheapest Eligible");
    assert.equal(strategyTitle("ASTRAOS"), "AstraOS");
  });
});

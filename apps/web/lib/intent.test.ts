import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  buyerRequestHighlights,
  constraintLabel,
  defaultBuyerCounter,
  formatConstraint,
  intentNarrative,
  intentPriceCeilingCents,
} from "./intent";
import type { HardConstraint, ShoppingIntent } from "@/types";

describe("buyer request highlights", () => {
  it("surfaces decision-relevant constraints without inventing values", () => {
    const intent = {
      category: "headphones",
      hard_constraints: [
        {
          id: "1",
          field: "anc",
          operator: "EQ",
          value: true,
          unit: null,
          source_phrase: "noise-cancelling",
          normalized_value: true,
          importance: "MANDATORY",
        },
        {
          id: "2",
          field: "price",
          operator: "LTE",
          value: 35000,
          unit: "AUD_CENTS",
          source_phrase: "under A$350",
          normalized_value: 35000,
          importance: "MANDATORY",
        },
      ],
      soft_preferences: [
        {
          id: "3",
          field: "comfort",
          direction: "MAXIMIZE",
          importance: 0.8,
          source_phrase: "comfort",
        },
        {
          id: "4",
          field: "reliability",
          direction: "MAXIMIZE",
          importance: 0.7,
          source_phrase: "reliability",
        },
      ],
    } as ShoppingIntent;

    const chips = buyerRequestHighlights(intent);
    assert.ok(chips.includes("Headphones"));
    assert.ok(chips.includes("ANC"));
    assert.ok(chips.some((item) => item.includes("A$350")));
    assert.ok(chips.includes("Comfort + Reliability prioritised"));
  });

  it("formats a same-day delivery constraint as today", () => {
    assert.equal(formatConstraint("EQ", 0, "DAYS"), "today");
  });

  it("writes a human sentence from structured intent", () => {
    const text = intentNarrative({
      category: "headphones",
      hard_constraints: [
        {
          id: "1",
          field: "anc",
          operator: "EQ",
          value: true,
          unit: null,
          source_phrase: "noise-cancelling",
          normalized_value: true,
          importance: "MANDATORY",
        },
      ],
      soft_preferences: [
        {
          id: "3",
          field: "comfort",
          direction: "MAXIMIZE",
          importance: 0.8,
          source_phrase: "comfort",
        },
      ],
      tradeoffs: [
        {
          preferred_dimension: "comfort",
          over_dimension: "price",
          source_phrase: "comfort over price",
        },
      ],
    } as ShoppingIntent);
    assert.match(text, /The buyer needs headphones with ANC/);
    assert.match(text, /Comfort is prioritised/);
    assert.match(text, /Comfort matters more than minimising price/);
  });
});

describe("price constraint labels", () => {
  it("labels default price as total spend", () => {
    const label = constraintLabel({
      field: "price",
      operator: "LT",
      value: 10000,
      normalized_value: 10000,
      unit: "AUD_CENTS",
    } as HardConstraint);
    assert.match(label, /Total/);
    assert.match(label, /A\$100/);
  });
});

describe("computed buyer price prompts", () => {
  it("reads the tightest price ceiling from intent", () => {
    const intent = {
      hard_constraints: [
        {
          field: "price",
          operator: "LTE",
          value: 35000,
          normalized_value: 35000,
        },
      ],
    };
    assert.equal(intentPriceCeilingCents(intent), 35000);
    assert.equal(defaultBuyerCounter(intent, 30185), "Can you get this below A$350?");
  });

  it("falls back to the current offer when intent has no price", () => {
    assert.equal(
      defaultBuyerCounter({ hard_constraints: [] }, 30185),
      "Can you get this below A$301.85?",
    );
    assert.equal(
      defaultBuyerCounter(null, null),
      "Can you adjust the commercial terms?",
    );
  });
});

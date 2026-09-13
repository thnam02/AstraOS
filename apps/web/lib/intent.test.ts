import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { buyerRequestHighlights, formatConstraint } from "./intent";
import type { ShoppingIntent } from "@/types";

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
});

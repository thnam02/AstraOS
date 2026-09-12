import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  conciseOfferReasons,
  constructStory,
  expansionSteps,
  humanizeCheck,
  LEARN_STATUS,
  LEARN_STORY,
  matchScoreDisplay,
  negotiationConstraint,
  offerVsProductCopy,
  productsDiffer,
} from "./decisionNarrative";

describe("product vs offer", () => {
  it("explains when the selected offer is a different product", () => {
    const differ = productsDiffer(
      { sku: "SON-T32-SLV", product_name: "Sonic Cabin 32" } as never,
      { sku: "AUR-T06-BLK", product_name: "Aurora Commute 06" } as never,
    );
    assert.equal(differ, true);
    assert.match(offerVsProductCopy(true), /best commercial response/);
  });

  it("explains when the same product remains strongest", () => {
    const differ = productsDiffer(
      { sku: "SON-T32-SLV", product_name: "Sonic Cabin 32" } as never,
      { sku: "SON-T32-SLV", product_name: "Sonic Cabin 32" } as never,
    );
    assert.equal(differ, false);
    assert.match(offerVsProductCopy(false), /remained strongest/);
  });
});

describe("product-to-offer bridge", () => {
  it("summarises construction dimensions", () => {
    const story = constructStory({
      input: { matched_products: 8 },
      dimensions: {
        price_options: 5,
        delivery_options: 3,
        warranty_options: 3,
        bundle_options: 4,
        return_options: 2,
      },
      summary: {
        generated_candidates: 2416,
        feasible_candidates: 1102,
        estimated_candidates: 2416,
      },
    } as never);
    assert.equal(story.products, 8);
    assert.equal(story.generated, 2416);
    const steps = expansionSteps(
      {
        input: { matched_products: 8 },
        dimensions: {
          price_options: 5,
          delivery_options: 3,
          warranty_options: 3,
          bundle_options: 4,
          return_options: 2,
        },
        summary: {
          generated_candidates: 2416,
          feasible_candidates: 1584,
          estimated_candidates: 2416,
        },
      } as never,
      { summary: { policy_safe: 1102, pareto_efficient: 9 }, recommended_offer: { sku: "x" } } as never,
    );
    assert.equal(steps[0]?.value, "8");
    assert.equal(steps.at(-1)?.label, "Selected response");
  });

  it("parses a buyer price constraint", () => {
    assert.equal(
      negotiationConstraint({ constraints: { max_total_price_cents: 31500 } }),
      "TOTAL PRICE ≤ A$315",
    );
  });
});

describe("learn story", () => {
  it("leads with observe, learn, improve", () => {
    assert.deepEqual(
      LEARN_STORY.map((item) => item.label),
      ["Intent", "Offer", "Outcome", "Learning record", "Response model", "Future support"],
    );
    assert.equal(LEARN_STATUS[2]?.state, "PRIMARY");
    assert.equal(LEARN_STATUS[3]?.state, "EXPERIMENTAL");
  });
});

describe("score terminology", () => {
  it("shows extra decimal only when rounded scores collide", () => {
    const tied = matchScoreDisplay(0.824, [0.824, 0.821]);
    assert.equal(tied.value, "82.4");
    const unique = matchScoreDisplay(0.82, [0.82, 0.78]);
    assert.equal(unique.value, "82");
    assert.equal(unique.suffix, "/ 100");
  });

  it("humanizes transaction failure codes", () => {
    assert.equal(humanizeCheck("PROPOSAL_EXPIRED"), "Proposal expired");
    assert.equal(humanizeCheck("OUT_OF_STOCK"), "Out of stock");
  });

  it("shortens offer rationale and drops probability disclaimers", () => {
    const reasons = conciseOfferReasons([
      "Satisfies all mandatory requirements and current merchant policy guardrails.",
      "Same-day delivery aligns with the urgency / travel context.",
      "Simulated buyer utility is a transparent cold-start score, not a win or purchase probability.",
      "Lies on the Pareto-efficient frontier of simulated buyer utility versus merchant contribution.",
    ]);
    assert.deepEqual(reasons, [
      "All mandatory requirements satisfied",
      "Same-day delivery addresses urgency",
      "Pareto efficient",
    ]);
  });
});

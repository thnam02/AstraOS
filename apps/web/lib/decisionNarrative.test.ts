import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  baselineTermsForProduct,
  commercialDeltas,
  completeOfferMandatorySatisfied,
  conciseOfferReasons,
  noCompliantOfferCopy,
  selectableCompleteOffer,
  constructStory,
  expansionSteps,
  humanizeCheck,
  LEARN_STATUS,
  LEARN_STORY,
  matchScoreDisplay,
  negotiationConstraint,
  offerVsProductCopy,
  productsDiffer,
  sameProductOfferSummary,
  termsFromScored,
  winnerChangeSummary,
} from "./decisionNarrative";

describe("product vs offer", () => {
  it("explains when the selected offer is a different product", () => {
    const differ = productsDiffer(
      { sku: "SON-T32-SLV", product_name: "Sonic Cabin 32" } as never,
      { sku: "AUR-T06-BLK", product_name: "Aurora Commute 06" } as never,
    );
    assert.equal(differ, true);
    assert.match(offerVsProductCopy(true), /complete merchant response/);
  });

  it("explains when the same product remains strongest", () => {
    const differ = productsDiffer(
      { sku: "SON-T32-SLV", product_name: "Sonic Cabin 32" } as never,
      { sku: "SON-T32-SLV", product_name: "Sonic Cabin 32" } as never,
    );
    assert.equal(differ, false);
    assert.match(offerVsProductCopy(false), /best complete offer/);
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
    const constructOnly = expansionSteps(
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
    );
    assert.deepEqual(
      constructOnly.map((item) => item.label),
      ["Matched products", "Candidate offers", "Feasible"],
    );
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

describe("commercial comparison", () => {
  const atlas = {
    sku: "ATL-C72",
    product_name: "Atlas Cabin 72",
  } as never;
  const aurora = {
    product_name: "Aurora Commute 06",
    sku: "AUR-T06",
    pricing: { total_price_cents: 30185 },
    delivery: { code: "SAME_DAY", name: "Same Day Delivery", days: 0 },
    warranty: { code: "EXTENDED_36", name: "36-month", months: 36 },
    bundle: { code: "HARD_CASE", name: "Hard travel case" },
    returns: { code: "FLEX_60", window_days: 60 },
    product_fit: 0.84,
    buyer_utility: 0.9,
  } as never;
  const atlasBaseline = {
    product_name: "Atlas Cabin 72",
    sku: "ATL-C72",
    is_baseline: true,
    pricing: { total_price_cents: 24800 },
    delivery: { code: "STANDARD", name: "Standard Delivery", days: 3 },
    warranty: { code: "STANDARD_12", name: "12-month", months: 12 },
    bundle: null,
    returns: { code: "STANDARD_30", window_days: 30 },
  } as never;

  it("prefers construction product_baselines over sampled scored offers", () => {
    const terms = baselineTermsForProduct(
      atlas,
      {
        recommended_offer: aurora,
        pareto_offers: [],
        alternative_pareto_offers: [],
        plot_points: [],
      } as never,
      {
        product_baselines: [
          {
            product: { sku: "ATL-C72", name: "Atlas Cabin 72" },
            pricing: { total_price_cents: 24800 },
            delivery: { code: "STANDARD", name: "Standard Delivery", days: 3 },
            warranty: { code: "STANDARD_12", name: "12-month", months: 12 },
            bundle: null,
            returns: { code: "STANDARD_30", window_days: 30 },
          },
        ],
      } as never,
    );
    assert.equal(terms?.delivery_code, "STANDARD");
    assert.equal(terms?.warranty_code, "STANDARD_12");
    assert.equal(terms?.bundle_code, null);
  });

  it("finds a baseline from scored offers without inventing terms", () => {
    const terms = baselineTermsForProduct(atlas, {
      recommended_offer: aurora,
      pareto_offers: [atlasBaseline],
      alternative_pareto_offers: [],
      plot_points: [],
    } as never, null);
    assert.equal(terms?.delivery_code, "STANDARD");
    assert.equal(terms?.warranty_code, "STANDARD_12");
  });

  it("lists only fields that actually differ", () => {
    const rows = commercialDeltas(
      baselineTermsForProduct(atlas, {
        recommended_offer: aurora,
        pareto_offers: [atlasBaseline],
        alternative_pareto_offers: [],
        plot_points: [],
      } as never, null),
      termsFromScored(aurora),
    );
    assert.ok(rows.some((item) => item.field === "Delivery"));
    assert.ok(rows.some((item) => item.field === "Warranty"));
    assert.equal(rows.some((item) => item.from.includes("undefined")), false);
  });

  it("summarises a product change from structured deltas", () => {
    const text = winnerChangeSummary("Atlas Cabin 72", "Aurora Commute 06", [
      { field: "Delivery", from: "Standard delivery", to: "Same-day delivery" },
      { field: "Warranty", from: "12-month warranty", to: "36-month warranty" },
    ]);
    assert.match(text, /Atlas Cabin 72 is the stronger standalone product match/);
    assert.match(text, /same-day delivery and 36-month warranty/);
  });

  it("uses the same-product story when the winner does not change", () => {
    const text = sameProductOfferSummary("Atlas Cabin 72", [
      { field: "Delivery", from: "Standard delivery", to: "Same-day delivery" },
    ]);
    assert.match(text, /remained the strongest product/);
    assert.match(text, /configured delivery/);
  });

  it("returns no rows when a baseline is missing", () => {
    assert.deepEqual(commercialDeltas(null, termsFromScored(aurora)), []);
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

  it("does not treat an over-budget recommended offer as selectable", () => {
    const offer = {
      policy_safe: true,
      policy_rejection_codes: [],
      selectable: true,
      is_recommended: true,
      is_pareto_efficient: true,
      pricing: { product_price_cents: 9200, total_price_cents: 12767, currency: "AUD" },
    } as never;
    assert.equal(
      selectableCompleteOffer(offer, { failure: null } as never, {
        hard_constraints: [
          {
            field: "price",
            operator: "LT",
            value: 10000,
            normalized_value: 10000,
          },
        ],
      }),
      null,
    );
  });

  it("trusts backend complete-offer buyer validation when present", () => {
    const offer = {
      policy_safe: true,
      policy_rejection_codes: [],
      all_mandatory_buyer_constraints_satisfied: false,
      pricing: { product_price_cents: 9200, total_price_cents: 12767, currency: "AUD" },
    };
    assert.equal(completeOfferMandatorySatisfied(offer, null), false);
  });

  it("describes a no-compliant-offer near-miss without calling it selected", () => {
    const copy = noCompliantOfferCopy({
      recommended_offer: null,
      failure: {
        code: "NO_COMPLIANT_OFFER",
        message: "No complete offer satisfies your A$100.00 maximum.",
        requested_max_price_cents: 10000,
        lowest_constructed_price_cents: 10420,
        lowest_policy_safe_price_cents: 10420,
        rejection_distribution: {},
      },
      near_miss: {
        offer_id: "x",
        product_name: "Orion Mini 106",
        sku: "ORI-106",
        total_customer_price_cents: 10420,
        gap_cents: 420,
        requested_max_price_cents: 10000,
        label: "NEAR_MISS",
        relaxation: "REQUIRES_BUYER_RELAXATION",
        blocked_codes: ["BUYER_MAX_TOTAL_EXCEEDED"],
        reason: "Requires buyer relaxation",
        is_pareto_efficient: false,
        is_recommended: false,
        selectable: false,
      },
    } as never);
    assert.match(copy.title, /mandatory total budget/);
    assert.equal(copy.budget, "A$100.00");
    assert.equal(copy.closest, "A$104.20");
    assert.equal(copy.gap, "+A$4.20");
  });

  it("does not treat policy_safe alone as a complete-offer budget pass", () => {
    const offer = {
      policy_safe: true,
      policy_rejection_codes: [],
      pricing: { product_price_cents: 9200, total_price_cents: 12700, currency: "AUD" },
    };
    assert.equal(
      completeOfferMandatorySatisfied(offer, {
        hard_constraints: [
          {
            field: "price",
            operator: "LTE",
            normalized_value: 10000,
            applies_to: "CUSTOMER_TOTAL",
          },
        ],
      }),
      false,
    );
    assert.equal(
      completeOfferMandatorySatisfied(offer, {
        hard_constraints: [
          {
            field: "price",
            operator: "LTE",
            normalized_value: 10000,
            applies_to: "PRODUCT_BASE",
          },
        ],
      }),
      true,
    );
  });
});

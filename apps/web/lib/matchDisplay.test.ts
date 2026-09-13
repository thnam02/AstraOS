import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  displayedCoverage,
  isSupportedFact,
  primaryReasons,
  proofItems,
  sourceBadge,
  tradeOffLine,
} from "./matchDisplay";
import type { RankedProductMatch } from "../types";

describe("source badges", () => {
  it("uses compact source labels", () => {
    assert.equal(sourceBadge("MERCHANT_PRODUCT_FEED").code, "PRODUCT FEED");
    assert.equal(sourceBadge("MERCHANT_INVENTORY").code, "INVENTORY");
    assert.equal(sourceBadge("PRICING_FEED").code, "PRICING");
    assert.equal(sourceBadge("FULFILMENT_CONFIGURATION").code, "FULFILMENT");
    assert.equal(sourceBadge("WARRANTY_POLICY").code, "WARRANTY");
    assert.equal(sourceBadge("BUNDLE_CONFIGURATION").code, "BUNDLE");
    assert.equal(sourceBadge("RETURN_POLICY").code, "RETURNS");
    assert.equal(sourceBadge("EXAMPLE_MERCHANT_IMPORT").code, "EXAMPLE IMPORT");
    assert.equal(sourceBadge("SYNTHETIC_DEMO_FIXTURE").code, "SYNTHETIC");
  });
});

describe("displayed facts", () => {
  it("omits unsupported and conflicted claims", () => {
    assert.equal(
      isSupportedFact({
        attribute: "anc",
        evidence_id: null,
        derived: false,
      }),
      false,
    );
    assert.equal(
      isSupportedFact({
        attribute: "anc",
        evidence_id: "e1",
        verification_status: "CONFLICTED",
      }),
      false,
    );
    assert.equal(
      isSupportedFact({
        attribute: "units_available",
        evidence_id: "e1",
        freshness: "STALE",
      }),
      false,
    );
    assert.equal(
      isSupportedFact({
        attribute: "battery_hours",
        evidence_id: "e1",
        verification_status: "VERIFIED",
      }),
      true,
    );
  });

  it("uses proof coverage rather than ranking coverage", () => {
    const match = {
      evidence_coverage: 1,
      proof_coverage: { match_rationale_proof_rate: 0.5 },
      reasons: [
        {
          need: "battery",
          kind: "context",
          facts: [
            {
              attribute: "battery_hours",
              value: 79,
              display: "79h battery",
              evidence_id: "e1",
              source_name: "Harbor product feed",
              source_type: "MERCHANT_PRODUCT_FEED",
            },
            {
              attribute: "comfort_score",
              value: 0.8,
              display: "Comfort score 0.8",
              evidence_id: null,
              source_name: null,
            },
          ],
        },
      ],
      evidence: [],
      unsupported_needs: [],
    } as unknown as RankedProductMatch;
    assert.equal(displayedCoverage(match), 0.5);
    assert.equal(primaryReasons(match).length, 1);
  });

  it("falls back to reason facts when proof is empty", () => {
    const items = proofItems({
      proof: [],
      reasons: [
        {
          need: "anc",
          kind: "requirement",
          facts: [
            {
              attribute: "anc",
              value: true,
              display: "ANC",
              evidence_id: null,
              source_name: "Harbor product feed",
              source_type: "MERCHANT_PRODUCT_FEED",
            },
          ],
        },
      ],
      evidence: [],
      unsupported_needs: [],
    } as unknown as RankedProductMatch);
    assert.equal(items.length, 1);
    assert.equal(items[0]?.claim_key, "anc");
  });

  it("compares context fit to the leading product name", () => {
    const leader = {
      variant_id: "a",
      product_name: "Atlas Cabin 72",
      preference_fit: 0.8,
      context_fit: 0.9,
      unsupported_needs: [],
    } as unknown as RankedProductMatch;
    const peer = {
      variant_id: "b",
      product_name: "Aurora Commute 06",
      preference_fit: 0.8,
      context_fit: 0.7,
      unsupported_needs: [],
    } as unknown as RankedProductMatch;
    assert.equal(
      tradeOffLine(peer, [leader, peer]),
      "Weaker context fit than Atlas Cabin 72.",
    );
  });
});

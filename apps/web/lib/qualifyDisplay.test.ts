import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  exclusionSummary,
  humanizeExclusionReason,
  qualificationReasonCopy,
  rowSpecificReasons,
  sharedExclusionReason,
} from "./qualifyDisplay";

const unknown = "intent UNKNOWN: NO_MANDATORY_CONSTRAINTS";

describe("qualification display", () => {
  it("deduplicates a shared unknown reason", () => {
    const items = [
      { exclusion_reasons: [unknown] },
      { exclusion_reasons: [unknown] },
    ] as never;
    assert.equal(sharedExclusionReason(items), unknown);
    assert.equal(
      qualificationReasonCopy(unknown),
      "No mandatory constraints were provided for this request.",
    );
  });

  it("hides the group reason on individual rows", () => {
    const item = {
      exclusion_reasons: [unknown, "price VIOLATED: OVER_BUDGET"],
    } as never;
    assert.deepEqual(rowSpecificReasons(item, unknown), [
      "price VIOLATED: OVER_BUDGET",
    ]);
  });

  it("humanizes price violations and groups observed values", () => {
    assert.equal(
      humanizeExclusionReason(
        "price VIOLATED: expected LT 20000, observed 22148",
      ),
      "Price over A$200.00",
    );
    assert.equal(
      humanizeExclusionReason(
        "price VIOLATED: expected LT 20000, observed 22148",
        { includeObserved: true },
      ),
      "A$221.48 is over the A$200.00 limit",
    );
    const rows = exclusionSummary({
      rejected_products: [
        {
          exclusion_reasons: [
            "price VIOLATED: expected LT 20000, observed 22148",
          ],
        },
        {
          exclusion_reasons: [
            "price VIOLATED: expected LT 20000, observed 27370",
          ],
        },
      ],
    } as never);
    assert.equal(rows.length, 1);
    assert.equal(rows[0]?.label, "Price over A$200.00");
    assert.equal(rows[0]?.count, 2);
  });

  it("humanizes delivery and unknown codes", () => {
    assert.equal(
      humanizeExclusionReason(
        "delivery_days VIOLATED: expected LTE 0, observed 1",
      ),
      "Delivery slower than same-day",
    );
    assert.equal(
      humanizeExclusionReason("anc UNKNOWN: MISSING_ATTRIBUTE"),
      "ANC not confirmed in catalogue data",
    );
  });

  it("returns no shared reason when rows differ", () => {
    const items = [
      { exclusion_reasons: [unknown] },
      { exclusion_reasons: ["delivery UNKNOWN: MISSING_DELIVERY_DATA"] },
    ] as never;
    assert.equal(sharedExclusionReason(items), null);
  });
});

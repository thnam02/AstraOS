import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  formatAudCents,
  formatCount,
  formatGrams,
  formatHours,
  formatMonths,
  formatScore100,
  formatUtility,
} from "./format";

describe("format helpers", () => {
  it("formats money, scores, and units", () => {
    assert.equal(formatAudCents(19488), "A$194.88");
    assert.equal(formatScore100(0.824), "82 / 100");
    assert.equal(formatUtility(0.88), "0.88 utility");
    assert.equal(formatHours(79), "79h");
    assert.equal(formatGrams(230), "230g");
    assert.equal(formatMonths(36), "36 months");
    assert.equal(formatCount(2416), "2,416");
  });
});

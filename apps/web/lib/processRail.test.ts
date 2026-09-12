import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { processRailState } from "../components/live/ProcessRail";

const ready = {
  hasMatch: true,
  hasOffers: true,
  hasOpt: true,
  hasNego: true,
  hasTxn: false,
  txnFailed: false,
  txnComplete: false,
};

describe("process rail", () => {
  it("marks the current stage active and prior stages complete", () => {
    assert.equal(processRailState("optimise", ready, "optimise"), "active");
    assert.equal(processRailState("match", ready, "optimise"), "complete");
    assert.equal(processRailState("transact", ready, "optimise"), "future");
  });

  it("marks a failed transaction", () => {
    assert.equal(
      processRailState(
        "transact",
        { ...ready, hasTxn: true, txnFailed: true },
        "transact",
      ),
      "failed",
    );
  });
});

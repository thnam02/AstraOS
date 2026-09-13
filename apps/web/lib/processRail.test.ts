import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { processRailState } from "../components/live/ProcessRail";
import { stageReachable } from "./liveStages";

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

  it("does not invent progress when no match exists", () => {
    const idle = {
      hasMatch: false,
      hasOffers: false,
      hasOpt: false,
      hasNego: false,
      hasTxn: false,
      txnFailed: false,
      txnComplete: false,
    };
    assert.equal(processRailState("qualify", idle, "understand"), "future");
    assert.equal(processRailState("match", idle, "understand"), "future");
  });

  it("lets merchants open transact after a proposal exists", () => {
    assert.equal(processRailState("transact", ready, "match"), "future");
    assert.equal(stageReachable("transact", ready, "match"), true);
    assert.equal(stageReachable("learn", ready, "match"), true);
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

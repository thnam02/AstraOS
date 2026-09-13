import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  AGENT_API_REFERENCE,
  activityKindLabel,
  buildExchangeEvents,
  channelLabel,
  operationPresentation,
} from "./integrationsDisplay";
import type { NegotiationResponse } from "@/types";

describe("integrations display", () => {
  it("maps capabilities operations without inventing extras", () => {
    const rows = operationPresentation([
      "request_offer",
      "counter_offer",
      "accept_offer",
    ]);
    assert.equal(rows.length, 3);
    assert.equal(rows[0]?.group, "Offer discovery");
    assert.equal(rows[1]?.label, "Submit buyer counter");
  });

  it("documents the public REST contract", () => {
    assert.ok(AGENT_API_REFERENCE.some((item) => item.path.includes("capabilities")));
    assert.ok(AGENT_API_REFERENCE.some((item) => item.path.includes("offers/request")));
  });

  it("humanizes activity labels", () => {
    assert.equal(activityKindLabel("PROPOSAL_GENERATED"), "Proposal generated");
    assert.equal(channelLabel("AGENT_API"), "Agent API");
    assert.equal(channelLabel("OPERATOR"), "Operator test");
  });

  it("builds exchange events only from real turns", () => {
    const negotiation = {
      session_id: "s1",
      state: "MERCHANT_PROPOSAL_CREATED",
      proposal: null,
      previous_proposal: null,
      turns: [
        {
          turn_id: "t1",
          turn_number: 1,
          actor: "BUYER_AGENT",
          raw_message: "Need ANC headphones under A$350",
          structured_action: "REQUEST",
          structured_payload: { max_total_price_cents: 35000 },
          related_offer_id: null,
          created_at: "2026-09-13T00:00:00Z",
        },
        {
          turn_id: "t2",
          turn_number: 2,
          actor: "MERCHANT",
          raw_message: null,
          structured_action: "PROPOSAL",
          structured_payload: {},
          related_offer_id: null,
          related_proposal_id: "p1",
          created_at: "2026-09-13T00:00:01Z",
        },
      ],
      proposals: [
        {
          proposal_id: "p1",
          negotiation_session_id: "s1",
          version: 1,
          proposal_type: "INITIAL",
          outcome: "ACCEPT_BUYER_COUNTER",
          offer_id: "o1",
          offer: null,
          reason_codes: ["ORIGINAL_CONSTRAINTS_RETAINED"],
          explanation: ["Best policy-safe complete offer"],
          next_allowed_actions: ["ACCEPT", "COUNTER"],
          compromise: null,
          expires_at: null,
          created_at: "2026-09-13T00:00:01Z",
        },
      ],
      commercial: null,
      timing: null,
      events: [],
    } as NegotiationResponse;

    const events = buildExchangeEvents(negotiation);
    assert.equal(events[0]?.kind, "REQUEST");
    assert.equal(events[0]?.actor, "BUYER AGENT");
    assert.ok(events[0]?.parsed?.some((line) => line.includes("MAX TOTAL")));
    assert.equal(events[1]?.kind, "PROPOSAL");
    assert.equal(events[1]?.actor, "ASTRAOS");
  });

  it("returns empty events when negotiation has no history", () => {
    const empty = {
      session_id: "s0",
      state: "CREATED",
      proposal: null,
      previous_proposal: null,
      turns: [],
      proposals: [],
      commercial: null,
      timing: null,
      events: [],
    } as NegotiationResponse;
    assert.deepEqual(buildExchangeEvents(empty), []);
  });
});

# Phase 10 — Final UI/UX Storytelling

Phase 10 does not add intelligence. It makes the existing AstraOS web
interface tell one decision story without a Presentation, Judge, Demo,
or Pitch mode. The normal UI is the demo UI.

## Design Goals

- Enterprise decision intelligence: dense, calm, precise
- LIVE is the product; ARENA proves value; LEARN stays honest
- Product ranking and offer selection are visually distinct
- **Product ≠ Offer** is explained only when it is true
- Raw JSON and enums stay in Inspect, not the default path

Tokens already in `apps/web/app/globals.css` were reused: canvas /
surface / ink / muted / line, low radius, minimal shadow, three
surface levels. No purple gradients, glass, or giant KPI cards.

## Global Design System

Unchanged palette. Additions were copy, hierarchy, and process
treatment rather than a second theme. Buttons already use
`cursor-pointer`. Focus rings and `prefers-reduced-motion` remain.

## LIVE

Adaptive three-column layout: intent (~20%), current stage (~55%),
selected offer (~25%). Empty state is scenario-first. Loading lists
pipeline work (“Understanding buyer intent” … “Creating merchant
response”), never “AI is thinking”.

## Product → Offer Story

`DecisionBridge` and Construct share `expansionSteps()`:

matched products → candidate offers → feasible → policy-safe →
Pareto-efficient → one selected response.

Values come from the live construction / optimisation summaries.

## Product ≠ Offer Explanation

When SKUs differ, the bridge shows Best Product vs Selected Offer with
actual utility and contribution. When they match, the UI says the top
product remained the best complete offer and still lists commercial
terms. No hardcoded product names.

## Construct Stage

Funnel plus a dense offer table. Delivery / warranty / bundle use
human labels (`Same-day delivery`, `12-month warranty`), not raw enums.

## Pareto

Chart remains the signature Optimise visual. Caption states that a
frontier point is an efficient trade-off and that merchant objective
moves the selected point, not the frontier. Objective weights sit
beside the chart.

## Selected Offer

Right rail: product, price, terms, simulated buyer utility (not
purchase probability), contribution, intervention, short why-this-offer
checks. Proof stays on demand.

## Evidence / Proof

Match card: summary + coverage. Drawer: claim, field, value, source,
record, verification, freshness, derived rule.

## Negotiation

Structured machine exchange (actor, action, natural request, parsed
constraint, counteroffer). Payload JSON is behind Inspect. Timeline
copy: Request → Proposal → Counter → Response → Accept.

## Transaction

Execution rail: Accepted → Revalidation → Reserved → Order → Confirmed.
Revalidation checks are human-labeled. Copy distinguishes proposal proof
(issuance-time) from revalidation (current operational truth).

## Arena

Primary duel: Default, Always Discount, Semantic Only, AstraOS. Banner:
same buyer / merchant / rules; only strategy differs. Cheapest Eligible
stays behind More strategies. Synthetic disclaimer remains visible.

## Arena Ablation Presentation

Semantic Only vs AstraOS shows both offers and a commercial-difference
list (product, price, delivery, warranty, bundle) plus utility and
contribution deltas from the live duel. Benchmark chart is still
selection rate × contribution per opportunity.

## Learn

Story: Intent → Offer → Outcome → Learning record → Response model →
Future support. Status table: eligibility ACTIVE, semantic ACTIVE,
transparent utility PRIMARY, learned model EXPERIMENTAL, real observed
model FUTURE. Metrics stay in a compact table.

## Merchant Rules

Grouped: Commercial objective, Economics, Fulfilment & commercial
options. Drawer, not a new top-level page.

## Merchant Data

Unchanged operational tables (catalogue, inventory, evidence, ingest).
No card grid for hundreds of SKUs.

## Responsive QA

Manual browser pass on `http://localhost:3000` against a live API:

- **1440×900** — LIVE empty → Urgent Traveller → Match / Construct /
  Optimise / Negotiate / Transact; Arena duel + benchmark; LEARN;
  Merchant Rules drawer; Merchant Data table.
- **1366×768** — LIVE Urgent Traveller Match remains understandable:
  buyer request, structured intent, #1 product match, process rail, and
  selected-offer rail stay on one decision surface. Optimise still
  needs light scrolling.
- **1920×1080** was not separately captured; 1440 used the same
  three-column layout.

Mobile was not a focus.

## Accessibility

Process rail has `aria-current` and `aria-label` including state
(`Understand, complete`, `Match, active`). Pareto chart has `role="img"`
and an accessible label. Status is text plus color. Drawers remain
keyboard-closable. Offer filters are labeled `<select>`s.

## Performance

No new chart libraries. Expansion steps are derived, not fetched.
Offer lists remain paginated via existing run filters (40-row page).

## Targeted Validation

Frontend:

```
npx tsx --test lib/arenaDisplay.test.ts lib/decisionNarrative.test.ts \
  lib/processRail.test.ts lib/matchDisplay.test.ts
```

28 tests passed. `npx tsc --noEmit` passed. `npx next build` passed
(Next.js 16.3.5). No backend tests were run for this phase. Full
backend `pytest` was not run.

## Remaining Issues

- Funnel can show optimisation `policy_safe` above construction
  `feasible` when those summaries come from different counts; both
  values are backend-truthful, but the sequence can look inverted.
- Construct product filters are derived from the first returned offer
  page, not the full offer space.
- LEARN repeats capability status (table plus compact list).
- Arena Benchmark renders the latest API run. On the QA database that
  was a 6-mission run, not the published 100-mission Phase 11 artifact.
- Transact still exposes existing inventory/margin demo toggles.
  There is no Presentation / Judge / Demo / Pitch mode.
- API readiness can show “embeddings stale / partial index” on a cold
  demo host; that is operational, not a UI invention.
- Negotiation structured-payload buttons still keep JSON in the
  accessibility tree when expanded.

## Recommendation

**PHASE 12 — RELIABILITY / RED TEAM / DEMO HARDENING**

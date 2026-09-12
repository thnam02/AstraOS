# 3-minute AstraOS demo

Reset first: `make reset-demo` (or `python -m app.cli reset-demo`).
Open http://localhost:3000. Parser: **Rule-based**. No API key required.

If the LLM option is selected and the key is missing, AstraOS falls back
to the deterministic parser. Say that out loud and continue.

## 0:00 — LIVE

Paste is already the hero intent, or click **Example request**.
Press **UNDERSTAND → NEGOTIATE**.

Say: “Traditional e-commerce is designed for people browsing pages.
AstraOS is designed for the buyer’s agent.”

## 0:15 — Intent

Point to **MANDATORY** (ANC, budget, same-day), **CONTEXT** (long-haul),
outcomes, and reliability > lowest price.

Say: “We don’t reduce the request to keywords.”

## 0:35 — Qualify + match

Point to checked / eligible counts and semantic matches with proof.

## 0:55 — Construct

Scroll to offer-space counts.

Say: “Selecting the right product isn’t enough.”
One product becomes many commercial configurations.

## 1:15 — Optimise

Point to the Pareto chart. X is merchant contribution. Y is
**Simulated Buyer Utility**, not purchase probability.

Say: “AstraOS optimises both buyer fit and merchant economics.”

## 1:35 — Intervention

Use the numbers on screen. Seed 2026 typically proposes **Aurora Commute 06**
at **A$301.85** with same-day, 36-month warranty, and a hard case.

Typical lever comparison from the same seed: same-day costs about **A$8**
and lifts simulated utility far more than a **~A$24** discount (which is
also usually not policy-safe on the baseline SKU). If the live run differs,
use the live numbers.

Say: “For this urgent traveller, spending on faster fulfilment may be
more efficient than giving away price.”

## 1:55 — Negotiate

Send **Can you get this below A$315?**

Show the natural-language line and the structured `COUNTER` payload.

## 2:15 — Transact

**EXECUTE ACCEPTANCE**. Point to revalidation PASS, reservation, order
`AST-…`.

Say: “The entire flow is machine-to-machine.”

Optional failure: **STOCK → 0**, then accept again. Revalidation fails.
No order. Restore **STOCK → 14**.

Optional policy: **MARGIN 25%**, rerun, show frontier change.

## 2:35 — ARENA

Open ARENA. Run a live duel or load the precomputed benchmark.

Say: “We evaluate against simpler merchant strategies using a transparent
synthetic buyer model.”

Point to: “Synthetic evaluation — not observed real-world sales uplift.”

## 2:50 — Close

Say: “In agentic commerce, the unit of competition is no longer just the
product or the price. It is the entire offer.”

LEARN is optional. Do not train live. The model is synthetic.

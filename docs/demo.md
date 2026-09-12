# 3-minute AstraOS demo

Reset first: `make reset-demo` (or `python -m app.cli reset-demo`).
Open http://localhost:3000. Parser default: **LLM**, with automatic
rule-based fallback. If `LLM_API_KEY` is missing, say that AstraOS fell
back to the deterministic parser and continue. Do not stop the demo.

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
Mandatory constraints already dropped ineligible SKUs before ranking.
Match scores are Product / Context / Preference Fit — Evidence
Coverage is support/trust, not relevance. Open **Inspect evidence**
to show claim → source → record → verification → freshness.
If the inspector shows hashing fallback, say the local semantic model
was unavailable and the pipeline stayed online.

## 0:55 — Construct

Scroll to offer-space counts.

Say: “Selecting the right product isn’t enough.”
One product becomes many commercial configurations.

## 1:15 — Optimise

Point to the Pareto chart. X is merchant contribution. Y is
**Simulated Buyer Utility**, not purchase probability.

Say: “AstraOS optimises both buyer fit and merchant economics.”

Open **Merchant Rules → Commercial Objective**. Start on **Balanced**.
The selected diamond is one efficient offer. Switch to **Margin**. The
frontier does not move; the selected point may. Switch to **Growth**
to move toward stronger buyer fit. If all three pick the same offer,
say the mission is objective-insensitive — that is a real result.

Say: “Merchant strategy selects among efficient trade-offs. It does
not change what is allowed.”

## 1:35 — Intervention

Use the numbers on screen. Seed 2026 typically proposes **Aurora Commute 06**
at **A$301.85** with same-day, 36-month warranty, and a hard case.

Typical lever comparison from the same seed: same-day costs about **A$8**
and lifts simulated utility far more than a **~A$24** discount (which is
also usually not policy-safe on the baseline SKU). If the live run differs,
use the live numbers.

Open **Inspect proof** on the selected offer. Price, delivery,
warranty, bundle, and returns each have a source badge.

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

Open ARENA. Run a live duel on the primary ablation:

Default → Always Discount → Semantic Only → AstraOS.

Same buyer, catalogue, inventory, policy, and buyer model. Only strategy
changes. Point to Semantic Only vs AstraOS: product matching vs the
complete commercial response.

Say: “We evaluate against simpler merchant strategies using a transparent
synthetic buyer model.”

Point to: “Synthetic evaluation — not observed real-world sales uplift.”
If Always Discount wins a mission, show it. Do not hide losses.

## 2:50 — Close

Say: “In agentic commerce, the unit of competition is no longer just the
product or the price. It is the entire offer.”

LEARN is optional. Do not train live. The model is synthetic.

## Optional — External Buyer Agent (Phase 4)

With the API running, in a second terminal:

```bash
make buyer-demo-deterministic
# or: make buyer-demo
```

This is a separate process. It discovers `/api/v1/agent/capabilities`,
requests an offer, may inspect or counter, then accepts or rejects.
LIVE can stay open as the merchant view of the same engine. Do not
copy-paste between them; both talk to the API.

If the buyer LLM key is missing, the Buyer Agent falls back to its
deterministic policy validator. That is still a real M2M session.

## Optional — Merchant ingestion (Phase 6)

Open Merchant Data. Upload `examples/merchant-data/harbor-sound.json`.
Show the dry-run counts, then Apply import. Semantic documents refresh
only when product facts change. Then send a Buyer Agent request: AstraOS
decides over the canonical catalogue, not a hardcoded fixture.

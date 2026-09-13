# Phase 7 — Hero Evidence Realification

AstraOS now traces buyer-visible claims from intent through match
rationale, merchant facts, evidence, source, and the final offer.
This phase did not change ranking, qualification, economics, Pareto,
negotiation policy, or transaction rules.

```
Merchant Sources
      ↓
Ingestion + Provenance
      ↓
Canonical Facts
      ↓
Eligibility / Matching / Offers
      ↓
Proof Compiler
      ↓
Machine-readable proposal
      ↓
External Buyer Agent
```

## Previous Evidence State

Phase 6 already stored `AttributeEvidence` / `DataSource` rows and
mapped Harbor import evidence. LIVE showed source names, but
verification and freshness were collapsed, the offer “Inspect proof”
drawer showed utility-trace math, and displayed coverage reused the
ranking `evidence_coverage` score. Public inspect could invent
`PRODUCT_SPECIFICATION` claims from raw attributes.

## Evidence Architecture

Existing provenance models were reused. No second evidence store.

Machine-readable proof lives in `app/decision/proof/`:

- `ProofItem` — claim, value, unit, evidence id, source, record,
  verification, freshness, observed/valid times, derived flag, rule
- `ProofBundle` — items plus displayed-claim coverage
- `OfferProofCompiler` (`compiler.py`) — deterministic; no LLM
- `resolver.py` — domain source precedence and CONFLICTED
- `freshness.py` — central TTL (inventory 48h, price 7d, same-day 24h;
  product facts current unless `expires_at`)
- `derived.py` — documented derivations only
- `enrich.py` — attaches provenance after ranking without changing scores

## Source Types

Normalized / accepted types:

- `MERCHANT_PRODUCT_FEED`
- `MERCHANT_INVENTORY`
- `MERCHANT_PRICING` / `PRICING_FEED`
- `FULFILMENT_CONFIGURATION`
- `WARRANTY_POLICY`
- `BUNDLE_CONFIGURATION`
- `RETURN_POLICY`
- `MERCHANT_MANUAL_ENTRY`
- `EXAMPLE_MERCHANT_IMPORT`
- `SYNTHETIC_DEMO_FIXTURE`

Synthetic seed rows stay labelled synthetic. Harbor example-import ANC
on Mini stays `EXAMPLE_MERCHANT_IMPORT`. They were not renamed to
product feed.

## Verification vs Freshness

These are separate.

Verification answers: can this claim be traced to an accepted source?

- `VERIFIED` — including merchant-declared feed rows
- `UNVERIFIED`
- `CONFLICTED` — same-precedence values disagree
- `UNKNOWN` — no evidence

Freshness answers: is the evidence current enough to use?

- `CURRENT`
- `STALE` — `expires_at` passed, or operational TTL exceeded
- `UNKNOWN`

Stale inventory is not shown as current executable stock. Conflicted
product facts are omitted from displayed rationale and are not SATISFIED.

## Hero Merchant Data

Harbor Sound Co. still enters only through the Phase 6 importer:

`examples/merchant-data/harbor-sound.json` → ingestion → canonical
model → evidence → semantic refresh → normal pipeline.

The feed now carries evidence for existing variant facts (ANC, wireless,
foldable, microphone, battery, weight, comfort, travel, inventory,
price). Missing attributes stay absent. Night Cabin ANC remains expired
(stale). Mini ANC remains example-import.

## Claim Lineage

Match reason → supporting claim → evidence → source record.

`enrich_match` copies evidence id, source type/name/record, verification,
freshness, observed time, and derivation onto `MatchFact` after scores
are already computed.

## Derived Claims

Documented rules only:

- `headphones_lightweight_v1` — weight ≤ 250 g, including parsed
  `"230 grams"`
- `fulfilment_same_day_v1` / `selected_delivery_option_v1` — selected
  fulfilment option with `days == 0`
- selected warranty / bundle / returns / list price

Derived items set `derived=true` and `derivation_rule`. They are never
presented as merchant-supplied raw facts.

## Proof Compiler

`compile_match_proof` and `compile_offer_proof` are deterministic.

Public commercial proof includes price, delivery, warranty, bundle
(if present), returns, and same-day when selected. It excludes COGS,
contribution, margin, and merchant objective weights.

Displayed-claim coverage formula:

```
unsupported_displayed_claim_rate
  = unsupported_displayed / displayed_claims

where displayed_claims are non-incomplete proof items
and a claim is supported if evidence_id OR derived
```

This is not ranking `evidence_coverage` (need-support weight ratio).
Product / Context / Preference Fit remain separate scores.

## Proposal Proof Snapshot

`attach_proof_bundle` writes `proof_bundle` onto the proposal snapshot
at issuance. Later merchant edits do not rewrite that historical bundle.
Acceptance still revalidates live inventory, price, delivery, and policy.

## Public Buyer-Agent Proof

`GET/POST /api/v1/agent/*` inspect returns `EvidenceClaim` rows from the
snapshotted bundle. The external Buyer Agent does not import AstraOS
internals. `same_day_delivery` remains present for the validator.

## Hero Evidence Results

Imported-only Harbor run (seed deactivated during the request):

| Item | Result |
| --- | --- |
| Top product | Harbor Cabin 12 (`HS-CAB-12-BLK`) |
| Selected offer | Harbor Cabin 12, A$323.00, same-day, 24-month warranty, travel adapter, 60-day returns |
| Displayed claims | 9 |
| Claims with evidence / derivation | 9 |
| Verified | 9 |
| Synthetic displayed | 0 |
| Unsupported displayed claim rate | 0 |
| Hard-constraint proof rate | 1.0 |
| Commercial-term proof rate | 1.0 |
| Match-rationale proof rate | 1.0 |
| Public inspect | PASS, no private leak |
| Transaction | CONFIRMED, revalidation present |

## Unsupported Displayed Claim Rate

0. The LIVE card only renders facts with `evidence_id` or a documented
derivation. Unsupported facts are omitted rather than fabricated.

## Hard Constraint Proof Coverage

1.0 on the hero SATISFIED constraints (evidence id or operational
source reference such as delivery options / list price). Semantic
similarity does not mark UNKNOWN as SATISFIED.

## Commercial Term Proof Coverage

1.0 for the selected price, delivery, warranty, bundle, and returns.

## Match Rationale Proof Coverage

1.0 for the displayed match reasons (3–5 LIVE reasons plus compiled
proof items).

## UI Changes

- Match card: compact source badges (PRODUCT FEED, INVENTORY, PRICING,
  FULFILMENT, WARRANTY, BUNDLE, RETURNS, EXAMPLE IMPORT, SYNTHETIC)
- Evidence coverage uses displayed-proof coverage, not ranking coverage
- Evidence drawer: claim, canonical field, value, source, record,
  verification, freshness, observed, derived / rule
- Selected offer: Inspect proof groups product vs commercial terms
- Why this product instead of #1 uses grounded commercial proof items
- Catalogue Merchant Data: concise evidence-quality summary

## Targeted Validation

```
pytest apps/api/tests/test_proof.py
pytest apps/api/tests/test_agent_proof.py
npm test  # includes lib/matchDisplay.test.ts
ruff check <changed Phase 7 modules>
npx tsc --noEmit
```

Conflict, stale inventory freshness, cross-SKU isolation, and private
key filtering are covered by unit tests. One focused imported-hero E2E
is in `app.eval.hero_evidence`.

The full backend suite was not run.

## Known Limitations

- Ranking `evidence_coverage` is still the need-support weight ratio
  used in rerank. It is intentionally unchanged.
- Qualification can still SATISFY a hard constraint from a canonical
  attribute when no evidence row exists (pre-existing fail-open for
  attributes). Harbor hero constraints used evidence or operational
  source references.
- Public proof is a snapshot of buyer-relevant claims, not a dump of
  every catalogue evidence row.
- mypy was deferred; targeted ruff and `tsc --noEmit` were run instead.
- Full frontend production build was not run.
- Harbor is a fictional example merchant for reproducibility.

## Next Step

PHASE 11 — ARENA ABLATION & COMPETITIVE PROOF

Do not begin Phase 11 automatically.

# AstraOS

Merchant-side offer intelligence for AI commerce.

**Product ≠ Offer.**

AstraOS is a merchant-side decision engine for agentic commerce. It takes AI
shopping intent, qualifies products against hard constraints, and (in later
stages) will construct commercial offers, enforce merchant policies, optimise
those offers, return proof-backed machine-readable responses, and learn from
Intent → Offer → Outcome data.

This repository is the technical foundation for UAVS Hackathon 2026.

## Current status

**Stage 4 — Offer Construction + Dynamic Bundling**

- Stage 0 — Scaffold — COMPLETE
- Stage 1 — Domain model and merchant data — COMPLETE
- Stage 2 — Intent interpretation + deterministic eligibility — COMPLETE
- Stage 3 — Deep intent intelligence + semantic matching — COMPLETE
- Stage 4 — Offer construction + dynamic bundling — COMPLETE

**Eligibility answers:** *Can this product satisfy the mandatory request?*

**Semantic matching answers:** *Among products that can satisfy it, which ones
best solve the human buyer's actual problem?*

**Offer construction answers:** *What valid commercial configurations can the
merchant construct around those products?*

A product is not an offer. Stage 4 enumerates the offer space. It does not
choose a winner, compute buyer utility, or draw a Pareto frontier.

Semantic similarity never overrides a hard constraint. A semantic score is
**Semantic Fit**, not a purchase, win, or agent probability.

## What Stage 3 adds

```
AI shopping intent
  → structured ShoppingIntent
      hard constraints + soft preferences
      + context + desired outcomes + values + trade-offs
  → Stage 2 deterministic eligibility
  → eligible SKUs only
  → IntentSemanticProfile + ProductSemanticDocument
  → embedding similarity
  → grounded rerank (product / context / preference / evidence)
  → RankedProductMatch[]
```

Stage 2 is unchanged in role. Soft preferences still never admit or exclude a
SKU. `VIOLATED` and `UNKNOWN` mandatory conditions still block eligibility.
Semantic ranking never sees those products unless you inspect a qualification
run for debugging.

## Deep intent

`ShoppingIntent` keeps every Stage 2 field and adds:

| Layer | Model | Role |
| --- | --- | --- |
| Context | `IntentContext` | usage / lifestyle situation |
| Desired outcomes | `DesiredOutcome` | what the shopper is trying to achieve |
| Values | `ValuePreference` | only when merchant data can support them |
| Trade-offs | `TradeoffPreference` | relative importance between goals |
| Unsupported needs | `UnsupportedSemanticNeed` | semantic ask with no catalogue representation |

Canonical headphone-MVP labels live in
`apps/api/app/decision/intent/taxonomy.py`.

**Context:** `long_haul_travel`, `short_travel`, `commuting`, `office`,
`gaming`, `studio`, `sports`, `frequent_travel`, `extended_continuous_use`

**Outcomes:** `low_fatigue`, `strong_noise_isolation`,
`long_battery_endurance`, `reliable_extended_use`, `portable_travel`,
`clear_calls`, `immersive_audio`, `easy_storage`, `weather_resilience`,
`travel_convenience`

**Values:** `durability`, `repairability`, `sustainability` — reserved, but
the current seed has no supporting attributes. Parsers record these as
unsupported semantic needs instead of inventing a score.

The Stage 3 hero request:

> I'm flying from Sydney to Singapore tomorrow and need wireless
> noise-cancelling headphones under A$350. I need them delivered today.
> I'll wear them for hours, so comfort and reliability matter more than
> getting the absolute cheapest option.

is interpreted as:

- **Hard:** category headphones, wireless, ANC, price `< A$350`, delivery today
- **Soft:** comfort high, reliability high, price sensitivity medium
- **Context:** long-haul travel, extended continuous use
- **Outcomes:** low fatigue, reliable extended use, travel convenience
- **Trade-offs:** comfort > lowest price, reliability > lowest price

`flying … tomorrow` is travel context, not delivery. Delivery tomorrow requires
delivery words.

## Parsers

`IntentParser` is still a protocol.

- `RuleBasedIntentParser` (`rule_based.v2`) — deterministic demo / test /
  fallback. It recognises common phrases. It is not a general NLP engine.
- `LLMIntentParser` (`llm.v2`) — optional schema-constrained structured output
  for the deeper layers. One validation retry, then rule-based fallback.

`INTENT_PARSER_MODE=rule_based` (default) or `llm`. Tests never call a live
model.

## Stage 2 eligibility (preserved)

Every hard condition still resolves to exactly one of `SATISFIED`,
`VIOLATED`, or `UNKNOWN`. Eligible iff `violated_count == 0` and
`unknown_count == 0`.

Field lookup still goes through the registry. Missing or null attributes are
`UNKNOWN`. Soft preferences are interpretation metadata only.

| Phrase | Result |
| --- | --- |
| `under $350` / `A$350` | `price LT 35000` AUD cents |
| `$350 or less` / `up to $350` | `price LTE 35000` |
| `delivered today` / `same day` | `delivery_days LTE 0` |
| `deliver tomorrow` | `delivery_days LTE 1` |
| `noise cancelling` / `ANC` | `anc EQ true` |

## Semantic documents and embeddings

Each active variant gets a deterministic `ProductSemanticDocument` built from
merchant facts only: ANC, battery, weight, foldable, wireless, comfort score,
travel score, microphone, water resistance, same-day eligibility. Missing
attributes are omitted. Use-case text is a template from present facts, not
LLM marketing copy.

`IntentSemanticProfile` is built from context, outcomes, preferences, values,
and trade-offs. Hard constraints are not included in ranking text so similarity
cannot substitute for qualification.

Embeddings use a local `EmbeddingProvider`:

- `LocalEmbeddingProvider` — scikit-learn `HashingVectorizer`, 384 dimensions,
  L2-normalised, model name `hashing-vectorizer-384`. No download, no API key.
- `DeterministicEmbeddingProvider` — tiny mock for tests.

pgvector is not required. Vectors are stored as JSONB on
`variant_embeddings` with `embedding_model`, `semantic_document_version`,
`document_hash`, and `generated_at`. Unchanged documents are not recomputed.

```bash
make embeddings
```

## Grounded matching

`SemanticMatchingService` pipeline:

1. Parse deep intent
2. Run the existing eligibility evaluator
3. Keep eligible variants only
4. Embed the intent profile
5. Cosine similarity against cached product embeddings
6. Structured rerank: `product_fit`, `context_fit`, `preference_fit`,
   `evidence_coverage`, `overall_semantic_fit`
7. Persist the match run

Feature → outcome mappings live in one place:
`apps/api/app/decision/retrieval/mapping.py`. Example: long-haul travel is
supported by ANC, battery, lower weight, foldable, and travel score. Missing
features are skipped, not scored as zero.

Every ranked candidate includes match reasons that cite merchant facts and
evidence ids. Unsupported semantic needs (for example “luxurious feel”) are
exposed and lower evidence coverage. They do not invent a luxury score.

Ranking: eligible products by `overall_semantic_fit` DESC, then evidence
coverage, then price, then SKU. Merchant economics are not mixed in.

## APIs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/api/v1/catalogue/products` | List products |
| GET | `/api/v1/catalogue/products/{id}` | Product + variants |
| GET | `/api/v1/catalogue/variants/{id}` | SKU detail |
| GET | `/api/v1/catalogue/stats` | Catalogue counters |
| GET | `/api/v1/merchant/policy` | Active policy |
| PATCH | `/api/v1/merchant/policy` | Update stored policy bounds/flags |
| POST | `/api/v1/intent/analyse` | Deep intent only |
| POST | `/api/v1/intent/qualify` | Stage 2 parse + qualify |
| GET | `/api/v1/intent/qualification/{run_id}` | Qualification run |
| GET | `/api/v1/intent/qualification/{run_id}/variants/{variant_id}` | One condition trace |
| POST | `/api/v1/match` | Qualify then semantically rank |
| GET | `/api/v1/match/{run_id}` | Persisted match run |
| POST | `/api/v1/offers/generate` | Construct the offer space |
| GET | `/api/v1/offers/runs/{offer_run_id}` | Paginated / filtered candidates |
| GET | `/api/v1/offers/{offer_id}` | One configuration + proof |

`POST /api/v1/match` body:

```json
{ "intent": "I'm flying from Sydney to Singapore...", "parser_mode": "rule_based", "limit": 8 }
```

Response includes structured intent, qualification counts, ranked matches with
Semantic Fit scores and grounded reasons, and
`intent_parse_ms` / `qualification_ms` / `embedding_ms` / `rerank_ms` /
`total_ms`.

Match runs persist raw text, structured intent, parser version, eligible set,
embedding model, scores, and rerank payload.

`POST /api/v1/offers/generate` accepts `{ "intent": "..." }` or
`{ "match_run_id": "..." }`. The response is a constructed offer space:
estimated / generated / feasible / rejected counts, dimension sizes, and a
machine-readable preview. No offer is labelled best or recommended.

## Frontend

`/` is LIVE V3:

- Left: buyer-agent request
- Center: AstraOS understanding — mandatory, context, outcomes, preferences,
  trade-offs — then qualification counts
- Right: matched products with Semantic Fit
- Below: Offer Space explorer — Product ≠ Offer, filters, totals,
  intervention cost, proof. Bundles are labelled context-relevant candidates,
  not recommendations.

Process rail after a run: Understand / Qualify / Match / Construct complete.
Optimise is next. Negotiate, Transact, Learn remain locked.

Catalogue inspector remains at `/catalogue`.

## Evaluation

Frozen human-authored cases live in `apps/api/app/eval/cases.py` (≥ 50,
headphones only). Gold labels cover constraints, context, outcomes,
preferences, and graded relevance predicates. Extra short variants use
keyword gold, not the ranker or a live LLM.

```bash
make eval
```

Baselines:

- **A** — structured eligibility + price sort
- **B** — structured eligibility + plain embedding similarity
- **AstraOS** — eligibility + deep intent + outcome mapping + grounded rerank

Hard-constraint violation among returned semantic matches must be `0`.

## What Stage 4 adds

```
RankedProductMatch[]
  → price options allowed by merchant policy
  → variant delivery / warranty / bundle / return rows
  → context-relevant bundle filter
  → Cartesian expansion (capped)
  → static feasibility
  → OfferCandidate[]
```

`OfferCandidate` holds product, price adjustment, delivery, warranty, bundle,
return policy, buyer total, descriptive intervention cost, proof, and expiry.
It does not store buyer utility, P(win), Pareto status, or a recommended flag.

Price states are BASE, −3%, −5%, −7%, −10%, never above
`MerchantPolicy.maximum_discount_rate`. Money is integer cents.

Bundles come only from `BundleOption` + `VariantBundleOption`. Relevance is an
explicit mapping in `apps/api/app/decision/offers/bundles.py` (e.g. long-haul
travel → travel adapter, airplane adapter, hard case). Gaming does not treat a
travel adapter as relevant. No LLM invents a physical accessory.

Default construction caps: 8 products, 5,000 candidates. If the estimate
exceeds the cap, products, then price, bundle, warranty, delivery, and
return depth are reduced in that order. `pruning_reason` is recorded.

Offers expire after `OFFER_TTL_SECONDS` (default 300). Expiry supports later
revalidation. Nothing is accepted or checked out here.

## Architecture

```
Routes → Services → Repositories / Decision modules → Database
```

Decision logic lives under `apps/api/app/decision/intent/`,
`apps/api/app/decision/eligibility/`, `apps/api/app/decision/retrieval/`,
and `apps/api/app/decision/offers/`.

Money remains integer cents. The MVP scans active variants in the selected
category. That is acceptable for a few hundred SKUs.

## Synthetic seed

```bash
make seed
```

Deterministic via `ASTRAOS_SEED=2026`. Fictional headphone brands only.
`make reset-db` remigrates from the Stage 0 baseline and reseeds.

## Local prerequisites

- Docker and Docker Compose (recommended), or
- Python 3.12, Node.js 22+, PostgreSQL 16

Host development defaults to `POSTGRES_HOST=localhost` and user `astraos`.

```bash
cp .env.example .env
make migrate
make seed
make embeddings
```

```bash
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd apps/web && npm run dev
```

Optional LLM parser:

```
INTENT_PARSER_MODE=llm
LLM_API_KEY=...
```

Without those values the API stays on the rule-based parser.

## Available commands

| Command | Purpose |
| --- | --- |
| `make up` | Build and start Compose services |
| `make down` | Stop Compose services |
| `make logs` | Follow Compose logs |
| `make test` | Run API pytest suite against `astraos_test` |
| `make lint` | Run ruff and mypy |
| `make migrate` | Apply Alembic migrations |
| `make seed` | Upsert the synthetic merchant catalogue |
| `make embeddings` | Build or refresh cached product embeddings |
| `make eval` | Run the frozen Stage 3 evaluation suite |
| `make reset-db` | Destructive remigrate + seed |

## Service URLs

| Service | URL |
| --- | --- |
| Frontend LIVE | http://localhost:3000 |
| Catalogue | http://localhost:3000/catalogue |
| Backend | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |

## Roadmap

- **Stage 0 — Scaffold** — COMPLETE
- **Stage 1 — Domain model and merchant data** — COMPLETE
- **Stage 2 — Intent interpretation + deterministic eligibility** — COMPLETE
- **Stage 3 — Deep intent intelligence + semantic matching** — COMPLETE
- **Stage 4 — Offer construction + dynamic bundling** — COMPLETE
- **Stage 5 — Merchant economics + Pareto optimisation**
- **Stage 6 — B2A negotiation**
- **Stage 7 — Transaction loop**
- **Stage 8 — Agent Arena + benchmark**
- **Stage 9 — Intent → Offer → Outcome learning**
- **Stage 10 — Protocol adapter + demo hardening**

Stage 4 does not implement buyer utility, P(win), Pareto frontiers,
recommended offers, negotiation, checkout, orders, Arena, or learning.

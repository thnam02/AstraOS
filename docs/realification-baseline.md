# AstraOS Realification Baseline

Phase 1 freeze of the completed hackathon core. This is a BEFORE snapshot.
No scoring, parser, embedding, Pareto, merchant-economics, Arena, or
learning behaviour was changed to produce these numbers.

## Version

- Logical version: `astraos-hackathon-core-v1`
- Git commit: `96389215844268d63e5e9c0b8396369a20adf1d1`
- Commit date: `2026-09-13 05:32:13 +1000`
- Commit subject: `feat: improve and refine ui`
- Capture date: `2026-09-13`
- Seed: `2026`
- Environment: local PostgreSQL 16 (`astraos_baseline`), API
  `http://127.0.0.1:8001`, `APP_ENV=development`,
  `INTENT_PARSER_MODE=rule_based`, `RESPONSE_MODEL_MODE=COLD_START`,
  `ASTRAOS_DEMO_MODE=true`
- Alembic head: `0010_learning` (single head)
- Proposed tag (not executed):

```bash
git tag astraos-hackathon-core-v1 96389215844268d63e5e9c0b8396369a20adf1d1
```

## Current Architecture

UNDERSTAND → QUALIFY → MATCH → CONSTRUCT → OPTIMISE → NEGOTIATE →
TRANSACT → LEARN.

External Buyer Agents reach the same services through REST
`/api/v1/agent/*`. An optional MCP stdio adapter calls that REST surface
only. Defaults: rule-based parser, hashing embeddings (384-d), cold-start
simulated buyer utility, merchant selection α = 0.5
(`normalized_weighted_sum`). Arena and LEARN labels are synthetic.

## Build Health

### Backend

| Check | Result |
| --- | --- |
| pytest | **325 passed**, 0 failed, 0 skipped, 2 deprecation warnings (Starlette/httpx, anyio BlockingPortal), ~140s |
| ruff check | passed |
| mypy `app` | Success, 210 files |

### Frontend

| Check | Result |
| --- | --- |
| `npm test` | **23 passed**, 0 failed, 0 skipped |
| `npm run build` | success |
| `npm run lint` | **2 errors, 2 warnings** (pre-existing; not fixed in Phase 1) |

Lint errors: `LearnWorkbench.tsx:46` and `MerchantPolicyDrawer.tsx:62`
(`react-hooks/set-state-in-effect`). Warnings: `LiveWorkbench.tsx`
missing `rerunOptimisation` dependency; unused `perSku` in
`OfferExplorer.tsx`. Production build still succeeds.

### Migrations

Blank database `astraos_baseline` upgraded to `0010_learning`. Single
head. Seed `python -m app.seed` succeeded and was rerun safely
(idempotent upsert, same counts). Embeddings: 332 variants,
`hashing-vectorizer-384`, document version `product_semantic.v1`.

### Docker

`docker-compose.yml` defines `db` / `api` / `web`. `make up` is the
documented compose path. This capture used an already-running local
Postgres; the `docker` CLI was not available in the capture shell.

### Health / readiness

`GET /health` → `ok`.

`GET /ready` → `degraded` with required checks passing:

- database reachable
- active merchant policy present
- seed catalogue 338 variants
- embeddings 332 cached; local hashing fallback available
- learned model: cold-start utility fallback
- llm parser: rule-based fallback
- protocol adapter: REST guaranteed; MCP optional

Degraded modes: `learned_model_unavailable`, `llm_unavailable`.
Expected for the current default configuration.

## Seed Data

Read from `astraos_baseline` after deterministic seed `ASTRAOS_SEED=2026`.

### Merchant

- Code: `ASTRA_ELECTRONICS`
- Name: Astra Electronics

### Catalogue

| Metric | Count |
| --- | ---: |
| Products | 156 |
| Active products | 156 |
| Variants | 338 |
| Active variants | 332 |

Headphones-only catalogue.

### Operations

| Metric | Count |
| --- | ---: |
| Inventory records | 338 |
| In stock (`units_available > units_reserved`) | 289 |
| Out of stock | 49 |
| Same-day capable variants (catalogue UI) | 202 |
| Delivery option types | 3 (`SAME_DAY`, `EXPRESS`, `STANDARD`) |
| Warranty option types | 3 (`STANDARD_12`, `EXTENDED_24`, `EXTENDED_36`) |
| Bundle option types | 3 (`HARD_CASE`, `TRAVEL_ADAPTER`, `AIRPLANE_ADAPTER`) |
| Return policy types | 2 (`STANDARD_30`, `FLEX_60`) |

### Evidence

| Metric | Count |
| --- | ---: |
| Attribute evidence rows | 4169 |
| Stale evidence (`expires_at < now()`) | 125 |
| Variants flagged missing core attributes (`anc`, `battery_hours`, `comfort_score`, `travel_score`, `weight_g`, `wireless`) | 24 |

Active variants missing `anc` evidence: 5. `wireless` evidence is
present on all active variants.

### Policy

Active policy: **Astra Electronics Default Policy**

- Minimum margin rate: `0.1500`
- Maximum discount rate: `0.1000`
- Delivery subsidy enabled: true (max 1000 cents)
- Warranty upgrade enabled: true (max 1400 cents)
- Bundles enabled: true (max 900 cents)
- Flexible returns enabled: true
- Loyalty enabled: false

## Hero Flow

Registered scenario `HERO_TRAVEL`. Buyer profile **INTENT_ADAPTED**.
Path: live `POST /api/v1/negotiations` (not the CLI agent helper).

Intent text:

> I'm flying from Sydney to Singapore tomorrow and need wireless
> noise-cancelling headphones under A$350. I need them delivered today.
> I'll wear them for hours, so comfort and reliability matter more than
> getting the absolute cheapest option.

### Intent

- Parser mode: `rule_based`
- Parser implementation: `rule_based.v2`
- Hard constraints: `anc EQ true`, `price LT 35000`, `delivery_days LTE 0`, `wireless EQ true`
- Preferences: comfort 0.9, reliability 0.85, price 0.3
- Context: `long_haul_travel`, `extended_continuous_use`
- Desired outcomes: `low_fatigue`, `reliable_extended_use`, `strong_noise_isolation`, `travel_convenience`
- Tradeoffs: comfort > price, reliability > price

### Qualification

- Variants checked: 332
- Eligible: 62
- Violated: 259
- Uncertain: 11

### Match

Embedding provider `hashing-vectorizer-384`, document
`product_semantic.v1`.

| Rank | Product | SKU | Semantic fit | Evidence |
| ---: | --- | --- | ---: | ---: |
| 1 | Sonic Cabin 32 | SON-T32-SLV | 0.8202 | 1.0 |
| 2 | Atlas Cabin 72 | ATL-T72-BLK | 0.8195 | 1.0 |
| 3 | Nova Fold 19 | NOV-T19-WHT | 0.7829 | 1.0 |
| 4 | Sonic Sport 38 | SON-S38-BLK | 0.7818 | 1.0 |
| 5 | Nova Fold 19 | NOV-T19-SLV | 0.7809 | 1.0 |

### Construction

- Matched products used: 8
- Estimated candidate offers: 2880
- Generated offers: 2880
- Feasible offers: 770
- Rejected offers: 2110
- Rejection mix: `DELIVERY_NOT_AVAILABLE` 1920, `WARRANTY_NOT_AVAILABLE` 80, `BUNDLE_INCOMPATIBLE` 60, `RETURN_POLICY_DISABLED` 50

### Optimisation

- Offers considered: 2880
- Policy-safe: 955
- Policy-rejected: 1925
- Pareto-efficient: 25
- Selected product: **Aurora Commute 06** (`AUR-T06-BLK`)
- Selected offer id: `26459f3e-5f0d-4f7f-8b79-e18963934b2a`
- Total price: A$301.85 (30185 cents)
- Delivery `SAME_DAY`, warranty 36 months (`EXTENDED_36`), bundle `HARD_CASE`, returns `FLEX_60`
- Simulated buyer utility: 0.876066
- Merchant contribution: 12415 cents
- Intervention cost: 3600 cents
- Merchant selection α / rule: `0.5` / `normalized_weighted_sum`
- Buyer model: `SIMULATED_UTILITY` / `INTENT_ADAPTED`

Best standalone product match (Sonic Cabin 32) is not the selected
offer. This is current intended Product ≠ Offer behaviour, not a defect.

### Negotiation

Representative counter: `Can you get this below A$315?`

- Opening proposal: Aurora Commute 06 at A$301.85
- Merchant outcome: `ACCEPT_BUYER_COUNTER`
- Reason codes: `EXACT_COUNTER_SATISFIED`, `ORIGINAL_CONSTRAINTS_RETAINED`
- Counter offer unchanged at 30185 cents (already under A$315)
- Turn timing: interpretation 0.05 ms, delta 0.12 ms, reoptimisation 1619.59 ms, proposal 1.52 ms, **total 1628.63 ms**

### Transaction

- Acceptance: yes
- Revalidation: `PASSED` (all advertised checks PASS)
- Reservation: created and `CONSUMED`
- Order number: `AST-2026-000001`
- Final status: `CONFIRMED`
- Payment: `SIMULATED` / `NOT_REQUIRED_FOR_DEMO`
- Transaction timing: revalidation 7.64 ms, reservation 7.94 ms, order 8.21 ms, **total 25.46 ms**

## Latency

One warmup create, then 10 timed LIVE creates on `127.0.0.1:8001`.
Laptop / single-process. **Not production-scale.**

Create-path `negotiation_turn_ms` is 0 because the timed loop is
proposal creation only. The representative counter above is the
negotiation sample.

| Stage | n | median (ms) | p95 (ms) |
| --- | ---: | ---: | ---: |
| intent_ms | 10 | 0.29 | 0.46 |
| qualification_ms | 10 | 232.77 | 315.81 |
| semantic_match_ms | 10 | 14.49 | 15.56 |
| offer_construction_ms | 10 | 852.44 | 924.76 |
| optimisation_ms | 10 | 743.55 | 803.14 |
| negotiation_turn_ms (create path) | 10 | 0.00 | 0.00 |
| negotiation_turn_ms (one counter) | 1 | 1628.63 | — |
| transaction_ms (one accept) | 1 | 25.46 | — |
| total_decision_ms | 10 | 1858.51 | 1939.28 |
| wall_ms | 10 | 1915.63 | 2008.25 |

## Intent Evaluation

Existing labelled suite `python -m app.eval --k 10` against the seeded
catalogue. 77 cases. Rule-based parser.

| Field | Extraction F1 |
| --- | ---: |
| Hard constraints | 0.9596 |
| Context | 0.9048 |
| Preferences | 0.8918 |
| Desired outcomes | 0.5349 |

Tradeoff F1 is computed inside `score_extraction` but **is not reported
by the current eval CLI**. Not fabricated here.

## Semantic Retrieval Evaluation

Same eval runner. 32 cases with relevance labels. Embedding
`hashing-vectorizer-384`, dimension 384, document `product_semantic.v1`.

| Ranker | Recall@10 | NDCG@10 |
| --- | ---: | ---: |
| astraos | 0.1042 | 0.9823 |
| price | 0.1045 | 0.9515 |
| similarity | 0.1051 | 0.9821 |

Hard-constraint violations in matches: 0.

Recall@10 is low because labels are sparse relative to the eligible set.
NDCG@10 is high because the labelled relevant items that do appear are
ranked near the top. This is the hashing-embedding BEFORE snapshot for
Phase 3.

## Arena Benchmark

**SYNTHETIC BASELINE. NOT REAL-WORLD CONVERSION.**

100 missions, seed `2026`, default strategies unchanged:
`DEFAULT`, `ALWAYS_DISCOUNT`, `CHEAPEST_ELIGIBLE`, `ASTRAOS`.
`SEMANTIC_ONLY` was not added. Bulk transaction simulation is disabled
(offer-selection only; inventory is snapshotted and never consumed), so
`transaction_completion_rate` is 0 for every strategy.

Runtime: 91328.64 ms total, 913.29 ms average per mission.

No-purchase rate: `0.0`.

| Strategy | Selection rate | Contribution / opportunity (¢) | Avg contribution when selected (¢) | Avg intervention (¢) | Avg simulated utility | No-offer | Hard-constraint violation | Policy violation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DEFAULT | 0.00 | 0.00 | — | 0.00 | 0.563668 | 0.00 | 0.33 | 0.00 |
| ALWAYS_DISCOUNT | 0.00 | 0.00 | — | 3734.10 | 0.578858 | 0.00 | 0.33 | 0.00 |
| CHEAPEST_ELIGIBLE | 0.55 | 2600.45 | 4728.09 | 2120.05 | 0.705988 | 0.00 | 0.00 | 0.00 |
| ASTRAOS | 0.45 | 9279.55 | 20621.22 | 2721.00 | 0.704789 | 0.00 | 0.00 | 0.00 |

Primary segment selection rates (ASTRAOS / CHEAPEST_ELIGIBLE):

| Segment | n | ASTRAOS | CHEAPEST_ELIGIBLE |
| --- | ---: | ---: | ---: |
| Budget | 20 | 0.20 | 0.80 |
| Urgent | 20 | 0.00 | 1.00 |
| Assurance | 15 | 1.00 | 0.00 |
| Quality | 15 | 1.00 | 0.00 |
| Balanced | 15 | 0.00 | 1.00 |
| Gaming / studio | 10 | 0.60 | 0.40 |
| Difficult | 5 | 1.00 | 0.00 |

Pairwise CHEAPEST_ELIGIBLE vs ASTRAOS: 0.55 / 0.45 / 0.00.

Confirmatory 500-mission run, same seed and strategies
(`benchmark_id` `5028b451-f536-4f6d-9a6f-5dc9d7d7ef7d`, 451630.54 ms,
903.26 ms/mission, no-purchase 0.0):

| Strategy | Selection rate | Contribution / opportunity (¢) | Avg contribution when selected (¢) | Avg intervention (¢) | Avg simulated utility | Hard-constraint violation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DEFAULT | 0.000 | 0.00 | — | 0.00 | 0.565976 | 0.328 |
| ALWAYS_DISCOUNT | 0.000 | 0.00 | — | 3718.44 | 0.580580 | 0.328 |
| CHEAPEST_ELIGIBLE | 0.594 | 2652.94 | 4466.23 | 2139.37 | 0.703844 | 0.000 |
| ASTRAOS | 0.406 | 8444.48 | 20799.20 | 2688.00 | 0.700164 | 0.000 |

500-mission segment selection (ASTRAOS / CHEAPEST_ELIGIBLE): Budget
0.19/0.81 (n=100), Urgent 0.00/1.00 (n=100), Assurance 1.00/0.00 (n=75),
Quality 1.00/0.00 (n=75), Balanced 0.00/1.00 (n=75), Gaming/studio
0.36/0.64 (n=50), Difficult 0.64/0.36 (n=25).

The 100-mission table above is the official Phase 1 quick baseline. 500
is confirmatory and directionally the same.

## Learning Baseline

**All model data is synthetic.** Trained with the existing script
`scripts/run_learning_report.py`, `LEARNING_TARGET=2500`,
`ASTRAOS_LEARNING_SEED=2026`, on `astraos_baseline`.

Active response-model mode from configuration: **`COLD_START`**.
Training selected `GRADIENT_BOOSTING` as an experimental candidate
artifact only. Default optimisation still uses cold-start utility.

| Dataset | Value |
| --- | --- |
| Size | 2500 |
| Positives | 157 |
| Negatives | 2343 |
| Positive rate | 0.0628 |
| Feature schema | `features.v1` |
| Dataset name | `synthetic.arena.v1` |
| Missions | 157 |
| Leakage violations | none |
| Train / validation / test | 1736 / 367 / 397 |

Held-out synthetic test metrics:

| Model | ROC AUC | PR AUC | Log loss | Brier | F1 | Top-1 | MRR | NDCG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.9431 | 0.3866 | 0.3103 | 0.0899 | 0.5000 | 0.56 | 0.7130 | 0.7835 |
| Gradient Boosting | 0.9892 | 0.8507 | 0.0610 | 0.0197 | 0.6957 | 0.72 | 0.8600 | 0.8967 |
| Cold-start utility (baseline) | 0.7748 | 0.1486 | 1.0394 | 0.4096 | 0.1256 | 0.12 | 0.4494 | 0.5858 |
| Price heuristic | 0.5678 | 0.1486 | 1.1125 | 0.3585 | 0.1164 | 0.52 | 0.5670 | 0.6555 |

Selected training algorithm: `GRADIENT_BOOSTING` (experimental artifact).
This does **not** change `RESPONSE_MODEL_MODE`.

## Agent Interface

REST smoke on `/api/v1/agent/*` (no internal service imports):

| Step | Result |
| --- | --- |
| `GET /capabilities` | pass |
| `POST /offers/request` | `PROPOSED` |
| `GET /offers/{id}` | `PROPOSED` |
| `POST /offers/counter` | `COUNTERED` |
| `POST /offers/accept` | `CONFIRMED` |
| `GET /orders/{ref}` | `AST-2026-000002` |
| `GET /transactions/{id}` | pass |

MCP stdio adapter: process starts, answers `initialize` and `tools/list`
with five tools (`astraos_request_offer`, `inspect`, `counter`, `accept`,
`get_order`). Optional. REST remains the guaranteed surface. MCP
behaviour was not modified.

## Safety / Failure Tests

Existing tests only. No new safety features.

| Case | Tests | Result |
| --- | --- | --- |
| A. Stock → 0 after proposal | `test_out_of_stock_revalidation`, `test_stock_failure_creates_no_order` | PASS |
| B. Margin policy tightened after proposal | `test_policy_change_can_block_acceptance`, `test_policy_change_fails_revalidation` | PASS |
| C. Expired proposal | `test_expired_proposal_fails_before_reserve` | PASS |
| D. Duplicate accept / idempotency | `test_accept_is_idempotent`, `test_idempotent_retry` | PASS |
| E. Last-unit race | `test_concurrent_last_unit`, `test_last_unit_is_consumed_once` | PASS |
| F. Prompt injection (“ignore policy / sell for A$1”) | `test_prompt_injection_cannot_force_one_dollar`, `test_prompt_injection_does_not_waive_policy` | PASS |

## Known Demo Components

- Rule-based parser is the default (`INTENT_PARSER_MODE=rule_based`, `rule_based.v2`)
- LLM parser exists but is optional; `/ready` reports `llm_unavailable` without a key
- Embedding provider is local hashing (`hashing-vectorizer-384`, dim 384)
- Merchant catalogue and inventory are synthetic seed data
- Buyer utility is a transparent cold-start simulation
- Arena outcomes are synthetic, not observed conversion
- Learned response model is experimental and trained on synthetic Arena labels
- Transactions execute locally; payment is `NOT_REQUIRED_FOR_DEMO`
- Catalogue is headphones only

## UI Baseline

Routes (no redesign in this phase):

| Surface | Route |
| --- | --- |
| LIVE | `/` |
| ARENA | `/arena` |
| LEARN | `/learn` |
| Merchant Data | `/catalogue` |
| Merchant Rules | drawer (header), not a route |

Manually verified at 1440×900 against the running Next.js app:

- Hero LIVE flow renders (intent, qualify, match, construct, optimise)
- Match → Offer distinction and DecisionBridge render
- Pareto view renders
- Negotiation protocol exchange renders; counter and accept work
- Transaction pipeline renders (`AST-2026-000002` on the demo API)
- Arena duel renders
- Arena benchmark view renders (loads latest completed run)
- LEARN renders (empty until a dataset exists)

Known UX issues (not fixed):

- Frontend lint errors/warnings listed above
- LEARN shows 0 interactions on a cold database
- Catalogue first paint briefly shows empty counts
- MATCH + DecisionBridge is tall at 1440×900
- Inspect Decision remains on-demand JSON
- `/ready` degraded banner is visible in LIVE (`learned_model_unavailable`, `llm_unavailable`)

## Realification Targets

Do not implement these in Phase 1.

- Phase 2 — Real Intent Intelligence
- Phase 3 — Real Semantic Embeddings
- Phase 4 — External Buyer Agent
- Phase 5 — Configurable Merchant Objective
- Phase 6 — Merchant Data Ingestion
- Phase 7 — Hero Evidence Realification
- Phase 8 — Second Category
- Phase 9 — Re-evaluation
- Phase 10 — UI Storytelling
- Phase 11 — Arena Ablation
- Phase 12 — Reliability
- Phase 13 — Final Evidence Package

## Bugs fixed in Phase 1

None. Existing frontend lint errors were left unchanged.

## Reproduction commands

Verified against the Makefile and running code. Defaults:
`POSTGRES_HOST=localhost`, `POSTGRES_USER=astraos`,
`POSTGRES_PASSWORD=astraos`, `ASTRAOS_SEED=2026`.

Clean DB (this capture used a dedicated `astraos_baseline` database):

```bash
# Postgres must already be running (make up, or local Postgres 16)
createdb -h localhost -U astraos astraos_baseline   # or use POSTGRES_DB=astraos
export POSTGRES_HOST=localhost POSTGRES_DB=astraos_baseline ASTRAOS_SEED=2026
```

Migration:

```bash
cd apps/api && .venv/bin/python -m alembic upgrade head
# or: make migrate
```

Seed:

```bash
cd apps/api && .venv/bin/python -m app.seed
# or: make seed
# rerun is safe (idempotent upsert)
```

Embedding / index build:

```bash
cd apps/api && .venv/bin/python -m app.eval.index
# or: make embeddings
```

Backend tests / lint / types:

```bash
make test
make lint
```

Frontend:

```bash
cd apps/web
npm test
npm run lint    # currently 2 errors / 2 warnings
npm run build
```

Hero run (LIVE path):

```bash
# API must be up on the target DB
export ASTRAOS_BASELINE_API_URL=http://127.0.0.1:8001
cd apps/api && .venv/bin/python scripts/collect_baseline.py
```

CLI hero (agent gateway, not the LIVE workbench path):

```bash
make demo-hero
```

Arena baseline:

```bash
curl -sS -X POST http://127.0.0.1:8001/api/v1/arena/benchmarks \
  -H 'Content-Type: application/json' \
  -d '{"mission_count":100,"seed":2026,"persist_missions":false}'
```

Learning baseline (synthetic; does not change `RESPONSE_MODEL_MODE`):

```bash
cd apps/api
LEARNING_TARGET=2500 ASTRAOS_LEARNING_SEED=2026 POSTGRES_DB=astraos_baseline \
  .venv/bin/python scripts/run_learning_report.py
```

Agent API smoke is included in `scripts/collect_baseline.py`.

Intent + retrieval eval:

```bash
cd apps/api && .venv/bin/python -m app.eval --k 10
# or: make eval
```

Demo reset (destructive remigrate + seed 2026):

```bash
make reset-demo
```

Lightweight identity + eval:

```bash
make baseline
```

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

**Stage 2 — Intent Interpretation + Deterministic Eligibility**

- Stage 0 — Scaffold — COMPLETE
- Stage 1 — Domain model and merchant data — COMPLETE
- Stage 2 — Intent interpretation + deterministic eligibility — COMPLETE

The LIVE page now accepts a natural-language shopper request, parses it into a
`ShoppingIntent`, and deterministically marks every active SKU as eligible,
rejected, or uncertain.

**Semantic similarity never overrides mandatory eligibility.**

**Missing evidence is UNKNOWN, not SATISFIED.**

## What Stage 2 does

```
AI shopping intent
  → structured ShoppingIntent
  → deterministic condition evaluation
  → eligible / rejected / uncertain products
```

Eligibility is not relevance. Soft preferences (comfort, reliability, price
sensitivity) are stored as interpretation metadata only. They never admit or
exclude a SKU.

A product is eligible only when every mandatory condition is `SATISFIED`.
`VIOLATED` and `UNKNOWN` both block eligibility. LLMs may interpret language.
LLMs must not decide product eligibility.

## ShoppingIntent

Internal typed model:

- `raw_text`, `category`
- `hard_constraints` — field, operator, value, unit, `source_phrase`
- `soft_preferences` — field, direction, importance 0..1
- `context_tags` — stored only (`long_haul_travel`, commuting, …)
- `ambiguities` — unsupported phrases are recorded, never dropped
- `parser_type`, `parser_version`, `status`

Statuses: `READY`, `NEEDS_CLARIFICATION`, `UNSUPPORTED`.

If a buyer says “must look luxurious” or “no animal leather” and the catalogue
has no supported field, AstraOS records an ambiguity. Mandatory unsupported
requirements make every SKU `UNKNOWN` for that condition. Absence of a material
attribute is not treated as “no leather”.

## Parsers

`IntentParser` is a protocol. Implementations:

- `RuleBasedIntentParser` — deterministic phrase matcher for demos, tests, and
  fallback. No API key required.
- `LLMIntentParser` — optional schema-constrained structured output, allow-listed
  fields/operators, one validation retry, then rule-based fallback.

`INTENT_PARSER_MODE=rule_based` (default) or `llm`. If LLM credentials are
missing, the application keeps working in rule-based mode. Tests never call a
live model.

## Normalisation

Downstream eligibility never sees natural-language variants.

| Phrase | Result |
| --- | --- |
| `under $350` / `A$350` / `AUD 350` | `price LT 35000` AUD cents |
| `$350 or less` / `up to $350` | `price LTE 35000` |
| `at least 30 hours battery` | `battery_hours GTE 30` |
| `more than 30 hours battery` | `battery_hours GT 30` |
| `delivered today` / `same day` | `delivery_days LTE 0` |
| `tomorrow` | `delivery_days LTE 1` |
| `within 2 days` | `delivery_days LTE 2` |
| `0.25kg` | `250` grams |
| `noise cancelling` / `ANC` | `anc EQ true` |

**under** means strictly less than (`LT`). **up to** / **or less** means `LTE`.

## Eligibility

Every hard condition resolves to exactly one of:

- `SATISFIED`
- `VIOLATED`
- `UNKNOWN`

Eligible iff `violated_count == 0` and `unknown_count == 0`.

Field lookup goes through a registry, not scattered `if field == "anc"` checks:

| Field | Source |
| --- | --- |
| `price` | `ProductVariant.base_price_cents` |
| `anc`, `battery_hours`, `weight_g`, `foldable`, `wireless`, `microphone` | variant `attributes` JSON |
| `brand`, `category` | `Product` |
| `in_stock` | `units_available - units_reserved` |
| `delivery_days` / same-day | `VariantDeliveryOption` + `DeliveryOption` |

Missing or null attributes are `UNKNOWN`, never false. Missing inventory is
`UNKNOWN`, not zero stock. Delivery is evaluated from fulfilment rows, never
from product attributes.

- Same-day `SATISFIED` when an available option has `delivery_days <= 0`
- `VIOLATED` when delivery rows exist but none meet the limit
- `UNKNOWN` when no usable delivery data exists

If the only supporting `AttributeEvidence` for an attribute-backed fact is
expired, the condition is `UNKNOWN` with reason `STALE_EVIDENCE`. Stock and
delivery use their own operational rows.

Operators are explicit functions (`EQ`, `NE`, `LT`, `LTE`, `GT`, `GTE`, `IN`,
`NOT_IN`). No `eval()`, no generated expressions.

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
| POST | `/api/v1/intent/qualify` | Parse + qualify the catalogue |
| GET | `/api/v1/intent/qualification/{run_id}` | Full run / paginated traces |
| GET | `/api/v1/intent/qualification/{run_id}/variants/{variant_id}` | One condition trace |

`POST /api/v1/intent/qualify` body:

```json
{ "intent": "I need noise-cancelling headphones under A$350...", "parser_mode": "rule_based" }
```

Response includes structured intent, eligible / uncertain / rejected previews,
counts, and `parse_ms` / `eligibility_ms` / `total_ms`. Rejected lists may be
truncated in the POST body; the GET endpoints return the complete trace.

Qualification runs are persisted (`QualificationRun`,
`QualificationVariantResult`). Offer candidates and outcome-learning tables are
not created in this stage.

## Frontend

`/` is the first LIVE experience:

- Left: shopper request, example intent, parser mode, **QUALIFY REQUEST**
- Center: structured intent + per-SKU condition rows
- Right: counts and the future process rail (Understand / Qualify complete;
  Construct, Optimise, Learn not started; Prove partial)

Click a condition to open a proof drawer (expected, observed, source,
verification, freshness). This is not a search-results page.

Catalogue inspector remains at `/catalogue`.

## Architecture

```
Routes → Services → Repositories / Decision modules → Database
```

Decision logic lives under `apps/api/app/decision/intent/` and
`apps/api/app/decision/eligibility/`, not in route handlers.

Money remains integer cents. The Stage 2 MVP scans all active variants in the
selected category. That is acceptable for a few hundred SKUs. This is not
production-scale retrieval.

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
- **Stage 3 — Semantic retrieval + product ranking**
- **Stage 4 — Offer construction and merchant economics**
- **Stage 5 — Pareto optimisation and buyer utility**
- **Stage 6 — LIVE decision UI**
- **Stage 7 — Agent Arena and benchmark simulator**
- **Stage 8 — Intent → Offer → Outcome learning**
- **Stage 9 — Protocol adapters and demo hardening**

Stage 2 does not implement embeddings, offer construction, discounts, Pareto
filtering, buyer utility, P(win), Agent Arena, or learning.

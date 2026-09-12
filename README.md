# AstraOS

Merchant-side offer intelligence for AI commerce.

**Product ≠ Offer.**

AstraOS is a merchant-side decision engine for agentic commerce. Later stages
will take AI shopping intent, qualify products, construct commercial offers,
enforce merchant policies, optimise those offers, return proof-backed
machine-readable responses, and learn from Intent → Offer → Outcome data.

This repository is the technical foundation for UAVS Hackathon 2026.

## Current status

**Stage 1 — Domain Model and Merchant Data**

Stage 0 scaffold is complete. Stage 1 adds PostgreSQL domain tables, Alembic
migrations, a deterministic synthetic headphone catalogue, catalogue read APIs,
a merchant policy store, and a merchant-data inspector.

The decision engine is **not implemented yet**. No intent parsing, eligibility,
retrieval, offer construction, Pareto optimisation, buyer utility, Agent Arena,
or learning code exists.

## Architecture

```
Routes → Services → Repositories / Decision modules → Database
```

Business logic does not live in API route handlers. Decision packages under
`apps/api/app/decision/` remain empty placeholders.

The API uses async SQLAlchemy 2 with PostgreSQL via psycopg.

## Database schema

Money is stored as integer cents. Currency is an ISO code (`AUD` in the seed).
Missing product facts are stored as absent/null JSON keys, not zeros.

```
Merchant
  └── MerchantPolicy

Product
  └── ProductVariant
       ├── InventoryRecord
       ├── VariantDeliveryOption → DeliveryOption
       ├── VariantWarrantyOption → WarrantyOption
       ├── VariantBundleOption → BundleOption
       ├── VariantReturnPolicy → ReturnPolicy
       └── AttributeEvidence → DataSource
```

Merchant economics fields:

- Variant: `base_price_cents`, `cogs_cents`
- Delivery / warranty / bundle: `merchant_cost_cents` vs customer charge/price
- Policy: `minimum_margin_rate`, `maximum_discount_rate`, subsidy flags

Provenance:

- `DataSource` records where a fact came from (`MANUFACTURER`, `MERCHANT_PIM`, …)
- `AttributeEvidence` stores the observed value, verification status, and
  optional `expires_at`. Stale evidence is representable. No cryptographic
  signing in this stage.

## Synthetic seed

```bash
make seed
```

- Deterministic via `ASTRAOS_SEED=2026`
- Fictional brands only (Aurora Audio, Nimbus, Vanta, …)
- Category: `headphones`
- Target: 100–160 products, 300–400 SKUs
- Upserts by stable UUID5 keys, so repeats do not duplicate rows
- About 5–10% of SKUs omit attributes for later UNKNOWN handling
- About 2–5% of evidence is deliberately stale
- Mix of out-of-stock, low-stock, same-day, weak-margin, and expensive SKUs

`make reset-db` is destructive: it remigrates the configured database from the
Stage 0 baseline and reseeds.

## APIs

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/api/v1/catalogue/products` | List products (`brand`, `category`, `active_only`, `limit`, `offset`) |
| GET | `/api/v1/catalogue/products/{id}` | Product + variants + merchant attachments |
| GET | `/api/v1/catalogue/variants/{id}` | SKU detail |
| GET | `/api/v1/catalogue/stats` | Catalogue counters |
| GET | `/api/v1/merchant/policy` | Active policy |
| PATCH | `/api/v1/merchant/policy` | Update stored policy bounds/flags |

Policy PATCH accepts `minimum_margin_rate`, `maximum_discount_rate`, and the
subsidy/upgrade toggles. It does not evaluate offers.

## Frontend

- `/` LIVE shell and API status
- `/catalogue` merchant-data inspector
- `/catalogue/[productId]` product/SKU detail
- Header **RULES** drawer edits merchant policy

## Local prerequisites

- Docker and Docker Compose (recommended), or
- Python 3.12, Node.js 22+, PostgreSQL 16

Host development defaults to `POSTGRES_HOST=localhost` and user `astraos`.

```bash
# one-time local role/databases if you are not using Docker
# create role astraos with password astraos
# create databases astraos and astraos_test
```

## Docker setup

```bash
cp .env.example .env
make up
```

## Development setup

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# from repo root
make migrate
make seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

## Available commands

| Command | Purpose |
| --- | --- |
| `make up` | Build and start Compose services |
| `make down` | Stop Compose services |
| `make logs` | Follow Compose logs |
| `make test` | Run API pytest suite against `astraos_test` |
| `make lint` | Run ruff and mypy |
| `make migrate` | Apply Alembic migrations |
| `make migration name="..."` | Autogenerate a new Alembic revision |
| `make seed` | Upsert the synthetic merchant catalogue |
| `make reset-db` | Destructive remigrate + seed |

## Service URLs

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Catalogue | http://localhost:3000/catalogue |
| Backend | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| PostgreSQL | `localhost:5432` locally, or Docker `db:5432` |

## Roadmap

- **Stage 0 — Scaffold** — COMPLETE
- **Stage 1 — Domain model and merchant data** — COMPLETE
- **Stage 2 — Intent and eligibility**
- **Stage 3 — Product retrieval**
- **Stage 4 — Offer construction and merchant economics**
- **Stage 5 — Pareto optimisation and buyer utility**
- **Stage 6 — LIVE decision UI**
- **Stage 7 — Agent Arena and benchmark simulator**
- **Stage 8 — Intent → Offer → Outcome learning**
- **Stage 9 — Protocol adapters and demo hardening**

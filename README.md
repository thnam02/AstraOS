# AstraOS

Merchant-side offer intelligence for AI commerce.

**Product ≠ Offer.**

AstraOS is a merchant-side decision engine that optimises what a retailer
should offer to autonomous AI shoppers.

This repository is the technical foundation for UAVS Hackathon 2026.

## What is AstraOS?

Traditional e-commerce is designed for people browsing pages. AstraOS is
designed for the **Buyer Agent**.

It takes shopping intent, qualifies products against hard constraints,
constructs commercial offers, enforces merchant policy, and selects a
Pareto-efficient merchant response. It then negotiates with a Buyer Agent
using structured actions. After acceptance it revalidates live merchant
state, reserves inventory, and creates a local order snapshot.

It is not a payment processor, OMS, ERP, chatbot, pricing engine, or
conversion study.

**LLMs interpret language. Deterministic AstraOS services control all
commercial terms.**

The Buyer Agent is an external evaluator/client. It is not the product.

## Core thesis

A product is not an offer. The unit of competition in agentic commerce is
the entire commercial configuration: product, price, delivery, warranty,
bundle, and returns — under merchant policy.

## Architecture

```
EXTERNAL BUYER AGENT
        │
        ├── REST  /api/v1/agent/*
        └── MCP   python -m app.agent.mcp_server
        ▼
AGENT COMMERCE ADAPTER   (translation only)
        ▼
CANONICAL ASTRAOS SERVICES
Intent → Qualification → Semantic Matching → Offer Construction
  → Economics / Policy → Pareto Optimisation → Negotiation → Transaction
        ▼
MACHINE-READABLE RESPONSE
```

The protocol adapter contains no pricing, eligibility, matching, Pareto,
or policy logic.

See [docs/architecture.md](docs/architecture.md).

## Tech stack

- API: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL 16
- Matching: local hashing embeddings (no hosted model required)
- Frontend: Next.js, TypeScript
- Demo: Docker Compose or local processes

## Run locally

```bash
cp .env.example .env
make up                 # docker compose up --build
```

Or without Docker (PostgreSQL 16 required):

```bash
cp .env.example .env
# set POSTGRES_HOST=localhost
make migrate
make seed
make embeddings
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd apps/web && npm run dev
```

| Surface | URL |
| --- | --- |
| LIVE | http://localhost:3000 |
| ARENA | http://localhost:3000/arena |
| LEARN | http://localhost:3000/learn |
| Merchant data | http://localhost:3000/catalogue |
| OpenAPI | http://localhost:8000/docs |
| Agent capabilities | http://localhost:8000/api/v1/agent/capabilities |

## Demo mode

`ASTRAOS_DEMO_MODE=true` uses the same business logic with deterministic
seed `2026`. It does not hardcode winners, Pareto output, or orders.

```bash
make reset-demo         # remigrate + seed 2026
python -m app.cli demo hero
python -m app.cli demo hero --stop-before-accept
```

Operator script: [docs/demo.md](docs/demo.md).
Judge Q&A: [docs/judge_qa.md](docs/judge_qa.md).

## Agent interface

Guaranteed demo interface: REST `/api/v1/agent/*`

| Operation | Endpoint |
| --- | --- |
| Discover | `GET /api/v1/agent/capabilities` |
| Request offer | `POST /api/v1/agent/offers/request` |
| Inspect | `GET /api/v1/agent/offers/{proposal_id}` |
| Counter | `POST /api/v1/agent/offers/counter` |
| Accept | `POST /api/v1/agent/offers/accept` |
| Order | `GET /api/v1/agent/orders/{ref}` |

Optional MCP stdio adapter (calls REST only):

```bash
python -m app.agent.mcp_server
```

Existing Stage 2–9 REST routes remain for the frontend and debugging.

## Capabilities

- Stage 0 — Scaffold — COMPLETE
- Stage 1 — Merchant data + product truth — COMPLETE
- Stage 2 — Intent + deterministic eligibility — COMPLETE
- Stage 3 — Deep intent + semantic matching — COMPLETE
- Stage 4 — Offer construction + bundling — COMPLETE
- Stage 5 — Economics + simulated buyer utility + Pareto — COMPLETE
- Stage 6 — B2A negotiation — COMPLETE
- Stage 7 — Proposal acceptance + transaction loop — COMPLETE
- Stage 8 — Agent Arena + synthetic benchmark — COMPLETE
- Stage 9 — Intent → Offer → Outcome learning — COMPLETE
- Stage 10 — Agent protocol adapter + demo hardening — COMPLETE

**Simulated Buyer Utility** is a transparent cold-start score. It is not
P(win) or purchase probability.

**Semantic Fit** ranks eligible products only. It never overrides a hard
constraint.

**Synthetic Response Score** is trained on simulated Arena outcomes. It
is experimental and not a real conversion model.

## Synthetic-data disclaimers

Arena and LEARN use simulated buyer-agent outcomes. Results do not
represent observed real-world conversion uplift, ChatGPT/Gemini purchase
behaviour, or production sales impact.

## Limitations

- Headphone catalogue only
- Local simulated payment (`NOT_REQUIRED_FOR_DEMO`)
- No warehouse logistics
- Learned model is experimental / synthetic
- MCP is optional; REST is the guaranteed interface
- LLM parser is optional; rule-based fallback is default

## Future production path

Observed B2A outcomes → periodic retraining → calibrated response model
→ A/B evaluation. No online bandit or reinforcement learning in this
repository.

## Commands

| Command | Purpose |
| --- | --- |
| `make up` | Compose build + start |
| `make migrate` | Alembic upgrade head |
| `make seed` | Deterministic catalogue seed 2026 |
| `make embeddings` | Refresh cached product embeddings |
| `make reset-demo` | Destructive remigrate + seed |
| `make test` | pytest |
| `make lint` | ruff + mypy |
| `make demo-hero` | Hero request → counter → accept |

Internet is not required for the core deterministic flow, Arena, LEARN
inspection, or transaction simulation. Optional LLM parsing needs
`INTENT_PARSER_MODE=llm` and an API key.

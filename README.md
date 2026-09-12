# AstraOS

Merchant-side offer intelligence for AI commerce.

**Product ≠ Offer.**

AstraOS is a merchant-side decision engine for agentic commerce. It will
eventually take AI shopping intent, qualify products, construct commercial
offers, enforce merchant policies, optimise those offers, return proof-backed
machine-readable responses, and learn from Intent → Offer → Outcome data.

This repository is the technical foundation for UAVS Hackathon 2026.

## Current status

**Stage 0 — Project Scaffold**

The monorepo, FastAPI service, Next.js shell, PostgreSQL connection,
Alembic, Docker Compose, and tooling are in place.

The decision engine, Pareto optimisation, buyer utility, semantic retrieval,
LLM integration, Agent Arena, and learning are **not implemented yet**.

## Architecture

Request flow for future stages:

```
Routes → Services → Repositories / Decision modules → Database
```

Business logic does not live in API route handlers.

Decision modules will live under `apps/api/app/decision/`:

- `intent`
- `eligibility`
- `retrieval`
- `offers`
- `policies`
- `pareto`
- `utility`
- `economics`

The API uses async SQLAlchemy 2 with PostgreSQL via psycopg.

The web app is a Next.js App Router shell with LIVE, ARENA, and LEARN
routes. Only LIVE talks to the backend today (`GET /health`).

## Repository structure

```
astraos/
├── apps/
│   ├── api/                 FastAPI service
│   └── web/                 Next.js 16 frontend
├── packages/
│   └── fixtures/            Reserved for later-stage sample data
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Local prerequisites

- Docker and Docker Compose (recommended)
- Or, for host development:
  - Python 3.12
  - Node.js 22+
  - PostgreSQL 16

## Docker setup

```bash
cp .env.example .env
make up
```

This starts PostgreSQL, the API, and the web app. The API retries
PostgreSQL until it is ready.

## Development setup

### Backend

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

For host-run Alembic or the API, set `POSTGRES_HOST=localhost` in `.env`.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

The browser calls `http://localhost:8000/health` through the shared API client.

## Available commands

| Command | Purpose |
| --- | --- |
| `make up` | Build and start all Compose services |
| `make down` | Stop Compose services |
| `make logs` | Follow Compose logs |
| `make test` | Run API pytest suite |
| `make lint` | Run ruff and mypy |
| `make migrate` | Apply Alembic migrations |
| `make migration name="..."` | Autogenerate a new Alembic revision |
| `make seed` | Placeholder until Stage 1 |

## Service URLs

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| OpenAPI / Swagger | http://localhost:8000/docs |
| PostgreSQL | internal Docker network (`db:5432`), also published on `localhost:5432` |

## Roadmap

- **Stage 0 — Scaffold** (current)
- **Stage 1 — Domain model and merchant data**
- **Stage 2 — Intent and eligibility**
- **Stage 3 — Product retrieval**
- **Stage 4 — Offer construction and merchant economics**
- **Stage 5 — Pareto optimisation and buyer utility**
- **Stage 6 — LIVE decision UI**
- **Stage 7 — Agent Arena and benchmark simulator**
- **Stage 8 — Intent → Offer → Outcome learning**
- **Stage 9 — Protocol adapters and demo hardening**

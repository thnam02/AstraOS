# AstraOS

AstraOS is a merchant-side AI agent for B2A (Business-to-Agent) commerce.

It lets autonomous buyer agents send shopping requests directly to a merchant. AstraOS then:

1. Understands buyer intent
2. Checks hard constraints
3. Matches suitable products
4. Builds complete commercial offers
5. Optimises the merchant response
6. Negotiates with the buyer agent
7. Completes the transaction through an API

AstraOS is **not** a consumer shopping assistant. It represents the **merchant** in agent-to-agent commerce.

Built for UAVS Hackathon 2026: *The B2A Shift: Adapting Retail for AI Shopping Agents*.

---

## How it works

```text
Buyer Agent
     ↓
   AstraOS
     ↓
Understand → Qualify → Match → Construct → Optimise → Negotiate → Transact
```

A complete offer can include:

**Product + Price + Delivery + Warranty + Bundle + Returns**

LLMs help interpret language. Hard buyer constraints and merchant policy are enforced deterministically. AstraOS only acts inside merchant-approved boundaries.

---

## Quick start (Docker)

**Requirements:** Docker and Docker Compose.

```bash
docker --version
docker compose version
```

```bash
git clone https://github.com/thnam02/AstraOS.git
cd AstraOS
cp .env.example .env
docker compose up --build
```

Background:

```bash
docker compose up --build -d
```

### Local URLs

| Surface | URL |
| --- | --- |
| Frontend (LIVE) | http://localhost:3000 |
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Ready | http://localhost:8000/ready |

Compose services: `db` (Postgres 16), `api`, `web`.

### Environment

Copy `.env.example` → `.env`. Important defaults:

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | Frontend → API base URL (default `http://localhost:8000`) |
| `FRONTEND_URL` | CORS / frontend origin (default `http://localhost:3000`) |
| `API_PORT` | Host port for the API (default `8000`) |
| `POSTGRES_*` | Database name/user/password/host/port |
| `INTENT_PARSER_MODE` | `llm` (default) or `rule_based` |
| `LLM_API_KEY` / `OPENAI_API_KEY` | Optional; without a key, intent parsing falls back to rules |
| `RESPONSE_MODEL_MODE` | Default `COLD_START` (production-safe LIVE path) |
| `ASTRAOS_DEMO_MODE` | Demo catalogue / deterministic seed behaviour |
| `SEMANTIC_EMBEDDING_*` | Embedding provider/model; hashing fallback if model missing |

Do not invent extra vars — see `.env.example`.

### Database / seed

On API container start, `apps/api/docker-entrypoint.sh` runs:

1. `alembic upgrade head`
2. Demo catalogue seed **if the catalogue is empty**

So a fresh `docker compose up --build` migrates and seeds automatically.

Manual (host / Makefile), from repo root with API deps available:

```bash
make migrate   # cd apps/api && alembic upgrade head
make seed      # cd apps/api && python -m app.seed
```

Inside a running API container:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed
```

---

## Using AstraOS

### LIVE — `/`

Merchant operator view of **one** buyer-agent request end-to-end.

```text
Understand → Qualify → Match → Construct → Optimise → Negotiate → Transact
```

Stages are a **decision trace**, not steps a human performs manually. LIVE uses the transparent cold-start decision path (`RESPONSE_MODEL_MODE=COLD_START`). Experimental learned models do **not** control LIVE.

### INTEGRATIONS — `/integrations`

How external machines connect to AstraOS:

- Agent API status / readiness
- Agent capabilities
- REST Agent API
- Optional MCP adapter (stdio; calls the same REST surface)
- Recent agent activity
- Exchange Inspector
- API reference + link to OpenAPI

### EVALUATE — `/arena`

Compares merchant strategies under controlled conditions.

Default strategies: **DEFAULT**, **ALWAYS_DISCOUNT**, **SEMANTIC_ONLY**, **ASTRAOS**.

Same buyer · same catalogue · same inventory · same merchant policy · same buyer model — only the strategy changes.

Evaluation uses **simulated** buyer behaviour. It is not real production sales uplift.

### LEARN — `/learn`

Explores outcome-based **experimental** response models:

- Synthetic outcome generation
- Train / validation / test splits
- Grouped split by mission (no mission leakage across splits)
- Experimental learned response model
- Held-out evaluation vs cold-start
- Shadow / experimental use only

**LIVE still uses the production-safe cold-start model.** Learned models do not drive LIVE decisions.

### DATA — `/catalogue`

Merchant truth: products, variants, prices, inventory signals, and feed ingestion status.

### RULES — header **Rules** drawer

Merchant authority: minimum margin, maximum discount, delivery / warranty / bundle / returns toggles, and objective (Growth / Balanced / Margin).

AstraOS only proposes offers inside these guardrails.

---

## Agent API (external buyer agents)

Public machine interface under `/api/v1/agent/*`:

| Method | Path |
| --- | --- |
| `GET` | `/api/v1/agent/capabilities` |
| `POST` | `/api/v1/agent/offers/request` |
| `GET` | `/api/v1/agent/offers/{proposal_id}` |
| `POST` | `/api/v1/agent/offers/counter` |
| `POST` | `/api/v1/agent/offers/accept` |
| `GET` | `/api/v1/agent/orders/{ref}` |
| `GET` | `/api/v1/agent/transactions/{transaction_id}` |
| `GET` | `/api/v1/agent/activity` |

Interactive docs: http://localhost:8000/docs

Optional MCP stdio adapter (API must already be running):

```bash
cd apps/api && python -m app.agent.mcp_server
```

A separate sample buyer client lives in `apps/buyer-agent` (`make buyer-demo-deterministic`).

---

## Project structure

```text
AstraOS
├── apps/
│   ├── api/           # FastAPI backend
│   ├── web/           # Next.js frontend
│   └── buyer-agent/   # External buyer-agent client (not the merchant UI)
├── docs/              # Architecture, demo, reliability notes
├── examples/          # Sample merchant feeds
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 |
| AI / decision | LLM intent parsing (optional), semantic embeddings, deterministic eligibility / policy / economics |

---

## Useful Docker commands

```bash
docker compose up --build      # start (foreground)
docker compose up --build -d   # start (background)
docker compose ps
docker compose logs -f
docker compose logs -f api
docker compose logs -f web
docker compose logs -f db
docker compose down
```

Makefile shortcuts: `make up`, `make down`, `make logs`, `make migrate`, `make seed`, `make test`.

---

## Troubleshooting

**Port already in use**

```bash
lsof -i :3000
lsof -i :8000
lsof -i :5432
```

Compose maps Postgres to `${POSTGRES_PORT:-5432}`. If local Postgres already uses 5432, set e.g. `POSTGRES_PORT=5433` in `.env`.

**Database / API not ready**

```bash
docker compose ps
docker compose logs -f db
docker compose logs -f api
curl -sS http://localhost:8000/health
curl -sS http://localhost:8000/ready
curl -sS http://localhost:8000/api/v1/agent/capabilities
```

`/ready` may report **degraded** when embeddings fall back to hashing (model not downloaded). Required checks can still pass.

**Frontend cannot reach API**

Web uses `NEXT_PUBLIC_API_URL` (see `.env.example` and `apps/web/lib/config.ts`). With Compose, rebuild web after changing it — the value is baked at image build time:

```bash
docker compose up --build -d web
```

**Empty catalogue**

```bash
docker compose exec api python -m app.seed
# or: make seed
```

---

## Important notes

- AstraOS is merchant-side; the Buyer Agent is an external machine customer.
- LLMs interpret language; they do not control merchant economics.
- Hard constraints and merchant policy are enforced deterministically.
- Arena / LEARN use synthetic outcomes — not real production conversion data.
- Experimental learned models do **not** currently control LIVE decisions.

---

## Hackathon context

Built for **UAVS Hackathon 2026**: *The B2A Shift: Adapting Retail for AI Shopping Agents*.

AstraOS explores how retailers move from passive catalogues to autonomous merchant agents that understand, negotiate with, and sell directly to AI buyers.

---

## Further documentation

| Doc | Topic |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | System overview |
| [docs/demo.md](docs/demo.md) | Demo operator script |
| [docs/judge_qa.md](docs/judge_qa.md) | Judge Q&A |
| [docs/deploy-railway.md](docs/deploy-railway.md) | Railway deploy |
| [docs/reliability-matrix.md](docs/reliability-matrix.md) | Reliability notes |
| [docs/realification-baseline.md](docs/realification-baseline.md) | Reproducible baseline |

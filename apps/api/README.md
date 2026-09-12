# AstraOS API

FastAPI service for the merchant-side decision engine.

The public Buyer Agent interface is `/api/v1/agent/*`. It translates onto
existing Stage 2–7 services. It does not price or optimise.

Optional MCP: `python -m app.agent.mcp_server` (calls REST).

```bash
make migrate
make seed
make embeddings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `GET /health` — liveness
- `GET /ready` — database, policy, seed, embeddings, adapter
- `GET /api/v1/agent/capabilities`
- `POST /api/v1/agent/offers/request`
- `POST /api/v1/agent/offers/counter`
- `POST /api/v1/agent/offers/accept`

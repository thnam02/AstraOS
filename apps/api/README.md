# AstraOS API

FastAPI service for the merchant-side decision engine.

The public Buyer Agent interface is `/api/v1/agent/*`. It translates onto
existing Stage 2–7 services. It does not price or optimise.

Optional MCP: `python -m app.agent.mcp_server` (calls REST).

```bash
make migrate
make seed
make embeddings-model   # caches BAAI/bge-small-en-v1.5; optional extra [semantic]
make embeddings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `GET /health` — liveness
- `GET /ready` — database, policy, seed, semantic retrieval, intent parser, adapter

Demo default parser is `INTENT_PARSER_MODE=llm` with rule-based fallback.
CI forces `rule_based` and `SEMANTIC_EMBEDDING_PROVIDER=hashing`.
Intent benchmark: `python -m app.eval.intent_benchmark`.
Retrieval benchmark: `python -m app.eval.retrieval`.
The default Docker image does not install torch; without a cached
sentence-transformer the API uses hashing and reports the fallback.
Merchant configuration:

- `GET /api/v1/merchant/policy` — hard guardrails
- `PATCH /api/v1/merchant/policy`
- `GET /api/v1/merchant/objective` — Growth / Balanced / Margin
- `PATCH /api/v1/merchant/objective`
- `POST /api/v1/optimisation/runs/{run_id}/reselect` — cheap frontier reselection

Objective evaluation: `python -m app.eval.merchant_objective`.

- `GET /api/v1/agent/capabilities`
- `POST /api/v1/agent/offers/request`
- `GET /api/v1/agent/offers/{proposal_id}`
- `POST /api/v1/agent/offers/counter`
- `POST /api/v1/agent/offers/accept`
- `GET /api/v1/agent/orders/{ref}`
- `GET /api/v1/agent/transactions/{transaction_id}`

The Buyer Agent is not this package. It lives in `apps/buyer-agent`
and calls these endpoints over HTTP.

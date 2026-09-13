# Competition-day demo recovery

Keep this short. Reset first whenever state is dirty.

## LLM unavailable

Symptom: `/ready` includes `llm_unavailable`, or LIVE shows parser fallback.

Action:

```bash
# Continue. Rule-based fallback is automatic and explicit
# (timeout, 500, auth, or empty LLM extraction).
# Optional: force it
export INTENT_PARSER_MODE=rule_based
```

Do not stop the demo. Say the merchant engine stayed deterministic.

## Buyer Agent LLM unavailable

```bash
make buyer-demo-deterministic
```

REST `/api/v1/agent/*` is unchanged.

## Semantic index mismatch / model missing

Symptom: `/ready` degraded (`embeddings_stale_model`, `embeddings_partial_index`, `semantic_model_unavailable`).

Action:

```bash
make embeddings-model   # only if the local model is not cached
make embeddings
# or hashing fallback (CI / backup):
export SEMANTIC_EMBEDDING_PROVIDER=hashing
```

Matching must not mix incompatible vectors. Restart the API after env changes.

## Database bad state

```bash
make reset-demo
```

Destructive: remigrates and reseeds 2026. Run twice if needed — seed is idempotent.

Non-destructive policy/objective restore:

```bash
curl -X POST http://localhost:8000/api/v1/demo/reset-state
```

## Hero inventory consumed

```bash
make reset-demo
# or LIVE demo buttons: Stock → 14, Same-day available, Margin 15%
```

## Web fails / clicks do nothing

Use `http://localhost:3000` not `http://127.0.0.1:3000`.
Next.js blocks HMR from `127.0.0.1`.

```bash
cd apps/web && npm run dev -- --port 3000
```

API must be on `http://localhost:8000`.

## API not ready

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
```

`/health` = process alive. `/ready` = operational checks.
If `not_ready`, fix the failing required check (usually database).

## MCP unavailable

Use REST. MCP is optional and calls the same `/api/v1/agent/*` surface.

## Docker path

```bash
docker compose down
docker compose up --build
```

Local judging already uses host Postgres + `make reset-demo`. Prefer that
if Compose would fight an existing local database.

# AstraOS API

FastAPI service for AstraOS.

Stage 5 selects a Pareto-efficient merchant response from the Stage 4 offer space.

- `POST /api/v1/intent/analyse` — structured deep intent
- `POST /api/v1/intent/qualify` — Stage 2 qualification (preserved)
- `POST /api/v1/match` — qualify, then rank eligible SKUs by Semantic Fit
- `POST /api/v1/offers/generate` — enumerate commercial configurations
- `GET /api/v1/offers/runs/{id}` — paginated / filtered offer space
- `GET /api/v1/offers/{id}` — one offer + proof
- `POST /api/v1/optimisation/run` — economics, policy, utility, Pareto
- `POST /api/v1/decision/run` — full intent → recommendation trace

```bash
make migrate
make seed
make embeddings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

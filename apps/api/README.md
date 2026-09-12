# AstraOS API

FastAPI service for AstraOS.

Stage 4 constructs a combinatorial offer space around Stage 3 matches.

- `POST /api/v1/intent/analyse` — structured deep intent
- `POST /api/v1/intent/qualify` — Stage 2 qualification (preserved)
- `POST /api/v1/match` — qualify, then rank eligible SKUs by Semantic Fit
- `POST /api/v1/offers/generate` — enumerate commercial configurations
- `GET /api/v1/offers/runs/{id}` — paginated / filtered offer space
- `GET /api/v1/offers/{id}` — one offer + proof

```bash
make migrate
make seed
make embeddings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

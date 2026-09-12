# AstraOS API

FastAPI service for AstraOS.

Stage 3 adds deep-intent analysis and semantic matching over products that
already passed Stage 2 hard eligibility.

- `POST /api/v1/intent/analyse` — structured deep intent
- `POST /api/v1/intent/qualify` — Stage 2 qualification (preserved)
- `POST /api/v1/match` — qualify, then rank eligible SKUs by Semantic Fit

```bash
make migrate
make seed
make embeddings
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Evaluation:

```bash
make eval
```

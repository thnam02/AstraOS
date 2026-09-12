# AstraOS API

FastAPI service for AstraOS.

Stage 2 adds intent parsing and deterministic eligibility at
`POST /api/v1/intent/qualify`. Catalogue and policy APIs from Stage 1 remain.

```bash
make migrate
make seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

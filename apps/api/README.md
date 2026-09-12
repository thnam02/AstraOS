# AstraOS API

FastAPI service for AstraOS.

Stage 1 exposes catalogue read APIs and merchant policy storage.
Decision logic is not implemented yet.

```bash
make migrate
make seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

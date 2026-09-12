.PHONY: up down logs test lint migrate migration seed reset-db reset-demo eval embeddings embeddings-model eval-retrieval demo-hero baseline buyer-demo buyer-demo-deterministic buyer-agent-test buyer-eval ingest

API_DIR := apps/api

export POSTGRES_HOST ?= localhost
export POSTGRES_USER ?= astraos
export POSTGRES_PASSWORD ?= astraos
export POSTGRES_DB ?= astraos
export ASTRAOS_SEED ?= 2026

ifeq ($(wildcard $(API_DIR)/.venv/bin/python),)
API_PY := python3
else
API_PY := .venv/bin/python
endif

.env:
	cp .env.example .env

up: .env
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd $(API_DIR) && $(API_PY) -m pytest
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m pytest

lint:
	cd $(API_DIR) && $(API_PY) -m ruff check .
	cd $(API_DIR) && $(API_PY) -m mypy app
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m ruff check buyer_agent tests
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m mypy buyer_agent

buyer-demo:
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m buyer_agent run --scenario urgent-traveller --mode llm

buyer-demo-deterministic:
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m buyer_agent run --scenario urgent-traveller --mode deterministic

buyer-agent-test:
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m pytest

buyer-eval:
	cd apps/buyer-agent && PYTHONPATH=. ../api/.venv/bin/python -m buyer_agent eval --mode deterministic --out ../../artifacts/realification/phase4-missions.json

migrate:
	cd $(API_DIR) && $(API_PY) -m alembic upgrade head

migration:
	cd $(API_DIR) && $(API_PY) -m alembic revision --autogenerate -m "$(name)"

seed:
	cd $(API_DIR) && $(API_PY) -m app.seed

reset-db:
	@echo "Destructive: remigrates $(POSTGRES_DB) from the Stage 0 baseline and reseeds."
	cd $(API_DIR) && $(API_PY) -m app.seed --reset

reset-demo:
	@echo "Destructive demo reset: remigrate + seed 2026."
	cd $(API_DIR) && $(API_PY) -m app.cli reset-demo

demo-hero:
	cd $(API_DIR) && $(API_PY) -m app.cli demo hero

embeddings-model:
	cd $(API_DIR) && $(API_PY) -m pip install '.[semantic]'
	cd $(API_DIR) && SEMANTIC_EMBEDDING_ALLOW_DOWNLOAD=1 $(API_PY) -c "from app.decision.retrieval.embeddings import load_sentence_transformer, DEFAULT_SEMANTIC_MODEL; from app.config import settings; load_sentence_transformer(settings.semantic_embedding_model or DEFAULT_SEMANTIC_MODEL); print('cached', settings.semantic_embedding_model)"

ingest:
	cd $(API_DIR) && $(API_PY) -m app.cli ingest --source json --file ../../examples/merchant-data/harbor-sound.json $(if $(APPLY),--apply,)

embeddings:
	cd $(API_DIR) && $(API_PY) -m app.eval.index

eval:
	cd $(API_DIR) && $(API_PY) -m app.eval

eval-retrieval:
	cd $(API_DIR) && $(API_PY) -m app.eval.retrieval_dataset
	cd $(API_DIR) && $(API_PY) -m app.eval.retrieval --out ../../artifacts/eval/retrieval-hash-vs-semantic-v1.json

# Lightweight Phase 1 reproduction: identity + migration head + frozen eval.
# Hero, Arena, learning, and full pytest are documented in
# docs/realification-baseline.md and are not inlined here.
baseline:
	@echo "version=astraos-hackathon-core-v1"
	@echo "git=$$(git rev-parse HEAD)"
	@echo "seed=$(ASTRAOS_SEED)"
	@echo "parser=$${INTENT_PARSER_MODE:-rule_based}"
	@echo "response_model=$${RESPONSE_MODEL_MODE:-COLD_START}"
	cd $(API_DIR) && $(API_PY) -m alembic heads
	cd $(API_DIR) && $(API_PY) -m alembic current
	cd $(API_DIR) && $(API_PY) -m app.eval --k 10
	@echo "Next: make test && cd apps/web && npm test && npm run build"
	@echo "Hero: ASTRAOS_BASELINE_API_URL=http://127.0.0.1:8000 cd $(API_DIR) && $(API_PY) scripts/collect_baseline.py"
	@echo "Arena: POST /api/v1/arena/benchmarks {mission_count:100, seed:2026}"
	@echo "Learning: LEARNING_TARGET=2500 ASTRAOS_LEARNING_SEED=2026 cd $(API_DIR) && $(API_PY) scripts/run_learning_report.py"
	@echo "See docs/realification-baseline.md"

.PHONY: up down logs test lint migrate migration seed reset-db eval embeddings

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

lint:
	cd $(API_DIR) && $(API_PY) -m ruff check .
	cd $(API_DIR) && $(API_PY) -m mypy app

migrate:
	cd $(API_DIR) && $(API_PY) -m alembic upgrade head

migration:
	cd $(API_DIR) && $(API_PY) -m alembic revision --autogenerate -m "$(name)"

seed:
	cd $(API_DIR) && $(API_PY) -m app.seed

reset-db:
	@echo "Destructive: remigrates $(POSTGRES_DB) from the Stage 0 baseline and reseeds."
	cd $(API_DIR) && $(API_PY) -m app.seed --reset

embeddings:
	cd $(API_DIR) && $(API_PY) -m app.eval.index

eval:
	cd $(API_DIR) && $(API_PY) -m app.eval

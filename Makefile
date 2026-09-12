.PHONY: up down logs test lint migrate migration seed

API_DIR := apps/api

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
	@echo "Seeding will be implemented in Stage 1."

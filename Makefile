# OmiAgent — one-stop dev entrypoints.  (make <target>)
PY ?= $(shell command -v uv >/dev/null 2>&1 && echo "uv run" || echo ".venv/bin/python -m")

.PHONY: help install dev serve ui ui-dev test lint fmt check build up down clean demo ping live-test

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-9s\033[0m %s\n",$$1,$$2}'

install: ## python deps (editable) + dev extras
	@command -v uv >/dev/null 2>&1 && (uv venv -q; uv pip install -q -e ".[dev]") || (python3 -m venv .venv && .venv/bin/pip install -q -e ".[dev]")

serve: ## run the server (UI + API on :8000)
	$(PY) -m omiagent serve

demo: ## offline demo (scripted model, real tools) — no keys needed
	$(PY) -m omiagent demo --fake

ui: ## build the UI into ui/dist (served by the API at /)
	cd ui && npm install --no-fund --no-audit && npm run build

ui-dev: ## vite dev server with proxy (also run `serve` in another terminal)
	cd ui && npm run dev

test: ## backend tests
	$(PY) -m pytest

lint: ## ruff
	@command -v uv >/dev/null 2>&1 && uv run ruff check src tests || (.venv/bin/ruff check src tests)

fmt: ## ruff autofix + import sort
	@command -v uv >/dev/null 2>&1 && uv run ruff check --fix src tests || (.venv/bin/ruff check --fix src tests)

check: lint test ## CI: lint + tests

ping: ## one real provider call — proves keys & routing
	@([ -f .env ] && set -a && . ./.env && set +a; true); \
	$(PY) -m omiagent ping

live-test: ## key-gated live provider test suite
	@([ -f .env ] && set -a && . ./.env && set +a; true); \
	$(PY) -m pytest -m live -v 2>&1 | tail -15

build: ui ## full artifact build (UI dist into repo for serving)

up: ## all-in-docker: build runtime + server image and compose-up
	docker build -t omiagent/runtime:local sandbox
	docker compose up --build

down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache ui/dist ui/node_modules

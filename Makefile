# Makefile for python-agent-boilerplate
# Run `make help` to list all targets.

.DEFAULT_GOAL := help
SHELL := /bin/bash

# ---- Variables (override on the command line: `make dev PORT=9000`) ----
PORT          ?= 8000
IMAGE_NAME    ?= python-agent-boilerplate
IMAGE_TAG     ?= latest
HELM_CHART    := deploy/helm/python-agent-boilerplate
HELM_RELEASE  ?= agent
K8S_DIR       := deploy/k8s
APP           := app.main:app

##@ Setup

.PHONY: install
install: ## Install all dependencies (incl. dev) and create .venv
	uv sync

.PHONY: install-prod
install-prod: ## Install production dependencies only
	uv sync --no-dev

.PHONY: lock
lock: ## Refresh uv.lock against pyproject.toml
	uv lock

##@ Development

.PHONY: dev
dev: ## Run dev server with auto-reload on PORT (default 8000)
	uv run uvicorn $(APP) --reload --port $(PORT)

.PHONY: run
run: ## Run production-like server (no reload) on PORT
	uv run uvicorn $(APP) --host 0.0.0.0 --port $(PORT)

.PHONY: shell
shell: ## Open a Python REPL inside the project venv
	uv run python

##@ Testing

.PHONY: test
test: ## Run the full pytest suite (quiet)
	uv run pytest tests/ -q

.PHONY: test-verbose
test-verbose: ## Run the full pytest suite (verbose)
	uv run pytest tests/ -v

.PHONY: test-fast
test-fast: ## Run pytest, stop at first failure
	uv run pytest tests/ -x

.PHONY: coverage
coverage: ## Run pytest with line + branch coverage report
	uv run pytest tests/ --cov=app --cov-branch --cov-report=term-missing

##@ Quality

.PHONY: lint
lint: ## Run ruff check
	uv run ruff check app/ tests/

.PHONY: lint-fix
lint-fix: ## Run ruff check with --fix
	uv run ruff check --fix app/ tests/

.PHONY: format
format: ## Format code with ruff
	uv run ruff format app/ tests/

.PHONY: format-check
format-check: ## Verify code is formatted (no changes)
	uv run ruff format --check app/ tests/

.PHONY: check
check: lint format-check test ## Full quality gate (lint + format-check + tests)
	@echo "✓ all checks passed"

##@ Docker

.PHONY: docker-build
docker-build: ## Build the production Docker image (auto-bakes git SHA + timestamp)
	docker build \
		--build-arg BUILD_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo unknown) \
		--build-arg BUILD_TIMESTAMP=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
		-t $(IMAGE_NAME):$(IMAGE_TAG) .

.PHONY: docker-up
docker-up: ## Start the local stack (service + ollama) detached
	docker compose up -d

.PHONY: docker-down
docker-down: ## Stop and remove the local stack
	docker compose down

.PHONY: docker-logs
docker-logs: ## Tail docker-compose logs
	docker compose logs -f

##@ Kubernetes / Helm

.PHONY: helm-lint
helm-lint: ## Lint the Helm chart
	helm lint $(HELM_CHART)

.PHONY: helm-template
helm-template: ## Render Helm templates to stdout (release name = HELM_RELEASE)
	helm template $(HELM_RELEASE) $(HELM_CHART)

.PHONY: k8s-validate
k8s-validate: ## Client-side validate K8s manifests (requires kubectl)
	@for f in $(K8S_DIR)/*.yaml; do \
		echo "→ $$f"; \
		kubectl apply --dry-run=client -f $$f >/dev/null && echo "  ok" || echo "  FAIL"; \
	done

##@ Release

.PHONY: version
version: ## Show the current project version
	@grep -m1 -E '^version = "' pyproject.toml | awk -F'"' '{print $$2}'

.PHONY: release-patch
release-patch: ## Bump patch version (X.Y.Z → X.Y.Z+1) and promote CHANGELOG
	uv run python scripts/release.py patch

.PHONY: release-minor
release-minor: ## Bump minor version (X.Y.Z → X.Y+1.0) and promote CHANGELOG
	uv run python scripts/release.py minor

.PHONY: release-major
release-major: ## Bump major version (X.Y.Z → X+1.0.0) and promote CHANGELOG
	uv run python scripts/release.py major

##@ Cleanup

.PHONY: clean
clean: ## Remove Python caches and build artefacts
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache -o -name '*.egg-info' \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

.PHONY: clean-all
clean-all: clean ## clean + remove the virtual environment (.venv)
	rm -rf .venv

##@ Help

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2} /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)}' $(MAKEFILE_LIST)

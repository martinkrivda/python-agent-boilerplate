# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production-ready FastAPI microservice exposing a provider-agnostic AI agent REST endpoint. Connects to any OpenAI-compatible backend (OpenAI, Ollama, LM Studio, vLLM, OpenRouter) via a single `ModelClient` abstraction.

**Python 3.14+ · uv · FastAPI · Pydantic v2 · structlog · prometheus-client**

## Project conventions

- **YAML files use `.yaml`, never `.yml`.** This is strict — applies to Helm charts, Kubernetes manifests, `docker-compose.yaml`, GitHub workflows, and any other YAML in this repository. When creating or renaming YAML files, use `.yaml`. Flag any `.yml` file as a violation in code review.
  - **Exception:** `.github/dependabot.yml` — GitHub Dependabot has a hardcoded filename. The rule applies to files we control; external tools with fixed filename contracts are exempt. Document any future exceptions here.

## Setup & Commands

A `Makefile` wraps the most common commands. Run `make help` for the full list (auto-generated from comments).

| Make target | Equivalent |
|-------------|------------|
| `make install` | `uv sync` |
| `make dev` | `uv run uvicorn app.main:app --reload` |
| `make test` | `uv run pytest tests/ -q` |
| `make lint` / `make format` | `uv run ruff check / format` |
| `make check` | full quality gate (lint + format-check + tests) |
| `make coverage` | `pytest --cov=app --cov-branch` |
| `make docker-build` / `make docker-up` | Docker workflow |
| `make helm-lint` / `make helm-template` | Helm chart validation / rendering |
| `make k8s-validate` | client-side `kubectl --dry-run` of all `deploy/k8s/*.yaml` |
| `make clean` / `make clean-all` | remove caches / also remove `.venv` |

Run a single test directly: `uv run pytest tests/test_agent.py::test_agent_run_happy_path -v`.
Add a dependency: `uv add <package>`.

## Architecture

### Entry points

- **`app/main.py`** — FastAPI app factory; `lifespan` builds `OpenAICompatibleModelClient` and `ModelSettings` on `app.state`; registers middleware, routers, exception handlers, and `/metrics` WSGI mount.
- **`app/cli.py`** — Typer-based terminal CLI (`agent` command, registered via `[project.scripts]`). Sub-commands: `version`, `models`, `ask`, `chat`, `serve`. Reuses the same `Settings` / `ModelClient` / `AssistantAgent` / `AgentService` as the HTTP service — never duplicate the agent logic in the CLI.

### Layer map

```
app/
  core/
    config.py          — Settings(BaseSettings): all env vars
    request_context.py — ContextVar[request_id] + helpers
    logging.py         — configure_logging() (structlog JSON)
    errors.py          — AppError hierarchy: ValidationError, ProviderError, InternalError
    metrics.py         — make_metrics(registry), Metrics dataclass, 6 prometheus metrics
    middleware.py      — CorrelationIdMiddleware, RequestLoggingMiddleware, MetricsMiddleware

  ai/
    model_client.py    — ModelClient ABC, ChatMessage, GenerateParams, GenerateResult
    model_settings.py  — ModelSettings(BaseModel).from_settings() — no api_key exposed
    providers/
      openai_compatible.py — AsyncOpenAI wrapper, SDK→ProviderError mapping

  agents/
    schemas.py         — AgentRunRequest, AgentRunResponse
    assistant_agent.py — AssistantAgent.run(message) → AgentRunResponse
    tools.py           — extension point (empty in v1)

  services/
    agent_service.py   — AgentService: per-request, applies overrides → AssistantAgent

  api/
    envelope.py        — ApiResponse, ok(), error_response(), error_response_with_fields()
    dependencies.py    — get_model_client, get_model_settings, get_agent_service (Depends)
    routes/
      health.py        — /health, /health/live, /health/ready
      agent.py         — POST /rest/v1/agent/run
      models.py        — GET /rest/v1/models/current
```

### Request flow

```
HTTP → CorrelationIdMiddleware → RequestLoggingMiddleware → MetricsMiddleware
     → route handler → Depends(get_agent_service)
     → AgentService → AssistantAgent → ModelClient → AsyncOpenAI → provider
```

### Middleware registration order (FastAPI: last added = outermost)

```python
app.add_middleware(MetricsMiddleware)       # innermost
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware) # outermost
```

## API Routes

| Path | Method | Envelope |
|------|--------|----------|
| `/rest/v1/agent/run` | POST | yes |
| `/rest/v1/models/current` | GET | yes |
| `/health`, `/health/live`, `/health/ready` | GET | yes |
| `/metrics` | GET | no (Prometheus WSGI) |
| `/doc` | GET | no (OpenAPI JSON) |

## Configuration (env vars)

| Variable | Default |
|----------|---------|
| `AI_PROVIDER` | `ollama` |
| `AI_MODEL` | `qwen3:8b` |
| `AI_BASE_URL` | `http://localhost:11434/v1` |
| `AI_API_KEY` | `ollama` |
| `AI_REQUEST_TIMEOUT` | `60` |
| `AI_SUPPORTS_TOOLS` | `false` |
| `LOG_LEVEL` | `INFO` |
| `APP_ENV` | `development` |
| `BUILD_COMMIT` | `""` (auto-baked at Docker build) |
| `BUILD_TIMESTAMP` | `""` (auto-baked at Docker build) |
| `LOG_FORMAT` | `json` (or `console` for local dev) |
| `LOG_TO_FILE` | `true` — also write to `logs/app.log` |
| `LOG_DIR` | `logs` |
| `LOG_FILE_NAME` | `app.log` |
| `LOG_ROTATION_WHEN` | `midnight` — daily UTC rotation |
| `LOG_ROTATION_BACKUP_COUNT` | `30` — older files gzipped, then pruned |

### Logging conventions

- structlog wraps stdlib `logging`; both `structlog.get_logger()` and
  `logging.getLogger(...)` produce identical structured output.
- Static fields automatically on every event: `service`, `env`, `version`,
  `hostname`, `timestamp`, `level`.
- Per-request fields via `structlog.contextvars` — `request_id`, `client_ip`,
  `method`, `path` are bound by `CorrelationIdMiddleware`; `user_id` /
  `conversation_id` are bound by the agent route when present in the body.
  `clear_contextvars()` runs in middleware `finally` to prevent leakage.
- Never log secrets (`api_key`, `Authorization` header, request body, model
  output). The middleware specifically excludes those.

See `.env.example` for all variables and provider-specific examples.

## Testing

- **`tests/conftest.py`** — `FakeModelClient`, `RaisesModelClient`, `app` fixture with `dependency_overrides`, `client` fixture (TestClient)
- Override the real client in tests via `app.dependency_overrides[get_model_client] = lambda: FakeModelClient()`
- Never makes real LLM calls in tests
- Prometheus metrics use isolated `CollectorRegistry` per test

## Error codes

| Code | HTTP | Meaning |
|------|------|---------|
| E1001 | 422 | Validation error |
| E2001 | 504 | Provider timeout |
| E2002 | 502 | Provider auth failure |
| E2003 | 503 | Provider unavailable |
| E2004 | 502 | Invalid provider response |
| E3001 | 500 | Unhandled internal error |

## Deployment

- **Docker:** `docker compose up` (includes Ollama)
- **K8s:** plain manifests in `deploy/k8s/`
- **Helm:** chart in `deploy/helm/python-agent-boilerplate/`

## Extension points (v2+)

| Feature | File |
|---------|------|
| Tool calling | `app/agents/tools.py` |
| Streaming | `app/ai/model_client.py` → add `generate_stream()` |
| Conversation memory | `AgentRunRequest.conversation_id` → wire to store in `app/services/` |
| New provider | New class in `app/ai/providers/` |
| RAG | New service injected into `AgentService` |

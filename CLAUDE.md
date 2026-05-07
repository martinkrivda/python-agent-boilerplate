# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production-ready FastAPI microservice exposing a provider-agnostic AI agent REST endpoint. Connects to any OpenAI-compatible backend (OpenAI, Ollama, LM Studio, vLLM, OpenRouter) via a single `ModelClient` abstraction.

**Python 3.14+ · uv · FastAPI · Pydantic v2 · structlog · prometheus-client**

## Setup & Commands

```bash
# Install dependencies
uv sync

# Run the service (development)
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_agent.py::test_agent_run_happy_path -v

# Lint
uv run ruff check app/ tests/

# Add a dependency
uv add <package>
```

## Architecture

### Entry point

- **`app/main.py`** — FastAPI app factory; `lifespan` builds `OpenAICompatibleModelClient` and `ModelSettings` on `app.state`; registers middleware, routers, exception handlers, and `/metrics` WSGI mount.

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

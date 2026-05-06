# Design: python-agent-boilerplate

**Date:** 2026-05-06
**Status:** Approved

## Overview

A production-ready FastAPI microservice exposing a provider-agnostic AI agent REST endpoint. The service communicates with any OpenAI-compatible model backend (OpenAI, Ollama, LM Studio, vLLM, SGLang, LiteLLM Proxy, OpenRouter) through a single `ModelClient` abstraction. All business logic is isolated from provider specifics.

**First version is intentionally narrow:** no LangChain, no LangGraph, no Celery, no Redis, no Postgres, no vector DB, no RAG, no long-term memory, no complex tool calling. Extension points for those are documented but not implemented.

---

## Python Version

- **Runtime:** Python 3.14+
- `.python-version` pinned to `3.14` for local development
- `pyproject.toml`: `requires-python = ">=3.14"`
- No upper bound unless a concrete dependency compatibility issue appears
- CI validates Python 3.14 only initially; newer versions added as they stabilise
- README documents 3.14 as the baseline and that newer versions are allowed

---

## Technology Stack

| Concern | Choice |
|---------|--------|
| Web framework | FastAPI |
| Dependency management | uv |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| AI client | `openai` Python SDK (`AsyncOpenAI`) |
| Testing | pytest + pytest-asyncio |
| Linting / formatting | ruff |
| Type checking | mypy (if all deps support 3.14; skip silently if not) |
| Structured logging | structlog (JSON) |
| Metrics | prometheus-client |
| Containerisation | Docker (slim base, non-root user) |
| Local dev orchestration | docker-compose |
| Kubernetes | plain manifests + Helm chart |

---

## Project Structure

```
python-agent-boilerplate/
  app/
    __init__.py
    main.py

    api/
      __init__.py
      envelope.py
      dependencies.py
      routes/
        __init__.py
        health.py
        agent.py
        models.py

    agents/
      __init__.py
      schemas.py
      assistant_agent.py
      tools.py            # extension point, empty in v1

    ai/
      __init__.py
      model_client.py
      model_settings.py
      providers/
        __init__.py
        openai_compatible.py

    core/
      __init__.py
      config.py
      logging.py
      errors.py
      middleware.py
      metrics.py
      request_context.py

    services/
      __init__.py
      agent_service.py

  tests/
    conftest.py
    test_health.py
    test_agent.py
    test_envelope.py
    test_errors.py
    test_metrics.py
    test_model_settings.py
    test_openapi.py

  deploy/
    k8s/
      namespace.yaml
      deployment.yaml
      service.yaml
      configmap.yaml
      secret.example.yaml
      ingress.yaml
      hpa.yaml
      servicemonitor.yaml

    helm/
      python-agent-boilerplate/
        Chart.yaml
        values.yaml
        templates/
          _helpers.tpl
          deployment.yaml
          service.yaml
          configmap.yaml
          secret.yaml
          ingress.yaml
          hpa.yaml
          serviceaccount.yaml
          servicemonitor.yaml
          NOTES.txt

  .dockerignore
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  pyproject.toml
  README.md
```

---

## Route Map

| Path | Method | Handler | Envelope |
|------|--------|---------|----------|
| `/rest/v1/agent/run` | POST | agent.py | yes |
| `/rest/v1/models/current` | GET | models.py | yes |
| `/health` | GET | health.py | yes |
| `/health/live` | GET | health.py | yes |
| `/health/ready` | GET | health.py | yes |
| `/metrics` | GET | prometheus-client WSGI | **no** |
| `/doc` | GET | OpenAPI JSON | **no** |
| `/reference` | GET | Scalar/ReDoc HTML | **no** |

FastAPI is configured with `docs_url=None`, `redoc_url=None`, `openapi_url="/doc"`. The interactive reference is mounted separately at `/reference`.

---

## Architecture & Call Chain

The service is stateless. All configuration flows in through environment variables read by `pydantic-settings` at startup. There is no database, queue, or persistent state.

### Startup sequence

1. `app/main.py` creates the FastAPI app with a `lifespan` context manager.
2. `lifespan` reads `Settings`, builds one `OpenAICompatibleModelClient` and one `ModelSettings`, stores both on `app.state` (immutable after startup).
3. Routers are registered. Business routes under `/rest/v1`; infrastructure routes at root level.
4. Three exception handlers are registered (see Error Handling).
5. Middleware is registered (see Middleware Stack).

### Request call chain — `POST /rest/v1/agent/run`

```
HTTP request
  → CorrelationIdMiddleware   (outermost)
  → RequestLoggingMiddleware
  → MetricsMiddleware         (innermost middleware)
  → route handler (agent.py)
      → Depends(get_model_client)   ← reads app.state.model_client
      → Depends(get_model_settings) ← reads app.state.model_settings
      → Depends(get_agent_service)  ← constructs AgentService(model_client, model_settings)
      → AgentService.run(AgentRunRequest)
          → AssistantAgent(...).run(message)
              → ModelClient.generate(messages, params)
                  → OpenAICompatibleModelClient → AsyncOpenAI → provider
      → ok(AgentRunResponse)
  → MetricsMiddleware: record duration, increment counters
  → RequestLoggingMiddleware: emit structured log line
  → CorrelationIdMiddleware: set X-Request-Id header, reset ContextVar
HTTP response
```

---

## Middleware Stack

Registration order (FastAPI — last added = outermost):

```python
app.add_middleware(MetricsMiddleware)        # added 1st → innermost
app.add_middleware(RequestLoggingMiddleware) # added 2nd → middle
app.add_middleware(CorrelationIdMiddleware)  # added 3rd → outermost
```

### CorrelationIdMiddleware

```
request in:
  read X-Request-Id header (or generate UUID v4)
  save as local variable `request_id`
  set ContextVar[request_id] → save reset token
  try:
    response = await call_next(request)
  except Exception as exc:
    log.error("middleware_exception", request_id=request_id, exc_info=True)
    response = build_safe_500_envelope(request_id)   # safe internal envelope
  finally:
    reset ContextVar using saved token               # always, even if exc
  response.headers["X-Request-Id"] = request_id     # use local var, not ContextVar
  return response
```

- `request_id` is a local variable; header is set from it **after** the finally block resets the ContextVar.
- If an exception escapes `call_next`, the middleware creates a safe 500 envelope itself (FastAPI route-level exception handlers may not fire for exceptions originating above the route layer).
- Context var reset is always in `finally` to prevent leakage between requests on the same worker.

### RequestLoggingMiddleware

Emits one structured JSON log line per request on completion (both success and failure):

```json
{
  "event": "http_request",
  "request_id": "...",
  "method": "POST",
  "path": "/rest/v1/agent/run",
  "status_code": 200,
  "duration_ms": 123,
  "user_id": "optional-if-present"
}
```

On failures, includes `status_code` (known value or 500) and `error_code` if available on response state.

**Never logs:** request body, response body, prompts, model output, `Authorization`, `X-Api-Key`, `Cookie`, tokens, or any secret header.

Excludes `/metrics`, `/doc`, `/reference` from log output (path-prefix check) to avoid noise.

### MetricsMiddleware

Records:
- `http_requests_total{method, route, status_code}` — incremented after response
- `http_request_duration_seconds{method, route}` — observed after response

Route label: reads `request.scope["route"].path` after routing resolves (e.g., `/rest/v1/agent/run`). Falls back to `"unmatched"` for 404s. Never uses raw paths, path parameter values, query strings, or IDs.

Explicitly excludes `/metrics` from self-instrumentation (path check before recording) to prevent recursive/noisy entries. Does not apply response envelope logic.

Middleware exceptions are caught, logged with `request_id`, and re-raised.

---

## Component Breakdown

### `app/core/`

**`config.py`** — `Settings(BaseSettings)` reads all env vars. Single source of truth for every tunable. Groups: app metadata, AI provider config, timeout, capability flags, logging, optional extra headers.

**`request_context.py`** — module-level `ContextVar[str]` (`_request_id_var`). Public helpers: `set_request_id(id) → Token`, `get_request_id() → str`, `reset_request_id(token)`. Used by middleware, logging, and envelope construction.

**`logging.py`** — `configure_logging()` sets up structlog with JSON renderer. Binds `request_id` from the ContextVar automatically on each log call. Called once at startup.

**`errors.py`** — Exception hierarchy:
```
AppError(status, code, title, detail, instance=None)
  ├── ValidationError   (E1xxx, status 400/422)
  ├── ProviderError     (E2xxx, status 502/503/504)
  └── InternalError     (E3xxx, status 500)
```

Provider error mapping:
| Condition | HTTP | Code |
|-----------|------|------|
| timeout | 504 | E2001 |
| auth failure | 502 | E2002 |
| provider unavailable | 503 | E2003 |
| invalid provider response | 502 | E2004 |

`AppError.to_problem_details(instance, request_id) → ProblemDetails`.

**`middleware.py`** — `CorrelationIdMiddleware`, `RequestLoggingMiddleware`, `MetricsMiddleware` (see Middleware Stack above).

**`metrics.py`** — Module-level Prometheus metric objects. Supports registry injection for test isolation (`make_metrics(registry=None)` returning a `Metrics` dataclass). AI metric helpers: `record_ai_request(provider, model)`, `record_ai_error(provider, model)`, `observe_ai_duration(provider, model, seconds)`.

Metric inventory:
| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | method, route, status_code |
| `http_request_duration_seconds` | Histogram | method, route |
| `http_errors_total` | Counter | status_code, error_code |
| `ai_model_requests_total` | Counter | provider, model |
| `ai_model_request_duration_seconds` | Histogram | provider, model |
| `ai_model_errors_total` | Counter | provider, model |

### `app/ai/`

**`model_client.py`** — `ModelClient` ABC:
```python
class ModelClient(ABC):
    @abstractmethod
    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult: ...
```
`GenerateResult(content: str, provider: str, model: str, usage: dict | None)`.

**`model_settings.py`** — `ModelSettings(BaseModel)` holding sanitised provider metadata (no `api_key`):
```
provider, model, base_url,
supports_tools, supports_structured_output,
supports_thinking, supports_streaming
```
Constructed from `Settings` at startup; stored on `app.state.model_settings`.

**`providers/openai_compatible.py`** — `OpenAICompatibleModelClient(ModelClient)`:
- Constructs `AsyncOpenAI(base_url, api_key, timeout, default_headers)` in `__init__`.
- `generate()` calls `client.chat.completions.create(...)`.
- Wraps SDK exceptions into `ProviderError` with appropriate code (E2001–E2004).
- Records metrics: increments `ai_model_requests_total` on attempt; observes duration in `finally`; increments `ai_model_errors_total` on exception.

### `app/agents/`

**`schemas.py`** — `AgentRunRequest(message, user_id?, conversation_id?, system_prompt?, temperature?, max_tokens?)` and `AgentRunResponse(answer, provider, model, usage?, metadata?)`.

**`assistant_agent.py`** — `AssistantAgent(model_client, model_settings, system_prompt, temperature, max_tokens)`. Instantiated per-request. Has one method: `async def run(message: str) → AgentRunResponse`. Builds `[SystemMessage, UserMessage]` list and calls `model_client.generate()`. No planning, memory, tools, RAG, or multi-step loops in v1.

**`tools.py`** — Empty extension point. Documents where tool definitions live in v2.

### `app/services/`

**`agent_service.py`** — `AgentService(model_client, model_settings)`. Created per-request via `Depends`. Constructs `AssistantAgent` with per-request overrides (system prompt, temperature, max_tokens from request; defaults from settings). Calls `agent.run(message)`.

### `app/api/`

**`envelope.py`** — Pydantic models and helpers:
```python
class ResponseMeta(BaseModel):
    requestId: str
    timestamp: str  # RFC 3339 with Z suffix, timezone-aware UTC

class ProblemDetails(BaseModel):
    type: str       # URI
    title: str
    status: int
    detail: str
    instance: str
    code: str       # E1xxx / E2xxx / E3xxx
    requestId: str
    errors: list[FieldError] | None  # only for validation errors

class FieldError(BaseModel):
    pointer: str    # RFC 6901, e.g. "/message" (into payload, not "/body/message")
    message: str
    code: str       # REQUIRED, INVALID_TYPE, MIN_VALUE, etc.

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ProblemDetails | None
    meta: ResponseMeta

def ok(data: T, status_code: int = 200) -> JSONResponse: ...
def error_response(err: AppError, instance: str, request_id: str) -> JSONResponse: ...
```

Invariants enforced in helpers:
- `success=true` ↔ HTTP 2xx; `data` populated; `error=null`
- `success=false` ↔ HTTP 4xx/5xx; `error` populated; `data=null`
- `error.status` == HTTP status code (errors only; success has no body status field)
- `meta` always present

**`dependencies.py`**:
```python
def get_model_client(request: Request) -> ModelClient:
    return request.app.state.model_client

def get_model_settings(request: Request) -> ModelSettings:
    return request.app.state.model_settings

def get_agent_service(
    model_client: ModelClient = Depends(get_model_client),
    model_settings: ModelSettings = Depends(get_model_settings),
) -> AgentService:
    return AgentService(model_client, model_settings)
```

This wiring means `app.dependency_overrides[get_model_client]` cleanly substitutes the fake client in tests, because `get_agent_service` depends on `get_model_client` through FastAPI `Depends`.

**`routes/health.py`** — `/health`, `/health/live`, `/health/ready`. All use `ok(data)` envelope. Readiness validates config and `app.state` only; no LLM call unless `AI_PROBE_ON_READY=true` env flag is set.

**`routes/agent.py`** — thin `POST /rest/v1/agent/run` handler. Calls `AgentService.run(request)`, returns `ok(response)`.

**`routes/models.py`** — `GET /rest/v1/models/current`. Returns `ModelSettings` fields via `ok(data)`. Never exposes `api_key`, `AI_API_KEY`, `HTTP-Referer`, `X-OpenRouter-Title`, or any secret header value.

### `app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(settings)
    app.state.model_client = OpenAICompatibleModelClient(settings)
    app.state.model_settings = ModelSettings.from_settings(settings)
    yield
    # cleanup if needed

app = FastAPI(
    title="python-agent-boilerplate",
    docs_url=None,
    redoc_url=None,
    openapi_url="/doc",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Middleware (last added = outermost)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Routers
app.include_router(health_router)
app.include_router(rest_router, prefix="/rest/v1")

# /reference (HTML docs)
# /metrics (Prometheus WSGI — middleware must explicitly exclude this path)
```

---

## Error Handling

### Three exception handlers

**`AppError` handler:**
```
AppError(status, code, title, detail, instance)
  → ApiErrorResponse(success=false, error=ProblemDetails(..., requestId), meta, data=null)
  → JSONResponse(status_code, headers={"Cache-Control": "no-store", "X-Request-Id": requestId})
```

**`RequestValidationError` handler:**
```
RequestValidationError(errors=[...])
  → FieldError per error:
      pointer = "/" + ".".join(loc[1:])  # RFC 6901 into payload, e.g. "/message"
      code    = REQUIRED | INVALID_TYPE | MIN_VALUE | MAX_VALUE | …
  → ApiErrorResponse(error.code="E1001", error.errors=[FieldError, ...])
  → JSONResponse(422, headers={"Cache-Control": "no-store", "X-Request-Id": requestId})
```

Field pointer convention: strip the leading `body` location element from FastAPI's error location tuple; use RFC 6901 format pointing into the submitted JSON payload (e.g., `/message`, `/temperature`). For query/header errors use `/query/<name>` or `/header/<name>`.

Per-field `code` values: `REQUIRED`, `INVALID_TYPE`, `MIN_VALUE`, `MAX_VALUE`, `INVALID_FORMAT`, `TOO_SHORT`, `TOO_LONG`, `EXTRA_FIELD`.

**Catch-all `Exception` handler:**
```
Exception
  → log.error("unhandled_exception", request_id=get_request_id(), exc_info=True)
  → ApiErrorResponse(error.code="E3001", status=500, detail="An unexpected error occurred.")
  → JSONResponse(500, headers={"Cache-Control": "no-store", "X-Request-Id": requestId})
```
No stack trace, SQL, path, service name, credential, or token in response body. All debug info server-side only.

### Timestamp format

All `meta.timestamp` and `error.timestamp` values are generated with timezone-aware UTC and serialised as RFC 3339 ending in `Z`:
```python
datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
```

### Envelope exclusions

`/metrics`, `/doc`, `/reference` are not wrapped in the envelope. If they fail, native framework/server errors are acceptable — they are infrastructure/docs endpoints, not business API endpoints. `X-Request-Id` header may still be present on these responses if the correlation middleware applies globally (acceptable).

---

## Settings & Provider Configuration

`Settings` env vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `python-agent-boilerplate` | Service name |
| `APP_ENV` | `development` | Environment tag |
| `LOG_LEVEL` | `INFO` | structlog level |
| `AI_PROVIDER` | `ollama` | Provider tag |
| `AI_MODEL` | `qwen3:8b` | Model name |
| `AI_BASE_URL` | `http://localhost:11434/v1` | OpenAI-compatible base URL |
| `AI_API_KEY` | `ollama` | API key (never logged or returned) |
| `AI_REQUEST_TIMEOUT` | `60` | Seconds |
| `AI_SUPPORTS_TOOLS` | `false` | Capability flag |
| `AI_SUPPORTS_STRUCTURED_OUTPUT` | `false` | Capability flag |
| `AI_SUPPORTS_THINKING` | `false` | Capability flag |
| `AI_SUPPORTS_STREAMING` | `false` | Capability flag |
| `AI_PROBE_ON_READY` | `false` | Enable LLM call in readiness |
| `OPENROUTER_HTTP_REFERER` | `` | Optional extra header |
| `OPENROUTER_TITLE` | `` | Optional extra header |

Provider configurations documented in `.env.example` and README.

---

## Testing Strategy

### Approach

- pytest + pytest-asyncio (`asyncio_mode = "auto"` in `pyproject.toml`)
- FastAPI `TestClient` (sync) for most tests; `AsyncClient` (via httpx) where async is needed
- No real LLM call ever made; no openai SDK imported directly in tests
- Provider access replaced via `app.dependency_overrides[get_model_client]`

### Fake clients

```python
class FakeModelClient(ModelClient):
    async def generate(self, messages, params) -> GenerateResult:
        return GenerateResult(content="fake answer", provider="fake",
                              model="fake-model", usage={...})

class RaisesModelClient(ModelClient):
    def __init__(self, exc: Exception): self._exc = exc
    async def generate(self, messages, params) -> GenerateResult:
        raise self._exc
```

### `tests/conftest.py`

- `app` fixture: applies `dependency_overrides[get_model_client] = lambda: FakeModelClient()`, clears overrides in teardown (prevents cross-test leakage).
- `client` fixture: `TestClient(app)`.
- `fake_model_client` fixture.
- `raises_model_client(exc)` factory fixture.
- Isolated Prometheus `CollectorRegistry` fixture: `metrics_registry = CollectorRegistry()` passed to `make_metrics(registry=metrics_registry)` via monkeypatching or DI; prevents global registry leakage between tests.
- Settings overridden via `monkeypatch.setenv` or direct `Settings(...)` construction; never reads `.env`.

### Test files

**`tests/test_health.py`**
- `GET /health`, `GET /health/live`, `GET /health/ready`: `success=true`, envelope present, `meta.requestId` is UUID4, `X-Request-Id` header matches `meta.requestId`, HTTP 200
- Readiness does not make LLM call by default

**`tests/test_agent.py`**
- Happy path with `FakeModelClient`: `success=true`, `data.answer == "fake answer"`, `data.provider == "fake"`, envelope shape correct
- `X-Request-Id` echoed when supplied by client
- `X-Request-Id` generated when absent
- Missing `message` field: 422, `success=false`, `error.code == "E1001"`, `error.errors[0].pointer == "/message"`, `error.errors[0].code == "REQUIRED"`, `Cache-Control: no-store`, `X-Request-Id` header present
- `RaisesModelClient(ProviderError(E2001))`: 504, `success=false`, `error.code == "E2001"`, no stack trace in body
- Forced unhandled exception via `RaisesModelClient(RuntimeError(...))`: 500, `error.code == "E3001"`, safe detail
- Malformed JSON body: 400 or 422, error envelope with `E1001` or `E100x`, no internal detail
- Unsupported `Content-Type` (if enforced): 415 or documented validation envelope

**`tests/test_model_settings.py`**
- `GET /rest/v1/models/current`: `success=true`, `data.provider`, `data.model`, capability flags present as booleans
- Response never contains `api_key`, `AI_API_KEY`, `HTTP-Referer`, `X-OpenRouter-Title`, or secret header values
- Default values: provider=`ollama`, model=`qwen3:8b`, base_url=`http://localhost:11434/v1`

**`tests/test_envelope.py`**
- `ok(data)` returns correct `ApiResponse[T]`: `success=true`, `data` populated, `error=null`, `meta` present
- `error_response(AppError(...))`: `success=false`, `error` populated, `data=null`, `meta` present
- `meta.timestamp` is RFC 3339 with `Z` suffix (UTC, timezone-aware)
- Invariant table (parametrized):

| Invariant | Scope |
|-----------|-------|
| `X-Request-Id` header == `meta.requestId` | all envelope routes |
| `error.requestId` == `meta.requestId` | error responses |
| `error.status` == HTTP status code | error responses only |
| HTTP 2xx ↔ `success=true` | success responses |
| `Cache-Control: no-store` | all 4xx/5xx |
| `data=null` when `success=false` | error responses |
| `error=null` when `success=true` | success responses |
| `data` and `error` never both populated | all responses |

**`tests/test_errors.py`**
- `AppError` serialises to `ProblemDetails` correctly
- Provider error codes: E2001 timeout (504), E2002 auth (502), E2003 unavailable (503), E2004 bad response (502)
- Error bodies never contain: stack traces, filesystem paths, internal service names, credentials, tokens, raw SQL
- All error responses include `Cache-Control: no-store` and `X-Request-Id`
- Field errors and fatal errors never mixed in one response

**`tests/test_metrics.py`**
- `GET /metrics`: 200, `Content-Type` starts with `text/plain`, body not wrapped in envelope (no `success` key)
- Body contains `http_requests_total`
- After one request, counters reflect it (isolated registry fixture)
- `/metrics` itself is not counted in `http_requests_total`

**`tests/test_openapi.py`**
- `GET /doc`: 200, `Content-Type` contains `application/json`, body has no `success` key (not enveloped), has `openapi` key
- `GET /reference`: 200, `Content-Type` contains `text/html`, body has no `meta` or `success` key

**Path exclusion tests (in `test_openapi.py` or `test_envelope.py`):**
- `/metrics`, `/doc`, `/reference` responses do not contain `meta` or `requestId` in body
- `X-Request-Id` header may be present (acceptable if middleware applies globally)

**Request ID context leak test (in `test_agent.py` or `test_envelope.py`):**
- Send two sequential requests with different `X-Request-Id` values
- Assert each response's `meta.requestId` matches its own request's `X-Request-Id`
- Assert no leakage (second response does not contain first request's ID)

---

## Docker

- Base image: `python:3.14-slim`
- `uv` for dependency installation in build stage
- Dedicated non-root user (`appuser`)
- Port 8000 exposed
- All configuration via environment variables; no secrets baked in
- `.dockerignore` excludes: `.env`, `.git`, `.venv`, `__pycache__`, `*.pyc`, `tests/`, `deploy/`, `docs/`

---

## Docker Compose

Local development stack:
- `ai-agent-service`: built from `Dockerfile`, configured with `AI_BASE_URL=http://ollama:11434/v1`
- `ollama`: optional service, persistent volume for model weights
- Document: `docker exec -it ollama ollama pull qwen3:8b`

---

## Kubernetes

Plain manifests under `deploy/k8s/`:
- `namespace.yaml`, `deployment.yaml`, `service.yaml`, `configmap.yaml`, `secret.example.yaml`, `ingress.yaml`, `hpa.yaml`, `servicemonitor.yaml`

Runtime requirements:
- Non-root user; `podSecurityContext` + `securityContext`
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true` where practical
- CPU and memory requests/limits defined
- Probes: liveness → `/health/live`, readiness → `/health/ready`, startup → `/health`
- Standard `app.kubernetes.io/` labels
- `/metrics` exposed for Prometheus scraping

---

## Helm

Chart under `deploy/helm/python-agent-boilerplate/`. Supports:
- image (repository, tag, pullPolicy), replicaCount
- service (type, port), ingress (enabled, host, tls)
- resources (requests, limits)
- autoscaling (enabled, minReplicas, maxReplicas, CPU/memory targets)
- env values and secrets
- podAnnotations, podLabels, nodeSelector, tolerations, affinity
- serviceAccount (create, name, annotations)
- Prometheus ServiceMonitor toggle
- liveness/readiness/startup probe configuration
- securityContext and podSecurityContext
- External model backend configuration (AI_PROVIDER, AI_MODEL, AI_BASE_URL, AI_API_KEY as secret ref)

Ollama is **not** deployed inside the default Helm chart. It is local-dev only.

---

## Extension Points (v2+)

| Feature | Where to extend |
|---------|----------------|
| Tool calling | `agents/tools.py` → pass to `AssistantAgent` |
| Streaming | `ModelClient.generate_stream()` + new route variant |
| Memory / conversation history | `AgentRunRequest.conversation_id` already present; wire to a store |
| RAG | New service injected into `AgentService` |
| Background jobs | Celery/Redis integration in `services/` |
| Multiple agent types | New `XxxAgent` classes alongside `AssistantAgent` |
| Additional providers | New `ModelClient` subclass in `ai/providers/` |

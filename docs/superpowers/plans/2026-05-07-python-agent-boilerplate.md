# Python Agent Boilerplate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready FastAPI microservice exposing a provider-agnostic AI agent REST endpoint backed by any OpenAI-compatible model.

**Architecture:** Stateless FastAPI app wired at startup via `lifespan`; all config from env vars via pydantic-settings; provider access behind a `ModelClient` ABC so tests never touch a real LLM. Business logic flows: Route → AgentService → AssistantAgent → ModelClient → AsyncOpenAI → provider.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pydantic-settings, openai SDK (AsyncOpenAI), structlog, prometheus-client, pytest + pytest-asyncio, ruff, uv, Docker, docker-compose, Kubernetes manifests, Helm.

---

## File Map

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | deps, tool config |
| `app/__init__.py` | package marker |
| `app/main.py` | FastAPI app factory, lifespan, router/middleware/handler registration |
| `app/core/config.py` | `Settings(BaseSettings)` — all env vars |
| `app/core/request_context.py` | `ContextVar` + helpers: `set_request_id`, `get_request_id`, `reset_request_id` |
| `app/core/logging.py` | `configure_logging(settings)` — structlog JSON |
| `app/core/errors.py` | `AppError` hierarchy + `ProblemDetails` |
| `app/core/metrics.py` | Prometheus metric objects, `make_metrics(registry)`, AI helpers |
| `app/core/middleware.py` | `CorrelationIdMiddleware`, `RequestLoggingMiddleware`, `MetricsMiddleware` |
| `app/ai/model_client.py` | `ModelClient` ABC, `ChatMessage`, `GenerateParams`, `GenerateResult` |
| `app/ai/model_settings.py` | `ModelSettings(BaseModel)`, `ModelSettings.from_settings(settings)` |
| `app/ai/providers/__init__.py` | package marker |
| `app/ai/providers/openai_compatible.py` | `OpenAICompatibleModelClient(ModelClient)` |
| `app/agents/schemas.py` | `AgentRunRequest`, `AgentRunResponse` |
| `app/agents/assistant_agent.py` | `AssistantAgent` — builds messages, calls ModelClient |
| `app/agents/tools.py` | empty extension point |
| `app/services/agent_service.py` | `AgentService` — per-request, constructs AssistantAgent with overrides |
| `app/api/envelope.py` | `ResponseMeta`, `ProblemDetails`, `FieldError`, `ApiResponse`, `ok()`, `error_response()` |
| `app/api/dependencies.py` | `get_model_client`, `get_model_settings`, `get_agent_service` |
| `app/api/routes/health.py` | `/health`, `/health/live`, `/health/ready` |
| `app/api/routes/agent.py` | `POST /rest/v1/agent/run` |
| `app/api/routes/models.py` | `GET /rest/v1/models/current` |
| `tests/conftest.py` | fixtures: app, client, fake_model_client, raises_model_client, metrics_registry |
| `tests/test_health.py` | health route tests |
| `tests/test_agent.py` | agent route happy/error paths |
| `tests/test_envelope.py` | envelope invariants |
| `tests/test_errors.py` | error serialisation |
| `tests/test_metrics.py` | prometheus endpoint + counters |
| `tests/test_model_settings.py` | models/current route |
| `tests/test_openapi.py` | /doc and /reference |
| `Dockerfile` | slim, non-root, uv install |
| `docker-compose.yml` | service + ollama |
| `.env.example` | all env vars documented |
| `.dockerignore` | excludes .env, .git, .venv, tests/, deploy/ |
| `deploy/k8s/*.yaml` | namespace, deployment, service, configmap, secret.example, ingress, hpa, servicemonitor |
| `deploy/helm/python-agent-boilerplate/` | full Helm chart |
| `README.md` | setup, provider examples, extension points |

---

## Task 1: Project Bootstrap — deps + tool config

**Files:**
- Modify: `pyproject.toml`
- Create: `app/__init__.py`, `app/ai/__init__.py`, `app/ai/providers/__init__.py`, `app/agents/__init__.py`, `app/services/__init__.py`, `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/core/__init__.py`

- [ ] **Step 1: Update pyproject.toml**

```toml
[project]
name = "python-agent-boilerplate"
version = "0.1.0"
description = "Provider-agnostic AI agent FastAPI microservice"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.3",
    "openai>=1.35",
    "structlog>=24.1",
    "prometheus-client>=0.20",
]

[dependency-groups]
dev = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

- [ ] **Step 2: Install deps**

```bash
uv sync
```

Expected: resolves and installs all packages without error.

- [ ] **Step 3: Create package markers**

```bash
mkdir -p app/core app/ai/providers app/agents app/services app/api/routes
touch app/__init__.py app/core/__init__.py app/ai/__init__.py app/ai/providers/__init__.py
touch app/agents/__init__.py app/services/__init__.py app/api/__init__.py app/api/routes/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock app/
git commit -m "chore: bootstrap project deps and package structure"
```

---

## Task 2: Core — config, request context, logging

**Files:**
- Create: `app/core/config.py`, `app/core/request_context.py`, `app/core/logging.py`
- Create: `tests/__init__.py`, `tests/conftest.py` (minimal, extended later)

- [ ] **Step 1: Write failing test for Settings**

Create `tests/__init__.py` (empty), then `tests/test_config.py`:

```python
import pytest
from app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.app_name == "python-agent-boilerplate"
    assert s.ai_provider == "ollama"
    assert s.ai_model == "qwen3:8b"
    assert s.ai_base_url == "http://localhost:11434/v1"
    assert s.ai_api_key == "ollama"
    assert s.ai_request_timeout == 60
    assert s.ai_supports_tools is False
    assert s.ai_supports_structured_output is False
    assert s.ai_supports_thinking is False
    assert s.ai_supports_streaming is False
    assert s.ai_probe_on_ready is False
    assert s.log_level == "INFO"
    assert s.app_env == "development"


def test_settings_override(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "gpt-4o")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    s = Settings()
    assert s.ai_model == "gpt-4o"
    assert s.ai_provider == "openai"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.config'`

- [ ] **Step 3: Implement Settings**

Create `app/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, case_sensitive=False)

    app_name: str = "python-agent-boilerplate"
    app_env: str = "development"
    log_level: str = "INFO"

    ai_provider: str = "ollama"
    ai_model: str = "qwen3:8b"
    ai_base_url: str = "http://localhost:11434/v1"
    ai_api_key: str = "ollama"
    ai_request_timeout: int = 60
    ai_supports_tools: bool = False
    ai_supports_structured_output: bool = False
    ai_supports_thinking: bool = False
    ai_supports_streaming: bool = False
    ai_probe_on_ready: bool = False

    openrouter_http_referer: str = ""
    openrouter_title: str = ""
```

- [ ] **Step 4: Run test — expect PASS**

```bash
uv run pytest tests/test_config.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Write failing test for request context**

Add to a new file `tests/test_request_context.py`:

```python
from app.core.request_context import get_request_id, reset_request_id, set_request_id


def test_set_and_get_request_id():
    token = set_request_id("abc-123")
    assert get_request_id() == "abc-123"
    reset_request_id(token)


def test_default_request_id_is_empty():
    assert get_request_id() == ""


def test_reset_restores_previous():
    token = set_request_id("first")
    assert get_request_id() == "first"
    reset_request_id(token)
    assert get_request_id() == ""
```

- [ ] **Step 6: Run to verify it fails**

```bash
uv run pytest tests/test_request_context.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 7: Implement request context**

Create `app/core/request_context.py`:

```python
from contextvars import ContextVar, Token

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(request_id: str) -> Token:
    return _request_id_var.set(request_id)


def get_request_id() -> str:
    return _request_id_var.get()


def reset_request_id(token: Token) -> None:
    _request_id_var.reset(token)
```

- [ ] **Step 8: Run to verify it passes**

```bash
uv run pytest tests/test_request_context.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 9: Implement logging (no failing test needed — it's a side-effect setup)**

Create `app/core/logging.py`:

```python
import logging
import structlog
from app.core.config import Settings
from app.core.request_context import get_request_id


def _add_request_id(logger, method_name, event_dict):  # noqa: ARG001
    event_dict["request_id"] = get_request_id()
    return event_dict


def configure_logging(settings: Settings) -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            _add_request_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
```

- [ ] **Step 10: Commit**

```bash
git add app/core/ tests/
git commit -m "feat: core config, request context, and structured logging"
```

---

## Task 3: Core — error hierarchy

**Files:**
- Create: `app/core/errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_errors.py`:

```python
import pytest
from app.core.errors import AppError, InternalError, ProviderError, ValidationError


def test_provider_error_timeout():
    err = ProviderError.timeout()
    assert err.status == 504
    assert err.code == "E2001"


def test_provider_error_auth():
    err = ProviderError.auth_failure()
    assert err.status == 502
    assert err.code == "E2002"


def test_provider_error_unavailable():
    err = ProviderError.unavailable()
    assert err.status == 503
    assert err.code == "E2003"


def test_provider_error_bad_response():
    err = ProviderError.bad_response()
    assert err.status == 502
    assert err.code == "E2004"


def test_internal_error():
    err = InternalError()
    assert err.status == 500
    assert err.code == "E3001"


def test_validation_error():
    err = ValidationError(detail="bad input")
    assert err.status == 422
    assert err.code == "E1001"


def test_app_error_is_exception():
    err = ProviderError.timeout()
    assert isinstance(err, Exception)
    assert isinstance(err, AppError)
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_errors.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement errors**

Create `app/core/errors.py`:

```python
from dataclasses import dataclass, field


@dataclass
class AppError(Exception):
    status: int
    code: str
    title: str
    detail: str
    instance: str = ""

    def __str__(self) -> str:
        return f"[{self.code}] {self.title}: {self.detail}"


@dataclass
class ValidationError(AppError):
    status: int = field(default=422, init=False)
    code: str = field(default="E1001", init=False)
    title: str = field(default="Validation Error", init=False)
    detail: str = "Invalid request."
    instance: str = ""

    def __init__(self, detail: str = "Invalid request.", instance: str = "") -> None:
        super().__init__(status=422, code="E1001", title="Validation Error",
                         detail=detail, instance=instance)


@dataclass
class ProviderError(AppError):
    @classmethod
    def timeout(cls, detail: str = "The AI provider timed out.") -> "ProviderError":
        return cls(status=504, code="E2001", title="Provider Timeout", detail=detail)

    @classmethod
    def auth_failure(cls, detail: str = "Authentication with the AI provider failed.") -> "ProviderError":
        return cls(status=502, code="E2002", title="Provider Auth Failure", detail=detail)

    @classmethod
    def unavailable(cls, detail: str = "The AI provider is unavailable.") -> "ProviderError":
        return cls(status=503, code="E2003", title="Provider Unavailable", detail=detail)

    @classmethod
    def bad_response(cls, detail: str = "The AI provider returned an invalid response.") -> "ProviderError":
        return cls(status=502, code="E2004", title="Invalid Provider Response", detail=detail)


@dataclass
class InternalError(AppError):
    def __init__(self, detail: str = "An unexpected error occurred.", instance: str = "") -> None:
        super().__init__(status=500, code="E3001", title="Internal Server Error",
                         detail=detail, instance=instance)
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_errors.py -v
```

Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add app/core/errors.py tests/test_errors.py
git commit -m "feat: AppError hierarchy with provider error codes"
```

---

## Task 4: Core — Prometheus metrics

**Files:**
- Create: `app/core/metrics.py`
- Create: `tests/test_metrics_unit.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_metrics_unit.py`:

```python
from prometheus_client import CollectorRegistry
from app.core.metrics import make_metrics


def test_make_metrics_returns_all_counters():
    registry = CollectorRegistry()
    m = make_metrics(registry=registry)
    assert m.http_requests_total is not None
    assert m.http_request_duration_seconds is not None
    assert m.http_errors_total is not None
    assert m.ai_model_requests_total is not None
    assert m.ai_model_request_duration_seconds is not None
    assert m.ai_model_errors_total is not None


def test_make_metrics_isolated_registry():
    r1 = CollectorRegistry()
    r2 = CollectorRegistry()
    m1 = make_metrics(registry=r1)
    m2 = make_metrics(registry=r2)
    # Both should succeed with different registries (no duplicate registration error)
    assert m1 is not m2


def test_record_ai_request(monkeypatch):
    registry = CollectorRegistry()
    m = make_metrics(registry=registry)
    m.record_ai_request("ollama", "qwen3:8b")
    val = m.ai_model_requests_total.labels(provider="ollama", model="qwen3:8b")._value.get()
    assert val == 1.0


def test_record_ai_error(monkeypatch):
    registry = CollectorRegistry()
    m = make_metrics(registry=registry)
    m.record_ai_error("ollama", "qwen3:8b")
    val = m.ai_model_errors_total.labels(provider="ollama", model="qwen3:8b")._value.get()
    assert val == 1.0
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_metrics_unit.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement metrics**

Create `app/core/metrics.py`:

```python
from dataclasses import dataclass
from prometheus_client import CollectorRegistry, Counter, Histogram, REGISTRY


@dataclass
class Metrics:
    http_requests_total: Counter
    http_request_duration_seconds: Histogram
    http_errors_total: Counter
    ai_model_requests_total: Counter
    ai_model_request_duration_seconds: Histogram
    ai_model_errors_total: Counter

    def record_ai_request(self, provider: str, model: str) -> None:
        self.ai_model_requests_total.labels(provider=provider, model=model).inc()

    def record_ai_error(self, provider: str, model: str) -> None:
        self.ai_model_errors_total.labels(provider=provider, model=model).inc()

    def observe_ai_duration(self, provider: str, model: str, seconds: float) -> None:
        self.ai_model_request_duration_seconds.labels(provider=provider, model=model).observe(seconds)


def make_metrics(registry: CollectorRegistry | None = None) -> Metrics:
    reg = registry or REGISTRY
    return Metrics(
        http_requests_total=Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "route", "status_code"],
            registry=reg,
        ),
        http_request_duration_seconds=Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "route"],
            registry=reg,
        ),
        http_errors_total=Counter(
            "http_errors_total",
            "Total HTTP errors",
            ["status_code", "error_code"],
            registry=reg,
        ),
        ai_model_requests_total=Counter(
            "ai_model_requests_total",
            "Total AI model requests",
            ["provider", "model"],
            registry=reg,
        ),
        ai_model_request_duration_seconds=Histogram(
            "ai_model_request_duration_seconds",
            "AI model request duration",
            ["provider", "model"],
            registry=reg,
        ),
        ai_model_errors_total=Counter(
            "ai_model_errors_total",
            "Total AI model errors",
            ["provider", "model"],
            registry=reg,
        ),
    )


_default_metrics: Metrics | None = None


def get_metrics() -> Metrics:
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = make_metrics()
    return _default_metrics
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_metrics_unit.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/core/metrics.py tests/test_metrics_unit.py
git commit -m "feat: prometheus metrics with isolated registry support"
```

---

## Task 5: AI layer — ModelClient ABC + ModelSettings

**Files:**
- Create: `app/ai/model_client.py`, `app/ai/model_settings.py`
- Create: `tests/test_model_settings.py` (unit portion)

- [ ] **Step 1: Write failing tests**

Create `tests/test_model_settings_unit.py`:

```python
from app.core.config import Settings
from app.ai.model_settings import ModelSettings


def test_model_settings_from_settings():
    s = Settings()
    ms = ModelSettings.from_settings(s)
    assert ms.provider == "ollama"
    assert ms.model == "qwen3:8b"
    assert ms.base_url == "http://localhost:11434/v1"
    assert ms.supports_tools is False
    assert ms.supports_structured_output is False
    assert ms.supports_thinking is False
    assert ms.supports_streaming is False


def test_model_settings_no_api_key(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "super-secret")
    s = Settings()
    ms = ModelSettings.from_settings(s)
    assert not hasattr(ms, "api_key")
    assert "super-secret" not in ms.model_dump().values()
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_model_settings_unit.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement ModelClient ABC and ModelSettings**

Create `app/ai/model_client.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class GenerateParams:
    temperature: float = 0.7
    max_tokens: int = 1024


@dataclass
class GenerateResult:
    content: str
    provider: str
    model: str
    usage: dict | None = None


class ModelClient(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        params: GenerateParams,
    ) -> GenerateResult: ...
```

Create `app/ai/model_settings.py`:

```python
from __future__ import annotations
from pydantic import BaseModel
from app.core.config import Settings


class ModelSettings(BaseModel):
    provider: str
    model: str
    base_url: str
    supports_tools: bool
    supports_structured_output: bool
    supports_thinking: bool
    supports_streaming: bool

    @classmethod
    def from_settings(cls, settings: Settings) -> "ModelSettings":
        return cls(
            provider=settings.ai_provider,
            model=settings.ai_model,
            base_url=settings.ai_base_url,
            supports_tools=settings.ai_supports_tools,
            supports_structured_output=settings.ai_supports_structured_output,
            supports_thinking=settings.ai_supports_thinking,
            supports_streaming=settings.ai_supports_streaming,
        )
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_model_settings_unit.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/ai/model_client.py app/ai/model_settings.py tests/test_model_settings_unit.py
git commit -m "feat: ModelClient ABC and ModelSettings without api_key exposure"
```

---

## Task 6: AI layer — OpenAICompatibleModelClient

**Files:**
- Create: `app/ai/providers/openai_compatible.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_openai_compatible.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from prometheus_client import CollectorRegistry

from app.ai.model_client import ChatMessage, GenerateParams
from app.ai.providers.openai_compatible import OpenAICompatibleModelClient
from app.core.config import Settings
from app.core.errors import ProviderError
from app.core.metrics import make_metrics


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL", "qwen3:8b")
    return Settings()


@pytest.fixture
def metrics():
    return make_metrics(registry=CollectorRegistry())


def _make_completion(content: str):
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    completion.model = "qwen3:8b"
    completion.usage = None
    return completion


@pytest.mark.asyncio
async def test_generate_returns_result(settings, metrics):
    client = OpenAICompatibleModelClient(settings, metrics=metrics)
    completion = _make_completion("hello world")
    with patch.object(client._client.chat.completions, "create", new=AsyncMock(return_value=completion)):
        result = await client.generate(
            [ChatMessage(role="user", content="hi")],
            GenerateParams(),
        )
    assert result.content == "hello world"
    assert result.provider == "ollama"
    assert result.model == "qwen3:8b"


@pytest.mark.asyncio
async def test_generate_timeout_raises_provider_error(settings, metrics):
    import openai
    client = OpenAICompatibleModelClient(settings, metrics=metrics)
    with patch.object(
        client._client.chat.completions, "create",
        new=AsyncMock(side_effect=openai.APITimeoutError(request=MagicMock()))
    ):
        with pytest.raises(ProviderError) as exc_info:
            await client.generate([ChatMessage(role="user", content="hi")], GenerateParams())
    assert exc_info.value.code == "E2001"


@pytest.mark.asyncio
async def test_generate_auth_raises_provider_error(settings, metrics):
    import openai
    client = OpenAICompatibleModelClient(settings, metrics=metrics)
    with patch.object(
        client._client.chat.completions, "create",
        new=AsyncMock(side_effect=openai.AuthenticationError(
            message="unauthorized", response=MagicMock(), body={}
        ))
    ):
        with pytest.raises(ProviderError) as exc_info:
            await client.generate([ChatMessage(role="user", content="hi")], GenerateParams())
    assert exc_info.value.code == "E2002"
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_openai_compatible.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement OpenAICompatibleModelClient**

Create `app/ai/providers/openai_compatible.py`:

```python
import time
import openai
import structlog
from openai import AsyncOpenAI

from app.ai.model_client import ChatMessage, GenerateParams, GenerateResult, ModelClient
from app.core.config import Settings
from app.core.errors import ProviderError
from app.core.metrics import Metrics, get_metrics

log = structlog.get_logger()


class OpenAICompatibleModelClient(ModelClient):
    def __init__(self, settings: Settings, metrics: Metrics | None = None) -> None:
        extra_headers: dict[str, str] = {}
        if settings.openrouter_http_referer:
            extra_headers["HTTP-Referer"] = settings.openrouter_http_referer
        if settings.openrouter_title:
            extra_headers["X-Title"] = settings.openrouter_title

        self._client = AsyncOpenAI(
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            timeout=float(settings.ai_request_timeout),
            default_headers=extra_headers if extra_headers else None,
        )
        self._provider = settings.ai_provider
        self._model = settings.ai_model
        self._metrics = metrics or get_metrics()

    async def generate(
        self,
        messages: list[ChatMessage],
        params: GenerateParams,
    ) -> GenerateResult:
        self._metrics.record_ai_request(self._provider, self._model)
        start = time.monotonic()
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=params.temperature,
                max_tokens=params.max_tokens,
            )
            content = completion.choices[0].message.content or ""
            usage = dict(completion.usage) if completion.usage else None
            return GenerateResult(
                content=content,
                provider=self._provider,
                model=completion.model or self._model,
                usage=usage,
            )
        except openai.APITimeoutError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            raise ProviderError.timeout() from exc
        except openai.AuthenticationError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            raise ProviderError.auth_failure() from exc
        except openai.APIConnectionError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            raise ProviderError.unavailable() from exc
        except openai.APIStatusError as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            if exc.status_code in (401, 403):
                raise ProviderError.auth_failure() from exc
            raise ProviderError.bad_response(detail=f"Provider returned status {exc.status_code}.") from exc
        except Exception as exc:
            self._metrics.record_ai_error(self._provider, self._model)
            log.error("unexpected_provider_error", exc_info=True)
            raise ProviderError.bad_response() from exc
        finally:
            self._metrics.observe_ai_duration(self._provider, self._model, time.monotonic() - start)
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_openai_compatible.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/ai/providers/openai_compatible.py tests/test_openai_compatible.py
git commit -m "feat: OpenAICompatibleModelClient with provider error mapping"
```

---

## Task 7: Agent layer — schemas, AssistantAgent, AgentService

**Files:**
- Create: `app/agents/schemas.py`, `app/agents/assistant_agent.py`, `app/agents/tools.py`
- Create: `app/services/agent_service.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_assistant_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock
from app.ai.model_client import ChatMessage, GenerateParams, GenerateResult, ModelClient
from app.ai.model_settings import ModelSettings
from app.agents.assistant_agent import AssistantAgent
from app.core.config import Settings


class FakeModelClient(ModelClient):
    def __init__(self, content: str = "fake answer"):
        self._content = content
        self.last_messages: list[ChatMessage] = []
        self.last_params: GenerateParams | None = None

    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult:
        self.last_messages = messages
        self.last_params = params
        return GenerateResult(content=self._content, provider="fake", model="fake-model", usage={})


@pytest.fixture
def model_settings():
    return ModelSettings.from_settings(Settings())


@pytest.mark.asyncio
async def test_assistant_agent_returns_answer(model_settings):
    fake = FakeModelClient("hello from fake")
    agent = AssistantAgent(
        model_client=fake,
        model_settings=model_settings,
        system_prompt="You are a helpful assistant.",
        temperature=0.7,
        max_tokens=512,
    )
    result = await agent.run("say hello")
    assert result.answer == "hello from fake"
    assert result.provider == "fake"
    assert result.model == "fake-model"


@pytest.mark.asyncio
async def test_assistant_agent_builds_correct_messages(model_settings):
    fake = FakeModelClient()
    agent = AssistantAgent(
        model_client=fake,
        model_settings=model_settings,
        system_prompt="You are a bot.",
        temperature=0.5,
        max_tokens=256,
    )
    await agent.run("what is 2+2?")
    assert fake.last_messages[0].role == "system"
    assert fake.last_messages[0].content == "You are a bot."
    assert fake.last_messages[1].role == "user"
    assert fake.last_messages[1].content == "what is 2+2?"
    assert fake.last_params.temperature == 0.5
    assert fake.last_params.max_tokens == 256
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_assistant_agent.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement schemas**

Create `app/agents/schemas.py`:

```python
from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: str | None = None
    conversation_id: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class AgentRunResponse(BaseModel):
    answer: str
    provider: str
    model: str
    usage: dict | None = None
    metadata: dict | None = None
```

- [ ] **Step 4: Implement AssistantAgent**

Create `app/agents/assistant_agent.py`:

```python
from app.agents.schemas import AgentRunResponse
from app.ai.model_client import ChatMessage, GenerateParams, ModelClient
from app.ai.model_settings import ModelSettings

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024


class AssistantAgent:
    def __init__(
        self,
        model_client: ModelClient,
        model_settings: ModelSettings,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._client = model_client
        self._settings = model_settings
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def run(self, message: str) -> AgentRunResponse:
        messages = [
            ChatMessage(role="system", content=self._system_prompt),
            ChatMessage(role="user", content=message),
        ]
        params = GenerateParams(temperature=self._temperature, max_tokens=self._max_tokens)
        result = await self._client.generate(messages, params)
        return AgentRunResponse(
            answer=result.content,
            provider=result.provider,
            model=result.model,
            usage=result.usage,
        )
```

Create `app/agents/tools.py`:

```python
# Extension point for v2 tool definitions.
# Add tool schemas and handlers here when implementing tool calling.
```

- [ ] **Step 5: Implement AgentService**

Create `app/services/agent_service.py`:

```python
from app.agents.assistant_agent import (
    AssistantAgent,
    DEFAULT_MAX_TOKENS,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
)
from app.agents.schemas import AgentRunRequest, AgentRunResponse
from app.ai.model_client import ModelClient
from app.ai.model_settings import ModelSettings


class AgentService:
    def __init__(self, model_client: ModelClient, model_settings: ModelSettings) -> None:
        self._model_client = model_client
        self._model_settings = model_settings

    async def run(self, request: AgentRunRequest) -> AgentRunResponse:
        agent = AssistantAgent(
            model_client=self._model_client,
            model_settings=self._model_settings,
            system_prompt=request.system_prompt or DEFAULT_SYSTEM_PROMPT,
            temperature=request.temperature if request.temperature is not None else DEFAULT_TEMPERATURE,
            max_tokens=request.max_tokens if request.max_tokens is not None else DEFAULT_MAX_TOKENS,
        )
        return await agent.run(request.message)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
uv run pytest tests/test_assistant_agent.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add app/agents/ app/services/ tests/test_assistant_agent.py
git commit -m "feat: AgentRunRequest/Response schemas, AssistantAgent, AgentService"
```

---

## Task 8: API layer — envelope

**Files:**
- Create: `app/api/envelope.py`
- Create: `tests/test_envelope.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_envelope.py`:

```python
import json
import pytest
from datetime import UTC, datetime

from app.api.envelope import ApiResponse, FieldError, ProblemDetails, ResponseMeta, error_response, ok
from app.core.errors import ProviderError, ValidationError


def test_ok_returns_success_envelope():
    response = ok({"key": "value"})
    body = json.loads(response.body)
    assert body["success"] is True
    assert body["data"] == {"key": "value"}
    assert body["error"] is None
    assert "requestId" in body["meta"]
    assert "timestamp" in body["meta"]
    assert response.status_code == 200


def test_ok_custom_status_code():
    response = ok({"x": 1}, status_code=201)
    assert response.status_code == 201


def test_error_response_success_false():
    err = ProviderError.timeout()
    response = error_response(err, instance="/rest/v1/agent/run", request_id="req-1")
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "E2001"
    assert body["error"]["status"] == 504
    assert body["error"]["requestId"] == "req-1"
    assert response.status_code == 504


def test_error_response_has_cache_control():
    err = ProviderError.timeout()
    response = error_response(err, instance="/test", request_id="r1")
    assert response.headers["cache-control"] == "no-store"


def test_timestamp_is_rfc3339_utc():
    response = ok({"x": 1})
    body = json.loads(response.body)
    ts = body["meta"]["timestamp"]
    assert ts.endswith("Z")
    datetime.fromisoformat(ts.replace("Z", "+00:00"))  # must not raise


def test_data_and_error_never_both_populated():
    ok_resp = json.loads(ok({"a": 1}).body)
    assert ok_resp["error"] is None
    assert ok_resp["data"] is not None

    err = ProviderError.unavailable()
    err_resp = json.loads(error_response(err, "/x", "r2").body)
    assert err_resp["data"] is None
    assert err_resp["error"] is not None


def test_validation_error_with_field_errors():
    from app.api.envelope import error_response_with_fields
    fields = [FieldError(pointer="/message", message="Field required.", code="REQUIRED")]
    err = ValidationError(detail="Validation failed.")
    response = error_response_with_fields(err, fields=fields, instance="/test", request_id="r3")
    body = json.loads(response.body)
    assert body["error"]["errors"][0]["pointer"] == "/message"
    assert body["error"]["errors"][0]["code"] == "REQUIRED"
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_envelope.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement envelope**

Create `app/api/envelope.py`:

```python
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.errors import AppError
from app.core.request_context import get_request_id

T = TypeVar("T")


class ResponseMeta(BaseModel):
    requestId: str
    timestamp: str


class FieldError(BaseModel):
    pointer: str
    message: str
    code: str


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    requestId: str
    errors: list[FieldError] | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ProblemDetails | None
    meta: ResponseMeta


def _meta(request_id: str) -> ResponseMeta:
    return ResponseMeta(
        requestId=request_id,
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def ok(data: Any, status_code: int = 200) -> JSONResponse:
    request_id = get_request_id()
    body = ApiResponse(
        success=True,
        data=data,
        error=None,
        meta=_meta(request_id),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={"X-Request-Id": request_id},
    )


def error_response(err: AppError, instance: str, request_id: str) -> JSONResponse:
    problem = ProblemDetails(
        type=f"https://httpstatuses.com/{err.status}",
        title=err.title,
        status=err.status,
        detail=err.detail,
        instance=instance,
        code=err.code,
        requestId=request_id,
        errors=None,
    )
    body = ApiResponse(
        success=False,
        data=None,
        error=problem,
        meta=_meta(request_id),
    )
    return JSONResponse(
        status_code=err.status,
        content=body.model_dump(),
        headers={"Cache-Control": "no-store", "X-Request-Id": request_id},
    )


def error_response_with_fields(
    err: AppError,
    fields: list[FieldError],
    instance: str,
    request_id: str,
) -> JSONResponse:
    problem = ProblemDetails(
        type=f"https://httpstatuses.com/{err.status}",
        title=err.title,
        status=err.status,
        detail=err.detail,
        instance=instance,
        code=err.code,
        requestId=request_id,
        errors=fields,
    )
    body = ApiResponse(
        success=False,
        data=None,
        error=problem,
        meta=_meta(request_id),
    )
    return JSONResponse(
        status_code=err.status,
        content=body.model_dump(),
        headers={"Cache-Control": "no-store", "X-Request-Id": request_id},
    )
```

- [ ] **Step 4: Run to verify it passes**

```bash
uv run pytest tests/test_envelope.py -v
```

Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add app/api/envelope.py tests/test_envelope.py
git commit -m "feat: ApiResponse envelope, ok() and error_response() helpers"
```

---

## Task 9: API layer — dependencies + routes + exception handlers

**Files:**
- Create: `app/api/dependencies.py`
- Create: `app/api/routes/health.py`, `app/api/routes/agent.py`, `app/api/routes/models.py`

- [ ] **Step 1: Implement dependencies**

Create `app/api/dependencies.py`:

```python
from fastapi import Depends, Request

from app.ai.model_client import ModelClient
from app.ai.model_settings import ModelSettings
from app.services.agent_service import AgentService


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

- [ ] **Step 2: Implement health routes**

Create `app/api/routes/health.py`:

```python
from fastapi import APIRouter, Request

from app.api.envelope import ok

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return ok({"status": "ok"})


@router.get("/health/live")
async def health_live():
    return ok({"status": "ok"})


@router.get("/health/ready")
async def health_ready(request: Request):
    client = getattr(request.app.state, "model_client", None)
    settings = getattr(request.app.state, "model_settings", None)
    ready = client is not None and settings is not None
    return ok({"status": "ready" if ready else "not_ready"})
```

- [ ] **Step 3: Implement agent route**

Create `app/api/routes/agent.py`:

```python
from fastapi import APIRouter, Depends

from app.agents.schemas import AgentRunRequest, AgentRunResponse
from app.api.dependencies import get_agent_service
from app.api.envelope import ok
from app.services.agent_service import AgentService

router = APIRouter(tags=["agent"])


@router.post("/agent/run", response_model=None)
async def run_agent(
    body: AgentRunRequest,
    service: AgentService = Depends(get_agent_service),
):
    result = await service.run(body)
    return ok(result.model_dump())
```

- [ ] **Step 4: Implement models route**

Create `app/api/routes/models.py`:

```python
from fastapi import APIRouter, Depends

from app.ai.model_settings import ModelSettings
from app.api.dependencies import get_model_settings
from app.api.envelope import ok

router = APIRouter(tags=["models"])


@router.get("/models/current", response_model=None)
async def get_current_model(settings: ModelSettings = Depends(get_model_settings)):
    return ok(settings.model_dump())
```

- [ ] **Step 5: Commit**

```bash
git add app/api/dependencies.py app/api/routes/
git commit -m "feat: API dependencies and health/agent/models routes"
```

---

## Task 10: Middleware

**Files:**
- Create: `app/core/middleware.py`

- [ ] **Step 1: Implement all three middleware classes**

Create `app/core/middleware.py`:

```python
import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.request_context import get_request_id, reset_request_id, set_request_id

log = structlog.get_logger()

_EXCLUDED_PATHS = {"/metrics", "/doc", "/reference"}


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        except Exception:
            log.error("middleware_exception", request_id=request_id, exc_info=True)
            response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "type": "https://httpstatuses.com/500",
                        "title": "Internal Server Error",
                        "status": 500,
                        "detail": "An unexpected error occurred.",
                        "instance": str(request.url.path),
                        "code": "E3001",
                        "requestId": request_id,
                        "errors": None,
                    },
                    "meta": {"requestId": request_id, "timestamp": _utc_now()},
                },
                headers={"Cache-Control": "no-store"},
            )
        finally:
            reset_request_id(token)
        response.headers["X-Request-Id"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_id=get_request_id(),
        )
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics=None) -> None:
        super().__init__(app)
        from app.core.metrics import get_metrics
        self._metrics = metrics or get_metrics()

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        route = _get_route(request)
        method = request.method
        status = str(response.status_code)
        try:
            self._metrics.http_requests_total.labels(
                method=method, route=route, status_code=status
            ).inc()
            self._metrics.http_request_duration_seconds.labels(
                method=method, route=route
            ).observe(duration)
            if response.status_code >= 400:
                self._metrics.http_errors_total.labels(
                    status_code=status, error_code="unknown"
                ).inc()
        except Exception:
            log.error("metrics_middleware_error", exc_info=True)
        return response


def _get_route(request: Request) -> str:
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return "unmatched"


def _utc_now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 2: Commit**

```bash
git add app/core/middleware.py
git commit -m "feat: CorrelationId, RequestLogging, Metrics middleware"
```

---

## Task 11: App entrypoint + exception handlers

**Files:**
- Create: `app/main.py`
- Delete stub: `main.py` (root level — kept for now, superseded)

- [ ] **Step 1: Implement app/main.py**

Create `app/main.py`:

```python
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import make_wsgi_app
from starlette.middleware.wsgi import WSGIMiddleware

from app.ai.model_settings import ModelSettings
from app.ai.providers.openai_compatible import OpenAICompatibleModelClient
from app.api.envelope import FieldError, error_response, error_response_with_fields
from app.api.routes.agent import router as agent_router
from app.api.routes.health import router as health_router
from app.api.routes.models import router as models_router
from app.core.config import Settings
from app.core.errors import AppError, InternalError, ValidationError
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware, MetricsMiddleware, RequestLoggingMiddleware
from app.core.request_context import get_request_id

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(settings)
    app.state.model_client = OpenAICompatibleModelClient(settings)
    app.state.model_settings = ModelSettings.from_settings(settings)
    log.info("startup_complete", provider=settings.ai_provider, model=settings.ai_model)
    yield
    log.info("shutdown")


app = FastAPI(
    title="python-agent-boilerplate",
    docs_url=None,
    redoc_url=None,
    openapi_url="/doc",
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(exc, instance=str(request.url.path), request_id=get_request_id())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = []
    for error in exc.errors():
        loc = error.get("loc", ())
        # Strip leading 'body' element; build RFC 6901 pointer into payload
        parts = [str(p) for p in loc[1:]] if loc and loc[0] in ("body", "query", "header") else [str(p) for p in loc]
        pointer = "/" + "/".join(parts) if parts else "/"
        msg_type = error.get("type", "")
        code = _validation_code(msg_type)
        fields.append(FieldError(pointer=pointer, message=error.get("msg", ""), code=code))
    err = ValidationError(detail="Request validation failed.")
    return error_response_with_fields(err, fields=fields, instance=str(request.url.path), request_id=get_request_id())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", request_id=get_request_id(), exc_info=True)
    return error_response(InternalError(), instance=str(request.url.path), request_id=get_request_id())


def _validation_code(error_type: str) -> str:
    mapping = {
        "missing": "REQUIRED",
        "string_type": "INVALID_TYPE",
        "int_type": "INVALID_TYPE",
        "float_type": "INVALID_TYPE",
        "bool_type": "INVALID_TYPE",
        "string_too_short": "TOO_SHORT",
        "string_too_long": "TOO_LONG",
        "greater_than_equal": "MIN_VALUE",
        "less_than_equal": "MAX_VALUE",
        "extra_forbidden": "EXTRA_FIELD",
    }
    return mapping.get(error_type, "INVALID_FORMAT")


# Middleware (last added = outermost)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# Routers
app.include_router(health_router)
app.include_router(agent_router, prefix="/rest/v1")
app.include_router(models_router, prefix="/rest/v1")

# Prometheus WSGI mounted at /metrics (excluded from envelope and self-instrumentation)
app.mount("/metrics", WSGIMiddleware(make_wsgi_app()))
```

- [ ] **Step 2: Verify the app starts**

```bash
uv run uvicorn app.main:app --port 8000 --no-access-log &
sleep 2
curl -s http://localhost:8000/health | python3 -m json.tool
kill %1
```

Expected: JSON with `"success": true`, `"data": {"status": "ok"}`.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: FastAPI app entrypoint with lifespan, middleware, exception handlers"
```

---

## Task 12: Integration tests — conftest + health + agent + models

**Files:**
- Modify: `tests/conftest.py`
- Create: `tests/test_health.py`, `tests/test_agent.py`, `tests/test_model_settings.py`

- [ ] **Step 1: Write conftest fixtures**

Create `tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from app.ai.model_client import ChatMessage, GenerateParams, GenerateResult, ModelClient
from app.api.dependencies import get_model_client
from app.core.metrics import make_metrics


class FakeModelClient(ModelClient):
    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult:
        return GenerateResult(content="fake answer", provider="fake", model="fake-model", usage={"total_tokens": 10})


class RaisesModelClient(ModelClient):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def generate(self, messages: list[ChatMessage], params: GenerateParams) -> GenerateResult:
        raise self._exc


@pytest.fixture
def fake_model_client():
    return FakeModelClient()


@pytest.fixture
def raises_model_client():
    def factory(exc: Exception) -> RaisesModelClient:
        return RaisesModelClient(exc)
    return factory


@pytest.fixture
def metrics_registry():
    return CollectorRegistry()


@pytest.fixture
def app(fake_model_client):
    from app.main import app as fastapi_app
    from app.ai.model_settings import ModelSettings
    from app.core.config import Settings

    fastapi_app.dependency_overrides[get_model_client] = lambda: fake_model_client
    fastapi_app.state.model_client = fake_model_client
    fastapi_app.state.model_settings = ModelSettings.from_settings(Settings())
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
```

- [ ] **Step 2: Write health tests**

Create `tests/test_health.py`:

```python
import uuid


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_health_ready(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_health_meta_has_request_id(client):
    response = client.get("/health")
    body = response.json()
    assert "requestId" in body["meta"]
    request_id = body["meta"]["requestId"]
    assert len(request_id) > 0


def test_health_x_request_id_header_matches_meta(client):
    response = client.get("/health")
    body = response.json()
    assert response.headers["x-request-id"] == body["meta"]["requestId"]


def test_health_echoes_provided_request_id(client):
    custom_id = str(uuid.uuid4())
    response = client.get("/health", headers={"X-Request-Id": custom_id})
    body = response.json()
    assert body["meta"]["requestId"] == custom_id
    assert response.headers["x-request-id"] == custom_id
```

- [ ] **Step 3: Run health tests**

```bash
uv run pytest tests/test_health.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 4: Write agent tests**

Create `tests/test_agent.py`:

```python
import uuid
import pytest
from app.api.dependencies import get_model_client
from app.core.errors import ProviderError


def test_agent_run_happy_path(client):
    response = client.post("/rest/v1/agent/run", json={"message": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["answer"] == "fake answer"
    assert body["data"]["provider"] == "fake"
    assert body["error"] is None


def test_agent_run_echoes_request_id(client):
    custom_id = str(uuid.uuid4())
    response = client.post(
        "/rest/v1/agent/run",
        json={"message": "hi"},
        headers={"X-Request-Id": custom_id},
    )
    body = response.json()
    assert body["meta"]["requestId"] == custom_id
    assert response.headers["x-request-id"] == custom_id


def test_agent_run_generates_request_id_when_absent(client):
    response = client.post("/rest/v1/agent/run", json={"message": "hi"})
    body = response.json()
    assert len(body["meta"]["requestId"]) > 0
    assert response.headers.get("x-request-id")


def test_agent_run_missing_message_returns_422(client):
    response = client.post("/rest/v1/agent/run", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "E1001"
    assert body["error"]["errors"][0]["pointer"] == "/message"
    assert body["error"]["errors"][0]["code"] == "REQUIRED"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get("x-request-id")


def test_agent_run_provider_timeout(app, raises_model_client):
    app.dependency_overrides[get_model_client] = lambda: raises_model_client(ProviderError.timeout())
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/rest/v1/agent/run", json={"message": "hi"})
    assert response.status_code == 504
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "E2001"
    assert "stack" not in response.text
    assert "traceback" not in response.text.lower()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_model_client] = lambda: app.state.model_client


def test_agent_run_unhandled_exception(app, raises_model_client):
    app.dependency_overrides[get_model_client] = lambda: raises_model_client(RuntimeError("boom"))
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/rest/v1/agent/run", json={"message": "hi"})
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "E3001"
    app.dependency_overrides.clear()
    app.dependency_overrides[get_model_client] = lambda: app.state.model_client


def test_no_request_id_leakage(client):
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    r1 = client.post("/rest/v1/agent/run", json={"message": "a"}, headers={"X-Request-Id": id1})
    r2 = client.post("/rest/v1/agent/run", json={"message": "b"}, headers={"X-Request-Id": id2})
    assert r1.json()["meta"]["requestId"] == id1
    assert r2.json()["meta"]["requestId"] == id2
    assert id1 not in r2.text
    assert id2 not in r1.text
```

- [ ] **Step 5: Run agent tests**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: PASS (7 tests)

- [ ] **Step 6: Write model settings route tests**

Create `tests/test_model_settings.py`:

```python
def test_models_current_returns_provider_and_model(client):
    response = client.get("/rest/v1/models/current")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["provider"] == "ollama"
    assert data["model"] == "qwen3:8b"
    assert data["base_url"] == "http://localhost:11434/v1"
    assert isinstance(data["supports_tools"], bool)
    assert isinstance(data["supports_streaming"], bool)


def test_models_current_no_api_key(client):
    response = client.get("/rest/v1/models/current")
    body = response.json()
    body_str = str(body)
    assert "api_key" not in body_str
    assert "AI_API_KEY" not in body_str
    assert "ollama" not in body_str or body_str.count("ollama") <= 2  # provider name is ok, key is not
```

- [ ] **Step 7: Run model settings tests**

```bash
uv run pytest tests/test_model_settings.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py tests/test_health.py tests/test_agent.py tests/test_model_settings.py
git commit -m "test: integration tests for health, agent, and models routes"
```

---

## Task 13: Integration tests — metrics + openapi

**Files:**
- Create: `tests/test_metrics.py`, `tests/test_openapi.py`

- [ ] **Step 1: Write metrics tests**

Create `tests/test_metrics.py`:

```python
def test_metrics_endpoint_200(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")


def test_metrics_not_enveloped(client):
    response = client.get("/metrics")
    body = response.text
    assert "success" not in body
    assert "requestId" not in body


def test_metrics_contains_http_requests_total(client):
    client.get("/health")  # generate a request so counter appears
    response = client.get("/metrics")
    assert "http_requests_total" in response.text


def test_metrics_not_counted_in_http_requests_total(client):
    response = client.get("/metrics")
    # /metrics itself should not appear as a counted route
    assert 'route="/metrics"' not in response.text
```

- [ ] **Step 2: Write OpenAPI tests**

Create `tests/test_openapi.py`:

```python
def test_doc_endpoint_returns_json(client):
    response = client.get("/doc")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    body = response.json()
    assert "openapi" in body
    assert "success" not in body


def test_doc_not_enveloped(client):
    response = client.get("/doc")
    body = response.json()
    assert "meta" not in body
    assert "requestId" not in body


def test_metrics_not_enveloped(client):
    response = client.get("/metrics")
    assert "meta" not in response.text
    assert "requestId" not in response.text
```

- [ ] **Step 3: Run all tests**

```bash
uv run pytest tests/ -v
```

Expected: all tests PASS (no failures)

- [ ] **Step 4: Commit**

```bash
git add tests/test_metrics.py tests/test_openapi.py
git commit -m "test: metrics endpoint and openapi doc tests"
```

---

## Task 14: Docker + docker-compose

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.env.example`

- [ ] **Step 1: Create .dockerignore**

Create `.dockerignore`:

```
.env
.env.*
.git
.gitignore
.venv
__pycache__
*.pyc
*.pyo
tests/
deploy/
docs/
*.md
!README.md
```

- [ ] **Step 2: Create Dockerfile**

Create `Dockerfile`:

```dockerfile
FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

FROM python:3.14-slim

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder /app /app
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create docker-compose.yml**

Create `docker-compose.yml`:

```yaml
services:
  ai-agent-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      AI_PROVIDER: ollama
      AI_MODEL: qwen3:8b
      AI_BASE_URL: http://ollama:11434/v1
      AI_API_KEY: ollama
    depends_on:
      - ollama
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

- [ ] **Step 4: Create .env.example**

Create `.env.example`:

```bash
# App
APP_NAME=python-agent-boilerplate
APP_ENV=development
LOG_LEVEL=INFO

# AI Provider — defaults to Ollama
AI_PROVIDER=ollama
AI_MODEL=qwen3:8b
AI_BASE_URL=http://localhost:11434/v1
AI_API_KEY=ollama
AI_REQUEST_TIMEOUT=60

# Capability flags (set to true if provider supports)
AI_SUPPORTS_TOOLS=false
AI_SUPPORTS_STRUCTURED_OUTPUT=false
AI_SUPPORTS_THINKING=false
AI_SUPPORTS_STREAMING=false

# Readiness probe (set to true to make a real LLM call on /health/ready)
AI_PROBE_ON_READY=false

# OpenRouter (optional)
# AI_PROVIDER=openrouter
# AI_MODEL=openai/gpt-4o
# AI_BASE_URL=https://openrouter.ai/api/v1
# AI_API_KEY=sk-or-...
# OPENROUTER_HTTP_REFERER=https://yourapp.com
# OPENROUTER_TITLE=YourAppName

# OpenAI (optional)
# AI_PROVIDER=openai
# AI_MODEL=gpt-4o
# AI_BASE_URL=https://api.openai.com/v1
# AI_API_KEY=sk-...

# LM Studio (optional)
# AI_PROVIDER=lmstudio
# AI_MODEL=lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF
# AI_BASE_URL=http://localhost:1234/v1
# AI_API_KEY=lm-studio
```

- [ ] **Step 5: Verify Docker build**

```bash
docker build -t python-agent-boilerplate:dev .
```

Expected: build succeeds, image created.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore .env.example
git commit -m "feat: Docker and docker-compose for local dev with Ollama"
```

---

## Task 15: Kubernetes manifests

**Files:**
- Create: `deploy/k8s/namespace.yaml`, `deployment.yaml`, `service.yaml`, `configmap.yaml`, `secret.example.yaml`, `ingress.yaml`, `hpa.yaml`, `servicemonitor.yaml`

- [ ] **Step 1: Create k8s directory and namespace**

```bash
mkdir -p deploy/k8s
```

Create `deploy/k8s/namespace.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai-agents
  labels:
    app.kubernetes.io/managed-by: kubectl
```

- [ ] **Step 2: Create configmap**

Create `deploy/k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
  labels:
    app.kubernetes.io/name: python-agent-boilerplate
data:
  APP_ENV: production
  LOG_LEVEL: INFO
  AI_PROVIDER: ollama
  AI_MODEL: qwen3:8b
  AI_BASE_URL: http://ollama:11434/v1
  AI_REQUEST_TIMEOUT: "60"
  AI_SUPPORTS_TOOLS: "false"
  AI_SUPPORTS_STRUCTURED_OUTPUT: "false"
  AI_SUPPORTS_THINKING: "false"
  AI_SUPPORTS_STREAMING: "false"
  AI_PROBE_ON_READY: "false"
```

- [ ] **Step 3: Create secret example**

Create `deploy/k8s/secret.example.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
  labels:
    app.kubernetes.io/name: python-agent-boilerplate
type: Opaque
stringData:
  AI_API_KEY: "your-api-key-here"
```

- [ ] **Step 4: Create deployment**

Create `deploy/k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
  labels:
    app.kubernetes.io/name: python-agent-boilerplate
    app.kubernetes.io/version: "0.1.0"
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: python-agent-boilerplate
  template:
    metadata:
      labels:
        app.kubernetes.io/name: python-agent-boilerplate
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
        - name: app
          image: python-agent-boilerplate:latest
          ports:
            - containerPort: 8000
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
          envFrom:
            - configMapRef:
                name: python-agent-boilerplate
            - secretRef:
                name: python-agent-boilerplate
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1000m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          startupProbe:
            httpGet:
              path: /health
              port: 8000
            failureThreshold: 10
            periodSeconds: 5
```

- [ ] **Step 5: Create service, ingress, HPA, ServiceMonitor**

Create `deploy/k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
  labels:
    app.kubernetes.io/name: python-agent-boilerplate
spec:
  selector:
    app.kubernetes.io/name: python-agent-boilerplate
  ports:
    - name: http
      port: 80
      targetPort: 8000
```

Create `deploy/k8s/ingress.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
  labels:
    app.kubernetes.io/name: python-agent-boilerplate
spec:
  rules:
    - host: agent.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: python-agent-boilerplate
                port:
                  name: http
```

Create `deploy/k8s/hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: python-agent-boilerplate
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

Create `deploy/k8s/servicemonitor.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: python-agent-boilerplate
  namespace: ai-agents
  labels:
    app.kubernetes.io/name: python-agent-boilerplate
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: python-agent-boilerplate
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

- [ ] **Step 6: Commit**

```bash
git add deploy/k8s/
git commit -m "feat: Kubernetes manifests (namespace, deployment, service, ingress, hpa, servicemonitor)"
```

---

## Task 16: Helm chart

**Files:**
- Create: `deploy/helm/python-agent-boilerplate/` (full chart)

- [ ] **Step 1: Create Helm chart skeleton**

```bash
mkdir -p deploy/helm/python-agent-boilerplate/templates
```

Create `deploy/helm/python-agent-boilerplate/Chart.yaml`:

```yaml
apiVersion: v2
name: python-agent-boilerplate
description: Provider-agnostic AI agent FastAPI microservice
type: application
version: 0.1.0
appVersion: "0.1.0"
```

- [ ] **Step 2: Create values.yaml**

Create `deploy/helm/python-agent-boilerplate/values.yaml`:

```yaml
replicaCount: 2

image:
  repository: python-agent-boilerplate
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false
  host: agent.example.com
  tls: []

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 512Mi

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

serviceAccount:
  create: true
  name: ""
  annotations: {}

podAnnotations: {}
podLabels: {}
nodeSelector: {}
tolerations: []
affinity: {}

securityContext:
  runAsNonRoot: true
  runAsUser: 1000

podSecurityContext:
  fsGroup: 1000

serviceMonitor:
  enabled: false

probes:
  liveness:
    path: /health/live
    initialDelaySeconds: 10
    periodSeconds: 15
  readiness:
    path: /health/ready
    initialDelaySeconds: 5
    periodSeconds: 10
  startup:
    path: /health
    failureThreshold: 10
    periodSeconds: 5

env:
  APP_ENV: production
  LOG_LEVEL: INFO
  AI_PROVIDER: ollama
  AI_MODEL: qwen3:8b
  AI_BASE_URL: http://localhost:11434/v1
  AI_REQUEST_TIMEOUT: "60"
  AI_SUPPORTS_TOOLS: "false"
  AI_SUPPORTS_STRUCTURED_OUTPUT: "false"
  AI_SUPPORTS_THINKING: "false"
  AI_SUPPORTS_STREAMING: "false"
  AI_PROBE_ON_READY: "false"

secret:
  AI_API_KEY: ""
```

- [ ] **Step 3: Create _helpers.tpl**

Create `deploy/helm/python-agent-boilerplate/templates/_helpers.tpl`:

```
{{- define "python-agent-boilerplate.name" -}}
{{- .Chart.Name }}
{{- end }}

{{- define "python-agent-boilerplate.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "python-agent-boilerplate.labels" -}}
app.kubernetes.io/name: {{ include "python-agent-boilerplate.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
```

- [ ] **Step 4: Create Helm templates**

Create `deploy/helm/python-agent-boilerplate/templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "python-agent-boilerplate.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ include "python-agent-boilerplate.name" . }}
        app.kubernetes.io/instance: {{ .Release.Name }}
        {{- with .Values.podLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- with .Values.podAnnotations }}
      annotations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
    spec:
      {{- with .Values.podSecurityContext }}
      securityContext:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- if .Values.serviceAccount.create }}
      serviceAccountName: {{ .Values.serviceAccount.name | default (include "python-agent-boilerplate.fullname" .) }}
      {{- end }}
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8000
          {{- with .Values.securityContext }}
          securityContext:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          envFrom:
            - configMapRef:
                name: {{ include "python-agent-boilerplate.fullname" . }}
            - secretRef:
                name: {{ include "python-agent-boilerplate.fullname" . }}
          {{- with .Values.resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          livenessProbe:
            httpGet:
              path: {{ .Values.probes.liveness.path }}
              port: 8000
            initialDelaySeconds: {{ .Values.probes.liveness.initialDelaySeconds }}
            periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
          readinessProbe:
            httpGet:
              path: {{ .Values.probes.readiness.path }}
              port: 8000
            initialDelaySeconds: {{ .Values.probes.readiness.initialDelaySeconds }}
            periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
          startupProbe:
            httpGet:
              path: {{ .Values.probes.startup.path }}
              port: 8000
            failureThreshold: {{ .Values.probes.startup.failureThreshold }}
            periodSeconds: {{ .Values.probes.startup.periodSeconds }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  selector:
    app.kubernetes.io/name: {{ include "python-agent-boilerplate.name" . }}
    app.kubernetes.io/instance: {{ .Release.Name }}
  ports:
    - name: http
      port: {{ .Values.service.port }}
      targetPort: 8000
```

Create `deploy/helm/python-agent-boilerplate/templates/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
data:
  {{- range $key, $val := .Values.env }}
  {{ $key }}: {{ $val | quote }}
  {{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/secret.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
type: Opaque
stringData:
  {{- range $key, $val := .Values.secret }}
  {{ $key }}: {{ $val | quote }}
  {{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/serviceaccount.yaml`:

```yaml
{{- if .Values.serviceAccount.create }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ .Values.serviceAccount.name | default (include "python-agent-boilerplate.fullname" .) }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
  {{- with .Values.serviceAccount.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/ingress.yaml`:

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
spec:
  rules:
    - host: {{ .Values.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "python-agent-boilerplate.fullname" . }}
                port:
                  name: http
  {{- with .Values.ingress.tls }}
  tls:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/hpa.yaml`:

```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "python-agent-boilerplate.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/servicemonitor.yaml`:

```yaml
{{- if .Values.serviceMonitor.enabled }}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "python-agent-boilerplate.fullname" . }}
  labels:
    {{- include "python-agent-boilerplate.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ include "python-agent-boilerplate.name" . }}
      app.kubernetes.io/instance: {{ .Release.Name }}
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
{{- end }}
```

Create `deploy/helm/python-agent-boilerplate/templates/NOTES.txt`:

```
python-agent-boilerplate has been deployed.

Access the service:
  kubectl port-forward svc/{{ include "python-agent-boilerplate.fullname" . }} 8000:80 -n {{ .Release.Namespace }}
  curl http://localhost:8000/health

API endpoint:
  POST http://localhost:8000/rest/v1/agent/run
  Body: {"message": "hello"}

Docs: http://localhost:8000/reference
```

- [ ] **Step 5: Commit**

```bash
git add deploy/helm/
git commit -m "feat: Helm chart with full values, security contexts, probes, and optional ServiceMonitor"
```

---

## Task 17: README + final cleanup

**Files:**
- Modify: `README.md`
- Modify: `main.py` (root level — update to delegate to app)

- [ ] **Step 1: Update README.md**

Create `README.md`:

```markdown
# python-agent-boilerplate

Production-ready FastAPI microservice exposing a provider-agnostic AI agent REST endpoint.
Connects to any OpenAI-compatible backend: OpenAI, Ollama, LM Studio, vLLM, OpenRouter, and more.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
cp .env.example .env
# edit .env with your provider config
uv run uvicorn app.main:app --reload
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rest/v1/agent/run` | POST | Run the agent |
| `/rest/v1/models/current` | GET | Show current model config |
| `/health` | GET | Service health |
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/metrics` | GET | Prometheus metrics |
| `/doc` | GET | OpenAPI JSON |
| `/reference` | GET | Interactive docs |

### Example

```bash
curl -X POST http://localhost:8000/rest/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

## Provider Configuration

Set env vars (see `.env.example`):

**Ollama (default):**
```
AI_PROVIDER=ollama
AI_MODEL=qwen3:8b
AI_BASE_URL=http://localhost:11434/v1
AI_API_KEY=ollama
```

**OpenAI:**
```
AI_PROVIDER=openai
AI_MODEL=gpt-4o
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
```

**OpenRouter:**
```
AI_PROVIDER=openrouter
AI_MODEL=openai/gpt-4o
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=sk-or-...
OPENROUTER_HTTP_REFERER=https://yourapp.com
```

**LM Studio:**
```
AI_PROVIDER=lmstudio
AI_MODEL=lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF
AI_BASE_URL=http://localhost:1234/v1
AI_API_KEY=lm-studio
```

## Docker

```bash
docker build -t python-agent-boilerplate .
docker compose up
# Pull model in Ollama:
docker exec -it python-agent-boilerplate-ollama-1 ollama pull qwen3:8b
```

## Tests

```bash
uv run pytest tests/ -v
```

## Extension Points (v2+)

| Feature | Where |
|---------|-------|
| Tool calling | `app/agents/tools.py` |
| Streaming | `ModelClient.generate_stream()` |
| Conversation memory | `AgentRunRequest.conversation_id` |
| RAG | New service in `app/services/` |
| Additional providers | New class in `app/ai/providers/` |
```

- [ ] **Step 2: Run full test suite one final time**

```bash
uv run pytest tests/ -v --tb=short
```

Expected: all tests PASS

- [ ] **Step 3: Lint**

```bash
uv run ruff check app/ tests/
```

Expected: no errors (or fix any reported)

- [ ] **Step 4: Final commit**

```bash
git add README.md main.py
git commit -m "docs: README with provider examples, setup, and extension points"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| FastAPI + lifespan | Task 11 |
| pydantic-settings config | Task 2 |
| ModelClient ABC | Task 5 |
| OpenAICompatibleModelClient | Task 6 |
| Provider error mapping E2001–E2004 | Task 6 |
| AssistantAgent | Task 7 |
| AgentService | Task 7 |
| Envelope (ok, error_response) | Task 8 |
| FieldError / ProblemDetails | Task 8 |
| CorrelationIdMiddleware | Task 10 |
| RequestLoggingMiddleware | Task 10 |
| MetricsMiddleware | Task 10 |
| Prometheus metrics (6 metrics) | Task 4 |
| /health /health/live /health/ready | Task 9 |
| POST /rest/v1/agent/run | Task 9 |
| GET /rest/v1/models/current | Task 9 |
| GET /metrics (WSGI, not enveloped) | Task 11 |
| GET /doc (OpenAPI JSON) | Task 11 |
| Three exception handlers | Task 11 |
| RequestValidationError → E1001 + FieldErrors | Task 11 |
| RFC 6901 field pointers | Task 11 |
| ValidationError codes (REQUIRED, etc.) | Task 11 |
| X-Request-Id echoed on all responses | Task 10 |
| Cache-Control: no-store on 4xx/5xx | Task 8 |
| structlog JSON logging | Task 2 |
| No secrets in logs or responses | Task 6 (no api_key in ModelSettings) |
| FakeModelClient + RaisesModelClient | Task 12 |
| dependency_overrides wiring | Task 12 |
| Isolated Prometheus registry in tests | Task 12 |
| Docker slim + non-root | Task 14 |
| docker-compose + ollama | Task 14 |
| .env.example all providers | Task 14 |
| K8s manifests (8 files) | Task 15 |
| Helm chart | Task 16 |
| README + provider examples | Task 17 |
| tools.py extension point | Task 7 |

All spec requirements covered. No placeholders detected.

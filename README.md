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

### Example

```bash
curl -X POST http://localhost:8000/rest/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

Response envelope:

```json
{
  "success": true,
  "data": {
    "answer": "The capital of France is Paris.",
    "provider": "ollama",
    "model": "qwen3:8b"
  },
  "error": null,
  "meta": {
    "requestId": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-05-07T10:00:00Z"
  }
}
```

## Provider Configuration

Set env vars (see `.env.example`):

**Ollama (default):**
```bash
AI_PROVIDER=ollama
AI_MODEL=qwen3:8b
AI_BASE_URL=http://localhost:11434/v1
AI_API_KEY=ollama
```

**OpenAI:**
```bash
AI_PROVIDER=openai
AI_MODEL=gpt-4o
AI_BASE_URL=https://api.openai.com/v1
AI_API_KEY=sk-...
```

**OpenRouter:**
```bash
AI_PROVIDER=openrouter
AI_MODEL=openai/gpt-4o
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=sk-or-...
OPENROUTER_HTTP_REFERER=https://yourapp.com
```

**LM Studio:**
```bash
AI_PROVIDER=lmstudio
AI_MODEL=lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF
AI_BASE_URL=http://localhost:1234/v1
AI_API_KEY=lm-studio
```

**vLLM:**
```bash
AI_PROVIDER=vllm
AI_MODEL=mistralai/Mistral-7B-Instruct-v0.2
AI_BASE_URL=http://localhost:8001/v1
AI_API_KEY=token-abc123
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

## Kubernetes

Apply plain manifests:

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.example.yaml   # rename and fill real values
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

Or use Helm:

```bash
helm install agent deploy/helm/python-agent-boilerplate \
  --set env.AI_PROVIDER=openai \
  --set env.AI_MODEL=gpt-4o \
  --set env.AI_BASE_URL=https://api.openai.com/v1 \
  --set secret.AI_API_KEY=sk-...
```

## Extension Points (v2+)

| Feature | Where |
|---------|-------|
| Tool calling | `app/agents/tools.py` |
| Streaming | Add `ModelClient.generate_stream()` in `app/ai/model_client.py` |
| Conversation memory | Wire `AgentRunRequest.conversation_id` to a store in `app/services/` |
| RAG | New service injected into `AgentService` in `app/services/` |
| Additional providers | New `ModelClient` subclass in `app/ai/providers/` |
| Background jobs | Celery/Redis integration in `app/services/` |

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide. The essentials:

- Set up: `make install` · validate: `make check` (lint + format + tests).
- Use a feature branch off `main`. Don't push to `main` directly.
- Add a one-line entry to `## [Unreleased]` in **[CHANGELOG.md](CHANGELOG.md)**
  for any user-visible change.

### Conventional Commits

Every commit message follows
[Conventional Commits 1.0.0](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative summary>
```

| Type | Use for | SemVer |
|------|---------|--------|
| `feat` | new feature | MINOR |
| `fix` | bug fix | PATCH |
| `perf` | performance | PATCH |
| `refactor` / `style` | code change, no behaviour change | none |
| `docs` | docs only | none |
| `test` | tests only | none |
| `build` / `ci` / `chore` | tooling, deps, infra | none |

Breaking changes use `feat(api)!: …` plus a `BREAKING CHANGE:` footer and
trigger a **MAJOR** version bump.

Examples:

```
feat(api): add /rest/v1/conversations endpoint
fix(envelope): preserve X-Request-Id when validation fails
docs: clarify OpenRouter setup
chore(deps): bump openai to 1.40
```

### Semantic Versioning

This project follows [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html).

| Part | Bumped when |
|------|-------------|
| **MAJOR** | Breaking change — envelope shape, error code value, removed route, breaking config rename, removed `ModelClient` method |
| **MINOR** | New backwards-compatible feature — new route, new provider, new optional config |
| **PATCH** | Backwards-compatible fix or internal improvement |

While the project is at `0.x`, anything may change between minor versions.
The full release procedure (changelog promotion, `pyproject.toml` bump, tag,
publish) is described in [CONTRIBUTING.md](CONTRIBUTING.md#cutting-a-release).

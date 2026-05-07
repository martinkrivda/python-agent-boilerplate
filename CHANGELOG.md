# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `app.__version__` exported from `app/__init__.py`, derived from
  `pyproject.toml` via `tomllib` (single source of truth).
- Version surfaced in the FastAPI app (`/doc` OpenAPI metadata) and in
  `GET /health` response (`data.version`).
- `scripts/release.py` to bump version following SemVer, sync it across
  `pyproject.toml`, Helm `Chart.yaml`, and K8s `deployment.yaml`, and
  promote the `## [Unreleased]` CHANGELOG section to a dated version.
- `make version`, `make release-patch`, `make release-minor`,
  `make release-major` Make targets.

## [0.1.0] — 2026-05-07

Initial release implementing the v1 design spec
(`docs/superpowers/specs/2026-05-06-python-agent-boilerplate-design.md`).

### Added

- FastAPI microservice with `lifespan`-managed `OpenAICompatibleModelClient` and
  `ModelSettings` on `app.state`.
- Provider-agnostic `ModelClient` ABC; reference implementation supports
  OpenAI / Ollama / LM Studio / vLLM / OpenRouter via the `openai` SDK.
- Business routes: `POST /rest/v1/agent/run`, `GET /rest/v1/models/current`.
- Infrastructure routes: `/health`, `/health/live`, `/health/ready`,
  `/metrics` (Prometheus WSGI), `/doc` (OpenAPI JSON).
- Standardised `ApiResponse` envelope with `ok()`, `error_response()` and
  `error_response_with_fields()` helpers.
- `AppError` hierarchy → error codes `E1001` (validation), `E2001`–`E2004`
  (provider timeout / auth / unavailable / bad response), `E3001` (internal).
- Three exception handlers (`AppError`, `RequestValidationError`, catch-all
  `Exception`) producing envelope-shaped JSON responses with `Cache-Control:
  no-store` and `X-Request-Id`.
- Middleware stack: `CorrelationIdMiddleware`, `RequestLoggingMiddleware`,
  `MetricsMiddleware` — registered last-in-first-out so correlation is outermost.
- structlog JSON logging with `request_id` bound automatically from a
  `ContextVar`.
- Prometheus metrics: 6 counters/histograms with isolated-registry support
  (`make_metrics(registry=...)`) for test isolation.
- pytest test suite: 52 tests covering routes, envelope invariants, error
  paths, request-id leakage, metrics counter behaviour, OpenAPI doc and
  metrics-endpoint envelope exclusions.
- Docker setup (`python:3.14-slim`, non-root `appuser`) and
  `docker-compose.yaml` with bundled Ollama for local dev.
- Plain Kubernetes manifests in `deploy/k8s/` (namespace, deployment, service,
  configmap, secret example, ingress, HPA, ServiceMonitor).
- Helm chart in `deploy/helm/python-agent-boilerplate/` with full
  values for image, ingress, autoscaling, securityContext, probes, env,
  optional ServiceMonitor.
- `Makefile` with self-documenting `help` target.
- Project tooling: `.editorconfig`, `.gitattributes`, `.dockerignore`,
  `.claudeignore`, `.vscode/` (settings + extension recommendations),
  `.claude/` (Claude Code settings, subagents, slash commands).

[Unreleased]: ../../compare/v0.1.0...HEAD
[0.1.0]: ../../releases/tag/v0.1.0

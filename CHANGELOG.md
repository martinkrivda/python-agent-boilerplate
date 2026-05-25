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
- Build provenance: `BUILD_COMMIT` and `BUILD_TIMESTAMP` settings populate
  `app.state.build_info`. Visible on `/health` as `commit` / `built_at`
  when set; omitted in local dev.
- Dockerfile now accepts `--build-arg BUILD_COMMIT=…` and
  `--build-arg BUILD_TIMESTAMP=…` and writes them as ENV plus the standard
  `org.opencontainers.image.{revision,created}` labels.
- `make docker-build` auto-fills these from `git rev-parse --short HEAD`
  and `date -u`.
- **Terminal CLI** (`agent` command): `version`, `models`, `ask "<q>"`,
  `chat` (interactive REPL), `serve` (start the HTTP service). Shares the
  same `Settings` / `ModelClient` / `AssistantAgent` core as the HTTP
  service — no duplicated logic.
- Project is now installable as a wheel (hatchling build backend); the
  `agent` script is registered via `[project.scripts]`.
- **File logging with rotation, gzip, and retention.** structlog now wraps
  stdlib `logging` so events flow through the same pipeline whether emitted
  by `structlog.get_logger()` or stdlib `logging.getLogger(...)`.
  - `LOG_TARGET=stdout` by default, with `stderr`, `file`, and `none` also
    supported.
  - `LOG_TARGET=file` enables `TimedRotatingFileHandler`, which
    writes to `logs/app.log`, rotates daily at UTC midnight, gzips rotated
    files, and prunes after `LOG_ROTATION_BACKUP_COUNT` (default 30 → ≈30
    days).
  - Static fields on every event: `service`, `env`, `version`, `hostname`.
  - Per-request fields via `structlog.contextvars` (`request_id`,
    `client_ip`, `method`, `path`; plus `user_id` / `conversation_id`
    bound by the agent route when present).
  - `log_format` setting: `json` (default) or `console` (pretty for dev).
- `request_context.py` now reads from `structlog.contextvars` instead of a
  bespoke `ContextVar`.
- New env vars: `LOG_FORMAT`, `LOG_TARGET`, `LOG_DIR`, `LOG_FILE_NAME`,
  `LOG_ROTATION_WHEN`, `LOG_ROTATION_BACKUP_COUNT`.
- 10 tests cover file write, stream target selection, static + dynamic fields,
  disable toggle, gzip rotation, and backup-count retention.
- `.github/dependabot.yml` — weekly Monday-morning updates for `uv`
  (Python deps, lockfile-only strategy), `docker` (base image), and
  `github-actions`. Minor/patch updates grouped to keep PR noise down;
  Conventional Commits prefixes (`chore(deps)`, `chore(docker)`,
  `chore(ci)`).
- CLAUDE.md and python-reviewer agent now document the
  `dependabot.yml` exception to the strict `.yaml` rule.

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

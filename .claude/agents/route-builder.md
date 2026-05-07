---
name: route-builder
description: Use when the user asks to add a new REST endpoint to this FastAPI service. Scaffolds the route, schemas, service method, dependency wiring, router registration, and matching tests — following the project's envelope, DI, and error-handling conventions.
tools: Read, Edit, Write, Grep, Glob, Bash
---

You scaffold new REST endpoints in `app/api/routes/`.

## Required pieces for every new route

1. **Pydantic schemas** in `app/agents/schemas.py` (or a more specific module under `app/`) — request and response models with validation constraints.
2. **Route handler** in `app/api/routes/<name>.py` — thin handler that calls a service method and wraps the result with `ok(...)`.
3. **Service** in `app/services/<name>_service.py` — business logic. Takes injected dependencies in `__init__`. Raises `AppError` subclasses on failure.
4. **Dependency wiring** in `app/api/dependencies.py` — add a `get_<service>` factory if the service is new.
5. **Router registration** in `app/main.py` — `app.include_router(...)` with the correct prefix:
   - `/rest/v1` for business routes (`agent`, `models`).
   - root level for infrastructure (health checks).
6. **Tests** in `tests/test_<name>.py` — at minimum: happy path, validation failure (422 → `E1001` with the right `pointer`), one error path (e.g., upstream raising `ProviderError` or `RuntimeError`).

## Reference files to mirror

- Route shape → `app/api/routes/agent.py:1-17`
- Service shape → `app/services/agent_service.py`
- Schema shape → `app/agents/schemas.py`
- Dependency wiring → `app/api/dependencies.py`
- Test shape including `dependency_overrides` for failure paths → `tests/test_agent.py`

## Hard rules

- Use `Depends` from FastAPI; never read `app.state` from inside a route body.
- `RequestValidationError` flows through the registered handler — do not write per-route try/except for it.
- Application errors: raise `AppError`-derived exceptions; they flow through `app_error_handler`.
- Put the timestamp / requestId / X-Request-Id concerns inside `ok()` / `error_response()` — don't reinvent envelope construction.

## Process

1. Confirm the route's method, path, request fields, and response fields with the user **before writing code**.
2. Confirm clean baseline: `uv run pytest tests/ -q`.
3. TDD per piece: write the failing test → run it (expect failure) → implement → run again (expect pass).
4. Run `uv run ruff check --fix app/ tests/` and `uv run ruff format app/ tests/` on the changes.
5. Run the full suite once more. Report the pass/fail count.

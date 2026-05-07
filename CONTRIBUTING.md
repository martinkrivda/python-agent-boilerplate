# Contributing

Thanks for taking the time to contribute. This document captures the
expectations for any change to this repository — read it once before opening
your first PR.

## Setup

```bash
git clone <repo-url>
cd python-agent-boilerplate
make install        # uv sync — installs deps and creates .venv
cp .env.example .env
make dev            # runs the FastAPI service on http://localhost:8000
```

You'll need:

- Python **3.14+** (pinned in `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- (optional) Docker — for `make docker-*`
- (optional) `helm`, `kubectl` — for `make helm-*` and `make k8s-validate`

## Coding standards

- Style is enforced by **ruff** (configured in `pyproject.toml`). Format on
  save is configured in `.vscode/settings.json` via the Ruff extension.
- **Async-first** — use `async def` for I/O; no blocking calls (`requests`,
  `time.sleep`) on the request path.
- **Type hints** on all public functions and class methods.
- **Pydantic v2** models for I/O boundaries; dataclasses for internal value
  objects.
- **YAML files use `.yaml`** — never `.yml`. This is a strict project rule.
- More project-specific conventions live in [CLAUDE.md](CLAUDE.md).

## Testing

Every change must be covered by a test. Use the existing patterns:

- `FakeModelClient` / `RaisesModelClient` from `tests/conftest.py` to swap
  the real `ModelClient` via `app.dependency_overrides[get_model_client]`.
  No real LLM calls in tests — the `openai` SDK must not be imported by
  test files.
- An isolated `CollectorRegistry` for any test touching Prometheus metrics
  (`make_metrics(registry=CollectorRegistry())`).
- The `client` fixture (`TestClient(app, raise_server_exceptions=False)`) for
  integration tests.

Run `make check` (lint + format-check + tests) before opening a PR. CI runs
the same gate.

## Branching

- Branch off `main`. Use a descriptive name: `feat/streaming`,
  `fix/request-id-leak`, `chore/bump-deps`.
- Keep commits small and focused. Each commit should pass `make check` on
  its own where practical.
- Never commit directly to `main`.

## Conventional Commits

Commit messages follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<optional-scope>): <short imperative summary>

<optional body — what + why, not how>

<optional footers>
```

### Types

| Type | When to use | SemVer impact |
|------|-------------|---------------|
| `feat` | New user-visible feature | MINOR |
| `fix` | Bug fix | PATCH |
| `perf` | Performance improvement | PATCH |
| `refactor` | Code change with no functional impact | none |
| `docs` | Documentation only | none |
| `test` | Adding / improving tests | none |
| `build` | Build system / dependency changes (`uv add ...`) | none |
| `ci` | CI / pipeline configuration | none |
| `chore` | Tooling, internal config, housekeeping | none |
| `revert` | Reverting a previous commit | matches reverted |
| `style` | Pure formatting (rare — `ruff format` usually handles this) | none |

### Breaking changes

Mark a breaking change with `!` after the type/scope **and** add a
`BREAKING CHANGE:` footer:

```
feat(api)!: rename `message` to `prompt` in AgentRunRequest

BREAKING CHANGE: clients must send `prompt` instead of `message`.
```

A breaking change drives a **MAJOR** version bump.

### Suggested scopes

`api`, `ai`, `agents`, `core`, `services`, `tests`, `docker`, `k8s`, `helm`,
`docs`, `ci`, `deps`. Keep the scope tight — one component per commit when
possible.

### Examples

```
feat(api): add /rest/v1/conversations endpoint
fix(envelope): preserve X-Request-Id when error_response_with_fields is used
docs: clarify provider configuration in README
test(agent): cover the request-id leakage path
chore(deps): bump openai to 1.40
refactor(ai): extract retry logic into a decorator
build(docker): switch base image to python:3.14-slim-bookworm
```

## Pull requests

1. Open a PR against `main`. The **PR title** must be a valid Conventional
   Commit — it is used for the squash-merge commit and changelog generation.
2. Update **`CHANGELOG.md`** under `## [Unreleased]` with a one-line entry
   in the appropriate section (Added / Changed / Deprecated / Removed /
   Fixed / Security).
3. Confirm `make check` passes locally.
4. Address review by adding new commits — don't force-push during review
   unless asked.
5. Squash-merge unless the branch's commit history is intentionally meaningful.

## Versioning & releases

This project follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

| Bump | Trigger |
|------|---------|
| **MAJOR** | Incompatible change to the HTTP envelope, error code values, removed routes, breaking config-variable renames, removed `ModelClient` methods. Marked with `!` or `BREAKING CHANGE:`. |
| **MINOR** | Backwards-compatible feature: new route, new provider, new optional config flag. |
| **PATCH** | Backwards-compatible bug fix or internal improvement. |

While the project is at `0.x` anything may change between minor versions.
After `1.0.0` we commit to the contract above.

### Cutting a release

1. Confirm `## [Unreleased]` in `CHANGELOG.md` accurately summarises every
   change since the last release.
2. Decide the new version (`MAJOR.MINOR.PATCH`) per SemVer.
3. Move `## [Unreleased]` entries into a new section with the version and
   today's date (UTC). Reset `## [Unreleased]` to empty.
4. Bump `version` in `pyproject.toml`.
5. Commit: `chore(release): vX.Y.Z`.
6. Tag and push: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.
7. Trigger the deployment pipeline / build & publish image and chart per your
   ops setup.

## Reporting issues

When opening an issue include:

- What you tried (request body, config, environment).
- What you expected.
- What actually happened (logs with `request_id`, error envelope, status code).
- Versions: Python, this service version (from `pyproject.toml`), AI provider.

**Never paste real API keys** or production logs containing secrets. Redact
before posting.

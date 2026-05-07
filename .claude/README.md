# Claude Code project settings

The `.claude/` directory contains project-wide configuration shared with the team.

## Layout

| Path | Purpose | Committed |
|------|---------|-----------|
| `settings.json` | Permissions, hooks, env — defines what Claude may do | yes |
| `settings.local.json` | Personal overrides (extra MCP servers, model, output style…) | no — gitignored |
| `agents/*.md` | Project-specific subagents (specialised reviewers / scaffolders) | yes |
| `commands/*.md` | Project-specific slash commands (`/test`, `/lint`, `/check`, …) | yes |

Personal `settings.local.json` overrides take precedence over `settings.json` for keys it defines.

## Subagents (`agents/`)

| Agent | When to use |
|-------|-------------|
| `python-reviewer` | After non-trivial Python changes — reviews against project conventions, runs ruff + pytest |
| `route-builder` | When adding a new REST endpoint — scaffolds schema + route + service + tests |
| `provider-adder` | When adding a non-OpenAI-compatible AI provider (Anthropic / Bedrock / Gemini) |
| `test-debugger` | When pytest fails — diagnoses against this project's testing model |

## Slash commands (`commands/`)

| Command | Effect |
|---------|--------|
| `/test` | `uv run pytest tests/ -q` with summary |
| `/lint` | `ruff check` + `ruff format --check`, auto-fix safe issues |
| `/check` | Full quality gate (lint + format + tests) |
| `/coverage` | `pytest --cov=app --cov-branch` with gap report |
| `/add-route <method> <path>` | Dispatches `route-builder` after confirming request/response shape |

## Permission tiers

- **`allow`** — read-only and idiomatic dev commands (`uv`, `pytest`, `ruff`, read-only `git`/`docker`/`kubectl`/`helm`, search & filesystem read tools, edits inside `app/`, `tests/`, `deploy/`, `docs/`).
- **`ask`** — state-changing infra (`docker build/run/push`, `kubectl apply/create`, `helm install/upgrade`, `uv publish`) and edits to sensitive root files (`pyproject.toml`, `Dockerfile`, `docker-compose.yaml`, `.github/`, `CLAUDE.md`).
- **`deny`** — mutating `git` commands, destructive infra ops (`kubectl delete`, `docker rm`, `rm -rf`), and reads of secrets (`.env`, `secrets/`, private keys).

## Hooks

| Event | What it does |
|-------|--------------|
| `PreToolUse` (Bash) | Blocks `pip install` / `poetry add` / `conda install` — forces use of `uv`. |
| `PostToolUse` (Edit/Write/MultiEdit) | Auto-runs `ruff check --fix` and `ruff format` on `*.py` / `*.pyi` files Claude writes. |
| `SessionStart` | Injects `Branch: <name> · <N> changed files` into session context. |
| `Stop` | Runs `ruff check app/ tests/` and shows last 5 lines as a final lint summary. |

## Environment

Hooks and Claude-spawned processes inherit:

- `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` — clean Python runtime.
- `APP_ENV=development` — matches the local dev profile.
- `DISABLE_TELEMETRY=1` — opt out of any telemetry.

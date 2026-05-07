# Claude Code project settings

`settings.json` is the **shared, committed** Claude Code config for this repository.
It defines what Claude can do without asking, what needs confirmation, what is forbidden,
and which automations run on tool use / session lifecycle events.

## Files

| File | Scope | Committed |
|------|-------|-----------|
| `settings.json` | Project-wide rules everyone shares | yes |
| `settings.local.json` | Personal overrides (extra MCP servers, model, output style…) | no — gitignored |

Personal overrides take precedence over `settings.json` for the keys they define.

## Permission tiers

- **`allow`** — read-only and idiomatic dev commands (`uv`, `pytest`, `ruff`, read-only `git`/`docker`/`kubectl`/`helm`, search & filesystem read tools, edits inside `app/`, `tests/`, `deploy/`, `docs/`).
- **`ask`** — state-changing infra (`docker build/run/push`, `kubectl apply/create`, `helm install/upgrade`, `uv publish`) and edits to sensitive root files (`pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.github/`, `CLAUDE.md`).
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

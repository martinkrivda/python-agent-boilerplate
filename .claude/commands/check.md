---
description: Full quality gate — lint, format check, full test suite
allowed-tools: Bash(uv run:*)
---

Run all of these in order. Stop at the first hard failure and do not run subsequent stages.

1. `uv run ruff check app/ tests/`
2. `uv run ruff format --check app/ tests/`
3. `uv run pytest tests/ -q`

Output a one-line summary per stage:

```
✓ ruff check — clean
✓ ruff format — clean
✓ pytest — 52 passed
```

If everything passes, say so plainly. If anything fails, show the failure (last 10 lines is usually enough), state which stage failed, and stop.

This command is purely diagnostic — do not modify code.

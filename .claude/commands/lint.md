---
description: Run ruff check and format-check; auto-fix what's safe
allowed-tools: Bash(uv run ruff:*)
---

Run the linter and formatter against `app/` and `tests/`:

1. `uv run ruff check app/ tests/`
   - If errors are reported, run `uv run ruff check --fix app/ tests/` and re-check.
2. `uv run ruff format --check app/ tests/`
   - If anything would be reformatted, run `uv run ruff format app/ tests/`.

Report the number of files changed and any remaining issues that auto-fix could not resolve.

If issues remain after auto-fix, show the offending lines so the user can decide.
